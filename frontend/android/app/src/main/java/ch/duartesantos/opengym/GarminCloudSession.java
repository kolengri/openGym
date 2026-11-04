package ch.duartesantos.opengym;

import org.json.JSONObject;

/** IO-owned renewal policy shared by the native bridge and deterministic failure tests. */
final class GarminCloudSession {
    static final class Credentials {
        final String token, csrf, accountBinding;
        Credentials(String token, String csrf, String accountBinding) {
            this.token = token; this.csrf = csrf; this.accountBinding = accountBinding;
        }
    }
    interface Renewal {
        Credentials fetch(String previousToken) throws GarminCloudClient.Failure;
        default void check() throws GarminCloudClient.Failure { }
    }
    static final Renewal UNAVAILABLE = previous -> { throw new GarminCloudClient.Failure("auth_expired"); };

    static boolean ready(GarminCloudStore store, String session, Renewal renewal, boolean force) throws Exception {
        store.requireSession(session);
        renewal.check();
        if (!force && !store.renewalDue()) return false;
        if (!store.renewalAvailable()) throw new GarminCloudClient.Failure("auth_expired");
        String previousToken = store.token();
        try {
            Credentials fresh = renewal.fetch(previousToken);
            renewal.check();
            store.finishRenewal(session, previousToken, fresh.token, fresh.csrf, fresh.accountBinding);
        } catch (GarminCloudClient.Failure failure) {
            // Only an unambiguous expired SSO session/account mismatch requires interactive login.
            // Offline/timeouts keep the old credentials and browser renewal cookies for retry.
            if (failure.code.equals("auth_required") || failure.code.equals("session_changed")) {
                store.reload();
                if (session.equals(store.sessionId())) store.rejectAuthentication(true);
            }
            throw failure;
        }
        return true;
    }

    static JSONObject readHealth(GarminCloudStore store, String session, String date, String metric,
                                 GarminHealthClient client, Renewal renewal) throws Exception {
        store.requireSession(session);
        GarminHealthClient.validateRead(date, metric);
        boolean renewed = ready(store, session, renewal, false);
        renewal.check();
        try { return client.read(store, session, date, metric); }
        catch (GarminCloudClient.Failure failure) {
            if (!failure.code.equals("auth_required")) throw failure;
            store.rejectAuthentication(renewed);
            if (renewed) throw failure;
            ready(store, session, renewal, true);
            renewal.check();
            // GET is safe to repeat once after the authoritative account endpoint rejected auth.
            try { return client.read(store, session, date, metric); }
            catch (GarminCloudClient.Failure retryFailure) {
                if (retryFailure.code.equals("auth_required")) store.rejectAuthentication(true);
                throw retryFailure;
            }
        }
    }

    static GarminCloudClient.Outcome upload(GarminCloudStore store, String session, String workout,
                                            String sha, boolean retryUnknown, GarminCloudPlugin.Upload upload,
                                            Renewal renewal) throws Exception {
        GarminCloudClient.Outcome receipt = store.inspectUpload(session, workout, sha, retryUnknown);
        if (receipt != null) return receipt;
        boolean wasUnknown = store.uncertain(workout);
        boolean renewed;
        try {
            renewed = ready(store, session, renewal, false);
            renewal.check();
            store.begin(session, workout, sha, retryUnknown);
        } catch (Exception failure) {
            // A failed preflight cannot establish what happened to an earlier POST.
            if (wasUnknown) throw new GarminCloudClient.Failure("unknown_result");
            throw failure;
        }
        GarminCloudClient.Outcome result;
        try { renewal.check(); result = upload.send(); }
        catch (GarminCloudClient.Failure failure) {
            String code = GarminCloudPlugin.recordUploadFailure(store, workout, wasUnknown, failure);
            if (failure.code.equals("auth_required") && (wasUnknown || !code.equals("unknown_result"))) {
                try {
                    store.rejectAuthentication(renewed);
                    if (!renewed) {
                        try { ready(store, session, renewal, true); if (!wasUnknown) code = "upload_failed"; }
                        catch (GarminCloudClient.Failure refreshFailure) {
                            // A definite failed POST must never become an automatic network retry.
                            if (!wasUnknown) code = refreshFailure.code.equals("network_error") ? "upload_failed" : refreshFailure.code;
                        }
                    }
                } catch (Exception refreshStorageFailure) {
                    // Neither renewal failure nor its failed persistence can resolve an older POST.
                    if (!wasUnknown) throw refreshStorageFailure;
                }
            }
            throw new GarminCloudClient.Failure(code);
        }
        try { store.complete(workout, result); }
        catch (Exception ignored) { throw new GarminCloudClient.Failure("unknown_result"); }
        return result;
    }
}
