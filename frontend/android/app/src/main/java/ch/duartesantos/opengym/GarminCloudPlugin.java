package ch.duartesantos.opengym;

import android.app.Activity;
import android.content.Intent;
import android.util.Base64;
import androidx.activity.result.ActivityResult;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

/** Native session, completed FIT upload and allowlisted read-only health bridge. */
@CapacitorPlugin(name = "GarminCloud")
public final class GarminCloudPlugin extends Plugin {
    private volatile String connectingNonce;
    // IO-owned origin: Capacitor itself remembers only the latest Activity call.
    private PluginCall connectingCall;
    private static final String CALL_NONCE = "__garminNativeLoginNonce";

    @PluginMethod public void status(PluginCall call) {
        GarminCloudStore.IO.execute(() -> {
            try { call.resolve(status(GarminCloudStore.open(getContext()))); }
            catch (Exception ignored) { reject(call, "storage_unavailable"); }
        });
    }

    static JSObject status(GarminCloudStore store) {
        // connected is credential presence, retained for receipt reconciliation. The UI uses
        // authState to distinguish an expired session without mistaking it for a storage failure.
        JSObject result = new JSObject().put("available", true).put("connected", store.connected())
            .put("authState", store.authState()).put("renewalAvailable", store.renewalAvailable());
        if (store.connected()) result.put("sessionId", store.sessionId());
        return result;
    }

    @PluginMethod public void connect(PluginCall call) {
        GarminCloudRenewal.cancelPending();
        GarminCloudStore.IO.execute(() -> {
            if (connectingNonce != null) { reject(call, "auth_required"); return; }
            try {
                GarminCloudStore store = GarminCloudStore.open(getContext());
                String nonce = store.startLogin();
                connectingNonce = nonce;
                connectingCall = call;
                call.getData().put(CALL_NONCE, nonce);
                getActivity().runOnUiThread(() -> {
                    try {
                        startActivityForResult(call, new Intent(getContext(), GarminCloudLoginActivity.class)
                            .putExtra(GarminCloudLoginActivity.NONCE, nonce), "loginResult");
                    } catch (Exception ignored) {
                        GarminCloudStore.IO.execute(() -> {
                            try { GarminCloudStore.open(getContext()).cancelLogin(nonce); } catch (Exception unavailable) { /* Fail closed. */ }
                            if (nonce.equals(connectingNonce)) {
                                connectingNonce = null;
                                connectingCall = null;
                                reject(call, "auth_required");
                            }
                        });
                    }
                });
            } catch (Exception ignored) { reject(call, "storage_unavailable"); }
        });
    }

    @ActivityCallback private void loginResult(PluginCall call, ActivityResult result) {
        String nonce = result.getData() == null ? null : result.getData().getStringExtra(GarminCloudLoginActivity.NONCE);
        GarminCloudStore.IO.execute(() -> {
            // An old callback can be delivered with the NEWEST PluginCall by Capacitor.
            // Resolve/reject only the native-bound originating call, never that unrelated call.
            PluginCall origin = connectingCall != null && GarminCloudStore.sameLoginNonce(nonce, connectingCall.getString(CALL_NONCE))
                ? connectingCall : call != null && GarminCloudStore.sameLoginNonce(nonce, call.getString(CALL_NONCE)) ? call : null;
            if (origin == null) return;
            if (GarminCloudStore.sameLoginNonce(nonce, connectingNonce)) {
                connectingNonce = null;
                connectingCall = null;
            }
            if (result.getResultCode() != Activity.RESULT_OK) {
                try { GarminCloudStore.open(getContext()).cancelLogin(nonce); } catch (Exception ignored) { /* Fail closed. */ }
                String error = result.getData() == null ? null : result.getData().getStringExtra(GarminCloudLoginActivity.ERROR);
                reject(origin, safeLoginError(error)); return;
            }
            try {
                GarminCloudStore store = GarminCloudStore.open(getContext());
                if (!store.loginResultMatches(nonce)) { reject(origin, "cancelled"); return; }
                origin.resolve(status(store));
            } catch (Exception ignored) { reject(origin, "storage_unavailable"); }
        });
    }

    @PluginMethod public void disconnect(PluginCall call) {
        GarminCloudRenewal.cancelPending();
        GarminCloudStore.IO.execute(() -> {
            String previous = connectingNonce;
            connectingNonce = null;
            PluginCall cancelledCall = connectingCall;
            connectingCall = null;
            if (cancelledCall != null) reject(cancelledCall, "cancelled");
            boolean disconnected;
            try {
                GarminCloudStore store = GarminCloudStore.open(getContext());
                previous = store.cancellationNonce();
                store.disconnect();
                disconnected = true;
            } catch (Exception ignored) { disconnected = false; }
            boolean success = disconnected;
            String cancelledNonce = previous;
            getActivity().runOnUiThread(() -> {
                GarminCloudLoginActivity.dismissCancelled(cancelledNonce);
                GarminCloudLoginActivity.clearGarminCookies(() -> {
                    if (success) call.resolve(); else reject(call, "storage_unavailable");
                });
            });
        });
    }

    @PluginMethod public void healthMetrics(PluginCall call) {
        try { call.resolve(new JSObject().put("metrics", GarminHealthClient.catalog())); }
        catch (Exception ignored) { reject(call, "health_failed"); }
    }

    @PluginMethod public void readHealthArchive(PluginCall call) {
        GarminCloudStore.IO.execute(() -> {
            try {
                org.json.JSONObject record = GarminHealthArchive.open(getContext()).read(
                    call.getString("ownerKey"), call.getString("date"), call.getString("metric"));
                call.resolve(new JSObject().put("record", record == null ? org.json.JSONObject.NULL : record));
            } catch (Exception failure) {
                reject(call, failure instanceof GarminCloudClient.Failure ? "invalid_metric" : "storage_error");
            }
        });
    }

