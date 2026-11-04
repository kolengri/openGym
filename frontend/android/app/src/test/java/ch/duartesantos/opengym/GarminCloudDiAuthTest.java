package ch.duartesantos.opengym;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import org.json.JSONObject;
import org.junit.Test;
import static org.junit.Assert.*;

/** Native production orchestration/parser seams. No device, account, cookies or real HTTP. */
public class GarminCloudDiAuthTest {
    private static final long NOW = 1800000000000L;
    private static final String TOKEN = "synthetic.payload.signature", FRESH = "synthetic.fresh.signature";
    private static final String TICKET = "ST-synthetic-ticket", SHA = "a".repeat(64);
    private static String callback() { return GarminCloudAuth.SERVICE + "?ticket=" + TICKET; }
    private static GarminCloudAuth auth(GarminCloudAuth.Transport transport, AtomicLong now) {
        return new GarminCloudAuth(transport, now::get, Base64.getUrlDecoder()::decode,
            value -> Base64.getEncoder().encodeToString(value));
    }
    private static GarminCloudStore open(GarminCloudStoreTest.Disk disk, AtomicLong now) throws Exception {
        return new GarminCloudStore(disk, now::get, Base64.getUrlDecoder()::decode);
    }
    private static String pair(String token, String refresh) {
        try {
            return new JSONObject().put("access_token", token).put("refresh_token", refresh)
                .put("expires_in", 7200).put("token_type", "Bearer").toString();
        } catch (Exception e) { throw new AssertionError(e); }
    }
    private static GarminCloudSession.Credentials credentials() {
        return new GarminCloudSession.Credentials(TOKEN, "old-refresh", GarminCloudAuth.CLIENT_ID, NOW + 120000);
    }

    @Test public void callbackBindsTheExactIssuedServiceAndRejectsAmbiguousOrUntrustedUrls() {
        assertEquals(TICKET, GarminCloudAuth.serviceTicket(callback()));
        for (String url : new String[]{
            "http://connect.garmin.com/app?ticket=" + TICKET,
            "https://connect.garmin.com:443/app?ticket=" + TICKET,
            "https://connect.garmin.com/app/?ticket=" + TICKET,
            "https://connect.garmin.com/modern?ticket=" + TICKET,
            "https://sso.garmin.com/app?ticket=" + TICKET,
            "https://connect.garmin.com.evil.invalid/app?ticket=" + TICKET,
            "https://evil.invalid@connect.garmin.com/app?ticket=" + TICKET,
            callback() + "&ticket=ST-second", callback() + "&service=" + GarminCloudAuth.SERVICE,
            callback() + "#fragment", GarminCloudAuth.SERVICE + "?ticket=ST-line%0Abreak",
            GarminCloudAuth.SERVICE + "?ticket=", GarminCloudAuth.SERVICE + "?ticket=%ZZ",
            "https://connect.garmin.com/%61pp?ticket=" + TICKET })
            assertNull(url, GarminCloudAuth.serviceTicket(url));
        assertNull(GarminCloudAuth.serviceTicket(null));
        assertNull(GarminCloudAuth.serviceTicket(GarminCloudAuth.SERVICE + "?ticket=ST-" + "x".repeat(4096)));
    }

    @Test public void navigationAndInterceptHooksCanClaimOnlyOnceAndOnlyForAMainFrameGet() throws Exception {
        GarminCloudAuth.LoginAttempt attempt = new GarminCloudAuth.LoginAttempt(UUID.randomUUID().toString());
        assertNull(attempt.claim(callback(), "POST", true));
        assertNull(attempt.claim(callback(), "GET", false));
        CountDownLatch start = new CountDownLatch(1);
        AtomicInteger claims = new AtomicInteger();
        Runnable hook = () -> {
            try { start.await(); if (attempt.claim(callback(), "GET", true) != null) claims.incrementAndGet(); }
            catch (InterruptedException e) { throw new AssertionError(e); }
        };
        Thread navigation = new Thread(hook), intercept = new Thread(hook);
        navigation.start(); intercept.start(); start.countDown(); navigation.join(); intercept.join();
        assertEquals(1, claims.get());
        assertFalse(attempt.incompletePage(GarminCloudAuth.SERVICE));
        assertNull(attempt.claim(callback(), "GET", true));
    }

    @Test public void completedPageWithoutATicketIsABoundedIncompleteLoginAndCancellationCannotClaim() {
        GarminCloudAuth.LoginAttempt attempt = new GarminCloudAuth.LoginAttempt(UUID.randomUUID().toString());
        assertFalse(attempt.incompletePage(GarminCloudAuth.SIGN_IN));
        assertTrue(attempt.incompletePage(GarminCloudAuth.SERVICE));
        assertTrue(attempt.incompletePage("https://connect.garmin.com/app/"));
        attempt.cancel();
        assertNull(attempt.claim(callback(), "GET", true));
        assertFalse(attempt.incompletePage(GarminCloudAuth.SERVICE));
        assertThrows(IllegalArgumentException.class, () -> new GarminCloudAuth.LoginAttempt("not-a-nonce"));
    }

    @Test public void exchangeUsesPinnedGrantServiceBasicAuthAndNativeHeadersWithoutCookies() throws Exception {
        AtomicInteger posts = new AtomicInteger();
        GarminCloudAuth client = auth((headers, body) -> {
            posts.incrementAndGet();
            assertEquals("Basic " + Base64.getEncoder().encodeToString((GarminCloudAuth.CLIENT_ID + ":").getBytes(StandardCharsets.UTF_8)), headers.get("Authorization"));
            assertEquals("application/x-www-form-urlencoded", headers.get("Content-Type"));
            assertEquals("GCM-Android-5.23", headers.get("User-Agent"));
            assertEquals("Android", headers.get("X-Garmin-Client-Platform"));
            assertFalse(headers.containsKey("Cookie"));
            assertFalse(headers.containsKey("connect-csrf-token"));
            assertFalse(headers.containsKey("Origin"));
            String form = java.net.URLDecoder.decode(body, StandardCharsets.UTF_8);
            assertTrue(form.contains("grant_type=" + GarminCloudAuth.SERVICE_GRANT));
            assertTrue(form.contains("client_id=" + GarminCloudAuth.CLIENT_ID));
            assertTrue(form.contains("service_ticket=" + TICKET));
            assertTrue(form.endsWith("service_url=" + GarminCloudAuth.SERVICE));
            return new GarminCloudAuth.Response(200, pair(TOKEN, "fresh-refresh"));
        }, new AtomicLong(NOW));
        GarminCloudSession.Credentials result = client.exchange(TICKET, GarminCloudAuth.SERVICE);
        assertEquals(TOKEN, result.token);
        assertEquals("fresh-refresh", result.refreshToken);
        assertEquals(NOW + 7200000, result.expiresAt);
        assertEquals(1, posts.get());
        assertEquals("auth_exchange_failed", assertThrows(GarminCloudClient.Failure.class,
            () -> client.exchange(TICKET, GarminCloudAuth.SERVICE + "/")).code);
        assertEquals(1, posts.get());
    }

    @Test public void successfulGrantPersistsBeforeAnyUnavailableProfileCanBlockLogin() throws Exception {
        for (int profileStatus : new int[]{204, 401, 403, 500}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            AtomicLong now = new AtomicLong(NOW);
            GarminCloudStore store = open(disk, now);
            GarminCloudAuth.LoginAttempt attempt = new GarminCloudAuth.LoginAttempt(store.startLogin());
            GarminCloudAuth.completeLogin(store, attempt, TICKET,
                auth((headers, body) -> new GarminCloudAuth.Response(200, pair(TOKEN, "persisted-refresh")), now), () -> { });
            GarminCloudStore restarted = open(disk, now);
            assertTrue(restarted.loginResultMatches(attempt.nonce));
            assertEquals("persisted-refresh", restarted.refreshToken());
            String saved = disk.value;
            GarminHealthClient unavailable = new GarminHealthClient((url, token, csrf) -> new GarminHealthClient.Response(profileStatus, null));
            GarminCloudPlugin.readHealthOnce(restarted, restarted.sessionId(), "2026-01-02", "sleep", unavailable);
            assertTrue(open(disk, now).connected());
            assertTrue(open(disk, now).loginResultMatches(attempt.nonce));
            if (profileStatus != 401) assertEquals(saved, disk.value);
            String bridged = GarminCloudPlugin.status(restarted).toString();
            assertFalse(bridged.contains(TOKEN));
            assertFalse(bridged.contains("persisted-refresh"));
            assertFalse(bridged.contains(GarminCloudAuth.CLIENT_ID));
        }
    }