    @PluginMethod public void writeHealthArchive(PluginCall call) {
        GarminCloudStore.IO.execute(() -> {
            try {
                GarminHealthArchive.open(getContext()).write(call.getString("ownerKey"), call.getString("date"),
                    call.getString("metric"), call.getString("record"));
                call.resolve();
            } catch (Exception failure) {
                reject(call, failure instanceof GarminCloudClient.Failure ? "invalid_metric" : "storage_error");
            }
        });
    }

    @PluginMethod public void readHealthMetric(PluginCall call) {
        long renewalLease = GarminCloudRenewal.lease();
        GarminCloudStore.IO.execute(() -> {
            String metric = call.getString("metric"), date = call.getString("date"), session = call.getString("sessionId");
            try {
                GarminCloudStore store = GarminCloudStore.open(getContext());
                org.json.JSONObject result = readHealthOnce(store, session, date, metric, new GarminHealthClient(),
                    GarminCloudRenewal.forOperation(getContext(), renewalLease));
                call.resolve(new JSObject(result.toString()));
            } catch (Exception failure) {
                String code = failure instanceof GarminCloudClient.Failure ? ((GarminCloudClient.Failure) failure).code : "storage_unavailable";
                try { call.resolve(new JSObject(GarminHealthClient.error(metric, date, code).toString())); }
                catch (Exception ignored) { reject(call, "health_failed"); }
            }
        });
    }

    /** Shared by the bridge and offline repeated-read/session-persistence tests. IO-owned. */
    static org.json.JSONObject readHealthOnce(GarminCloudStore store, String session, String date,
                                              String metric, GarminHealthClient client) throws Exception {
        return readHealthOnce(store, session, date, metric, client, GarminCloudSession.UNAVAILABLE);
    }

    static org.json.JSONObject readHealthOnce(GarminCloudStore store, String session, String date,
                                              String metric, GarminHealthClient client, GarminCloudSession.Renewal renewal) throws Exception {
        try { return GarminCloudSession.readHealth(store, session, date, metric, client, renewal); }
        catch (GarminCloudClient.Failure failure) {
            return GarminHealthClient.error(metric, date, failure.code);
        }
    }

    @PluginMethod public void upload(PluginCall call) {
        long renewalLease = GarminCloudRenewal.lease();
        GarminCloudStore.IO.execute(() -> {
            if (connectingNonce != null) { reject(call, "auth_required"); return; }
            GarminCloudStore store;
            String workout = call.getString("workoutId");
            try {
                String encoded = call.getString("base64");
                GarminCloudClient.validateBase64(encoded);
                byte[] fit = Base64.decode(encoded, Base64.NO_WRAP);
                GarminCloudClient.validateFit(fit);
                store = GarminCloudStore.open(getContext());
                resolve(call, uploadOnce(store, call.getString("sessionId"), workout,
                    GarminCloudClient.sha256(fit), Boolean.TRUE.equals(call.getBoolean("retryUnknown", false)),
                    () -> new GarminCloudClient().upload(fit, call.getString("filename"), store.token(), store.csrf()),
                    GarminCloudRenewal.forOperation(getContext(), renewalLease)));
            } catch (GarminCloudClient.Failure failure) { reject(call, failure.code); }
            catch (Exception ignored) { reject(call, "storage_unavailable"); }
        });
    }

    interface Upload { GarminCloudClient.Outcome send() throws GarminCloudClient.Failure; }

    /** Receipt/readiness ordering is shared by the native bridge and offline no-POST tests. */
    static GarminCloudClient.Outcome uploadOnce(GarminCloudStore store, String session, String workout,
                                               String sha, boolean retryUnknown, Upload upload) throws Exception {
        return uploadOnce(store, session, workout, sha, retryUnknown, upload, GarminCloudSession.UNAVAILABLE);
    }

    static GarminCloudClient.Outcome uploadOnce(GarminCloudStore store, String session, String workout,
                                               String sha, boolean retryUnknown, Upload upload,
                                               GarminCloudSession.Renewal renewal) throws Exception {
        return GarminCloudSession.upload(store, session, workout, sha, retryUnknown, upload, renewal);
    }

    /** IO-owned failure transition; never discard an earlier ambiguous upload receipt. */
    static String recordUploadFailure(GarminCloudStore store, String workout, boolean wasUnknown,
                                     GarminCloudClient.Failure failure) {
        if (!failure.code.equals("unknown_result")) {
            try {
                if (!wasUnknown) store.definitelyFailed(workout);
            } catch (Exception ignored) { return "unknown_result"; }
        }
        return wasUnknown ? "unknown_result" : failure.code;
    }

    private void resolve(PluginCall call, GarminCloudClient.Outcome receipt) {
        JSObject result = new JSObject().put("status", receipt.status);
        if (receipt.activityId != null) result.put("activityId", receipt.activityId);
        call.resolve(result);
    }

    private void reject(PluginCall call, String code) { call.reject(code, code); }

    private static String safeLoginError(String code) {
        if ("network_error".equals(code) || "auth_required".equals(code) || "profile_unavailable".equals(code)
            || "storage_unavailable".equals(code) || "rate_limited".equals(code)
            || "auth_incomplete".equals(code) || "auth_exchange_failed".equals(code)) return code;
        return code == null || "cancelled".equals(code) ? "cancelled" : "profile_unavailable";
    }
}