    @Test public void cancelledOrSupersededNonceCannotPersistTheNetworkResult() throws Exception {
        for (boolean newLogin : new boolean[]{false, true}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            AtomicLong now = new AtomicLong(NOW);
            GarminCloudStore stale = open(disk, now);
            GarminCloudAuth.LoginAttempt attempt = new GarminCloudAuth.LoginAttempt(stale.startLogin());
            GarminCloudAuth client = auth((headers, body) -> {
                try {
                    GarminCloudStore current = open(disk, now);
                    if (newLogin) current.startLogin(); else current.cancelLogin(attempt.nonce);
                    return new GarminCloudAuth.Response(200, pair(TOKEN, "uncommitted-refresh"));
                } catch (Exception e) { throw new AssertionError(e); }
            }, now);
            assertEquals("cancelled", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudAuth.completeLogin(stale, attempt, TICKET, client, () -> { })).code);
            assertFalse(open(disk, now).connected());
            assertFalse(disk.value.contains("uncommitted-refresh"));
        }
    }

    @Test public void lifecycleCancellationAndRevokedOperationLeaseFenceLoginBeforePersistence() throws Exception {
        for (boolean cancelAttempt : new boolean[]{false, true}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            AtomicLong now = new AtomicLong(NOW);
            GarminCloudStore store = open(disk, now);
            GarminCloudAuth.LoginAttempt attempt = new GarminCloudAuth.LoginAttempt(store.startLogin());
            long lease = GarminCloudRenewal.lease();
            GarminCloudAuth client = auth((headers, body) -> {
                if (cancelAttempt) attempt.cancel(); else GarminCloudRenewal.cancelPending();
                return new GarminCloudAuth.Response(200, pair(TOKEN, "uncommitted-refresh"));
            }, now);
            assertEquals("cancelled", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudAuth.completeLogin(store, attempt, TICKET, client, () -> GarminCloudRenewal.checkLease(lease))).code);
            assertFalse(open(disk, now).connected());
        }
    }

    @Test public void unusableInitialPairNeverBecomesConnectedOrEchoesTheResponse() throws Exception {
        for (String body : new String[]{"{broken-private-response", "{}",
            "{\"access_token\":\"" + TOKEN + "\",\"expires_in\":7200}",
            "{\"access_token\":\"" + TOKEN + "\",\"refresh_token\":\"r\",\"expires_in\":0}",
            "{\"access_token\":\"" + TOKEN + "\",\"refresh_token\":null,\"expires_in\":7200}",
            "{\"access_token\":\"" + TOKEN + "\",\"refresh_token\":\"r\",\"expires_in\":\"7200\"}",
            "{\"access_token\":\"" + TOKEN + "\",\"refresh_token\":\"r\",\"expires_in\":7200,\"token_type\":\"Basic\"}",
            pair(TOKEN, "r") + " trailing"}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            AtomicLong now = new AtomicLong(NOW);
            GarminCloudStore store = open(disk, now);
            GarminCloudAuth.LoginAttempt attempt = new GarminCloudAuth.LoginAttempt(store.startLogin());
            String before = disk.value;
            GarminCloudClient.Failure failure = assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudAuth.completeLogin(store, attempt, TICKET,
                    auth((headers, form) -> new GarminCloudAuth.Response(200, body), now), () -> { }));
            assertEquals("auth_exchange_failed", failure.getMessage());
            assertEquals(before, disk.value);
            assertFalse(store.connected());
        }
    }

    @Test public void refreshGrantRotatesDurablyBeforePostAndSurvivesRestartWithoutChangingGeneration() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong now = new AtomicLong(NOW);
        GarminCloudStore store = open(disk, now);
        store.login(credentials());
        String session = store.sessionId();
        now.addAndGet(61000); // Refresh before the server-provided access-token expiry.
        AtomicInteger refreshes = new AtomicInteger(), posts = new AtomicInteger();
        GarminCloudAuth client = auth((headers, body) -> {
            refreshes.incrementAndGet();
            assertEquals("grant_type=refresh_token&client_id=" + GarminCloudAuth.CLIENT_ID + "&refresh_token=old-refresh", body);
            assertFalse(body.contains("service_ticket"));
            return new GarminCloudAuth.Response(200, pair(FRESH, "rotated-refresh"));
        }, now);
        GarminCloudPlugin.uploadOnce(open(disk, now), session, "workout", SHA, false, () -> {
            posts.incrementAndGet();
            try {
                GarminCloudStore durable = open(disk, now);
                assertEquals(FRESH, durable.token());
                assertEquals("rotated-refresh", durable.refreshToken());
                assertEquals(session, durable.sessionId());
            } catch (Exception e) { throw new AssertionError(e); }
            return new GarminCloudClient.Outcome("uploaded", "123");
        }, client::refresh);
        assertEquals(1, posts.get());
        assertEquals(1, refreshes.get());
        assertEquals(session, new JSONObject(disk.value).getJSONArray("receipts").getJSONObject(0).getString("generation"));
        assertTrue(open(disk, now).renewalAvailable());
    }

    @Test public void refreshCanRetainItsUnrotatedTokenAndUseJwtExpiryWhenExpiresInIsAbsent() throws Exception {
        AtomicLong now = new AtomicLong(NOW);
        String jwt = "e30." + Base64.getUrlEncoder().withoutPadding().encodeToString("{\"exp\":1800007200}".getBytes(StandardCharsets.UTF_8)) + ".synthetic";
        GarminCloudSession.Credentials result = auth((headers, body) -> new GarminCloudAuth.Response(200,
            "{\"access_token\":\"" + jwt + "\"}"), now).refresh(credentials());
        assertEquals("old-refresh", result.refreshToken);
        assertEquals(1800007200000L, result.expiresAt);
    }

    @Test public void onlyDefinitiveRefreshRejectionDisablesRenewalAndTransientErrorsPreserveTheGrant() throws Exception {
        for (int status : new int[]{400, 401, 403, 429, 500, 302, 200}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            AtomicLong now = new AtomicLong(NOW);
            GarminCloudStore store = open(disk, now);
            store.login(credentials());
            String session = store.sessionId();
            now.addAndGet(180000);
            String before = disk.value;
            String body = status == 400 ? "{\"error\":\"invalid_grant\",\"private\":\"never-echo\"}" : "{}";
            GarminCloudAuth client = auth((headers, form) -> new GarminCloudAuth.Response(status, body), now);
            String expected = status == 400 || status == 401 ? "auth_required" : status == 429 ? "rate_limited"
                : status == 500 || status == 302 ? "network_error" : "auth_exchange_failed";
            assertEquals(expected, assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudSession.ready(store, session, client::refresh, false)).getMessage());
            GarminCloudStore after = open(disk, now);
            assertTrue(after.connected());
            assertEquals("old-refresh", after.refreshToken());
            assertEquals(session, after.sessionId());
            assertEquals(!(status == 400 || status == 401), after.renewalAvailable());
            if (status != 400 && status != 401) assertEquals(before, disk.value);
        }
    }

    @Test public void failedGrantPersistenceCannotPublishLoginOrAllowAPost() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong now = new AtomicLong(NOW);
        GarminCloudStore store = open(disk, now);
        GarminCloudAuth.LoginAttempt attempt = new GarminCloudAuth.LoginAttempt(store.startLogin());
        String before = disk.value;
        disk.fail = true;
        assertThrows(java.io.IOException.class, () -> GarminCloudAuth.completeLogin(store, attempt, TICKET,
            auth((headers, form) -> new GarminCloudAuth.Response(200, pair(TOKEN, "uncommitted-refresh")), now), () -> { }));
        assertEquals(before, disk.value);
        assertFalse(store.connected());
    }

    @Test public void legacyCookiesReconcileReceiptsButNeverRenewOrPostAndPreserveUnknownPreflight() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong now = new AtomicLong(NOW);
        GarminCloudStore store = open(disk, now);
        store.login(credentials());
        String session = store.sessionId();
        store.begin(session, "done", SHA, false);
        store.complete("done", new GarminCloudClient.Outcome("uploaded", "123"));
        store.begin(session, "unknown", SHA, false);
        JSONObject legacy = new JSONObject(disk.value);
        for (String key : new String[]{"authType", "refreshToken", "clientId", "expiresAt"}) legacy.remove(key);
        legacy.put("csrf", "legacy-csrf").put("accountBinding", "b".repeat(64));
        disk.value = legacy.toString();
        GarminCloudStore migrated = open(disk, now);
        assertTrue(migrated.connected());
        assertEquals("expired", migrated.authState());
        assertFalse(migrated.renewalAvailable());
        String before = disk.value;
        AtomicInteger posts = new AtomicInteger(), renewals = new AtomicInteger();
        GarminCloudPlugin.Upload send = () -> { posts.incrementAndGet(); return new GarminCloudClient.Outcome("uploaded", "456"); };
        GarminCloudSession.Renewal renewal = previous -> { renewals.incrementAndGet(); return credentials(); };
        assertEquals("123", GarminCloudPlugin.uploadOnce(migrated, session, "done", SHA, false, send, renewal).activityId);
        for (boolean retry : new boolean[]{false, true}) assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(migrated, session, "unknown", SHA, retry, send, renewal)).code);
        assertEquals("auth_expired", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(migrated, session, "new-workout", SHA, false, send, renewal)).code);
        assertEquals(0, posts.get());
        assertEquals(0, renewals.get());
        assertEquals(before, disk.value);
    }
}
