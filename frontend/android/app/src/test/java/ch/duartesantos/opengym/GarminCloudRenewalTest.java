package ch.duartesantos.opengym;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import org.json.JSONObject;
import org.junit.Test;
import static org.junit.Assert.*;

/** Production orchestration with deterministic refresh/HTTP seams; no real account or network. */
public class GarminCloudRenewalTest {
    private static final long NOW = 1800000000000L;
    private static final String SHA = "a".repeat(64);
    private static final String OLD = token(1800000120), FRESH = token(1800007200);
    private static String token(long expiry) {
        return "e30." + Base64.getUrlEncoder().withoutPadding().encodeToString(
            ("{\"exp\":" + expiry + "}").getBytes(StandardCharsets.UTF_8)) + ".synthetic";
    }
    private static GarminCloudStore open(GarminCloudStoreTest.Disk disk, AtomicLong clock) throws Exception {
        return new GarminCloudStore(disk, clock::get, Base64.getUrlDecoder()::decode);
    }
    private static GarminCloudStore login(GarminCloudStoreTest.Disk disk, AtomicLong clock) throws Exception {
        GarminCloudStore store = open(disk, clock);
        store.finishLogin(store.startLogin(), GarminCloudStoreTest.credentials(OLD));
        return store;
    }
    private static GarminCloudSession.Renewal renewal(AtomicInteger count) {
        return previous -> {
            count.incrementAndGet();
            assertEquals(OLD, previous.token);
            assertEquals("synthetic-refresh", previous.refreshToken);
            return new GarminCloudSession.Credentials(FRESH, "fresh-refresh", GarminCloudAuth.CLIENT_ID, 1800007200000L);
        };
    }

    @Test public void expiryAfterRestartRenewsDurablyWithoutChangingSessionOrReceiptGeneration() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        String session = login(disk, clock).sessionId();
        clock.addAndGet(3600000); // A long workout and process restart crossed expiry.
        GarminCloudStore restarted = open(disk, clock);
        AtomicInteger renewals = new AtomicInteger(), posts = new AtomicInteger();
        GarminCloudClient.Outcome result = GarminCloudPlugin.uploadOnce(restarted, session, "workout", SHA, false, () -> {
            posts.incrementAndGet();
            assertEquals(FRESH, restarted.token());
            return new GarminCloudClient.Outcome("uploaded", "123");
        }, renewal(renewals));
        GarminCloudStore after = open(disk, clock);
        assertEquals("uploaded", result.status);
        assertEquals(FRESH, after.token());
        assertEquals("fresh-refresh", after.refreshToken());
        assertNull(after.csrf());
        assertEquals(session, after.sessionId());
        assertEquals(session, new JSONObject(disk.value).getJSONArray("receipts").getJSONObject(0).getString("generation"));
        assertEquals(1, renewals.get());
        assertEquals(1, posts.get());
        GarminCloudPlugin.uploadOnce(after, session, "next-workout", SHA, false,
            () -> new GarminCloudClient.Outcome("duplicate", null), renewal(renewals));
        assertEquals(1, renewals.get());
        assertFalse(GarminCloudPlugin.status(after).toString().contains("fresh-refresh"));
    }

    @Test public void terminalAndUnknownReceiptsResolveBeforeRenewalEvenWhenExpired() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        String session = store.sessionId();
        store.begin(session, "done", SHA, false);
        store.complete("done", new GarminCloudClient.Outcome("uploaded", "123"));
        store.begin(session, "unknown", SHA, false);
        clock.addAndGet(3600000);
        AtomicInteger renewals = new AtomicInteger(), posts = new AtomicInteger();
        GarminCloudPlugin.Upload send = () -> { posts.incrementAndGet(); return new GarminCloudClient.Outcome("uploaded", "456"); };
        assertEquals("123", GarminCloudPlugin.uploadOnce(store, session, "done", SHA, false, send, renewal(renewals)).activityId);
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, session, "unknown", SHA, false, send, renewal(renewals))).code);
        assertEquals(0, renewals.get());
        assertEquals(0, posts.get());
        assertTrue(store.uncertain("unknown"));
    }

    @Test public void differentRefreshClientCannotReplaceCredentialsOrSendWorkout() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        String session = store.sessionId();
        clock.addAndGet(3600000);
        AtomicInteger posts = new AtomicInteger();
        assertEquals("session_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, session, "workout", SHA, false,
                () -> { posts.incrementAndGet(); return new GarminCloudClient.Outcome("uploaded", "123"); },
                previous -> new GarminCloudSession.Credentials(FRESH, "fresh-refresh", "GARMIN_CONNECT_MOBILE_IOS_DI", 1800007200000L))).code);
        GarminCloudStore after = open(disk, clock);
        assertEquals(OLD, after.token());
        assertEquals(session, after.sessionId());
        assertFalse(after.renewalAvailable());
        assertEquals(0, posts.get());
        assertFalse(after.uncertain("workout"));
    }

    @Test public void failedExpiredPreflightCannotHideAnEarlierAmbiguousUpload() throws Exception {
        for (String failure : new String[]{"network_error", "auth_required", "storage_unavailable", "persistence"}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            AtomicLong clock = new AtomicLong(NOW);
            GarminCloudStore store = login(disk, clock);
            String session = store.sessionId();
            store.begin(session, "unknown", SHA, false);
            clock.addAndGet(3600000);
            AtomicInteger posts = new AtomicInteger(), renewals = new AtomicInteger();
            GarminCloudSession.Renewal failed = previous -> {
                renewals.incrementAndGet();
                if (failure.equals("persistence")) {
                    disk.fail = true;
                    return new GarminCloudSession.Credentials(FRESH, "fresh-refresh", GarminCloudAuth.CLIENT_ID, 1800007200000L);
                }
                throw new GarminCloudClient.Failure(failure);
            };
            assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudPlugin.uploadOnce(store, session, "unknown", SHA, true,
                    () -> { posts.incrementAndGet(); return null; }, failed)).code);
            assertEquals(1, renewals.get());
            assertEquals(0, posts.get());
            disk.fail = false;
            GarminCloudStore restarted = open(disk, clock);
            assertTrue(restarted.uncertain("unknown"));
            assertEquals(session, restarted.sessionId());
            assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudPlugin.uploadOnce(restarted, session, "unknown", SHA, false,
                    () -> { posts.incrementAndGet(); return null; }, renewal(renewals))).code);
            assertEquals(1, renewals.get());
            assertEquals(0, posts.get());
        }
    }

    @Test public void offlineRenewalLeavesCredentialsAndJournalUntouchedAndDoesNotPost() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        clock.addAndGet(3600000);
        String before = disk.value;
        AtomicInteger posts = new AtomicInteger();
        assertEquals("network_error", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, false,
                () -> { posts.incrementAndGet(); return null; },
                previous -> { throw new GarminCloudClient.Failure("network_error"); })).code);
        assertEquals(before, disk.value);
        assertTrue(open(disk, clock).renewalAvailable());
        assertEquals(0, posts.get());
    }

    @Test public void definiteUnauthorizedUploadCanRenewButNeverRepeatsThePost() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        String session = store.sessionId();
        AtomicInteger renewals = new AtomicInteger(), posts = new AtomicInteger();
        assertEquals("upload_failed", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, session, "workout", SHA, false, () -> {
                posts.incrementAndGet();
                return GarminCloudClient.response(401, null, () -> { throw new GarminCloudClient.Failure("auth_required"); });
            }, renewal(renewals))).code);
        assertEquals(1, posts.get());
        assertEquals(1, renewals.get());
        assertEquals(FRESH, open(disk, clock).token());
        assertFalse(open(disk, clock).uncertain("workout"));
        assertEquals(session, open(disk, clock).sessionId());
    }

    @Test public void failedRenewalAfterDefiniteRejectionCannotBecomeAnAutomaticNetworkRetry() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        assertEquals("upload_failed", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, false,
                () -> { throw new GarminCloudClient.Failure("auth_required"); },
                previous -> { throw new GarminCloudClient.Failure("network_error"); })).code);
        assertEquals(OLD, open(disk, clock).token());
        assertTrue(open(disk, clock).renewalAvailable());
        assertFalse(open(disk, clock).uncertain("workout"));
    }

    @Test public void ambiguousPostNeverRenewsOrReplaysAndKeepsItsMarker() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        AtomicInteger renewals = new AtomicInteger(), posts = new AtomicInteger();
        GarminCloudPlugin.Upload send = () -> { posts.incrementAndGet(); throw new GarminCloudClient.Failure("unknown_result"); };
        for (int i = 0; i < 2; i++) assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, false, send, renewal(renewals))).code);
        assertEquals(1, posts.get());
        assertEquals(0, renewals.get());
        assertTrue(open(disk, clock).uncertain("workout"));
    }

    @Test public void explicitRetryUnauthorizedCannotConcealAnEarlierUnknownResult() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        String session = store.sessionId();
        store.begin(session, "workout", SHA, false);
        AtomicInteger renewals = new AtomicInteger(), posts = new AtomicInteger();
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, session, "workout", SHA, true, () -> {
                posts.incrementAndGet(); throw new GarminCloudClient.Failure("auth_required");
            }, renewal(renewals))).code);
        assertEquals(1, posts.get());
        assertEquals(1, renewals.get());
        assertTrue(open(disk, clock).uncertain("workout"));
        assertEquals(session, open(disk, clock).sessionId());
        assertEquals(FRESH, open(disk, clock).token());
        assertEquals("ready", open(disk, clock).authState());
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, session, "workout", SHA, false,
                () -> { fail("No automatic replay"); return null; }, renewal(renewals))).code);
        assertEquals("duplicate", GarminCloudPlugin.uploadOnce(store, session, "workout", SHA, true,
            () -> { posts.incrementAndGet(); assertEquals(FRESH, store.token()); return new GarminCloudClient.Outcome("duplicate", null); },
            renewal(renewals)).status);
        assertEquals(2, posts.get());
        assertEquals(1, renewals.get());
    }

    @Test public void failedAuthenticationPersistenceCannotHideAnEarlierUnknownResult() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        store.begin(store.sessionId(), "workout", SHA, false);
        AtomicInteger renewals = new AtomicInteger();
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, true, () -> {
                disk.fail = true;
                throw new GarminCloudClient.Failure("auth_required");
            }, renewal(renewals))).code);
        assertEquals(0, renewals.get());
        disk.fail = false;
        assertTrue(open(disk, clock).uncertain("workout"));
    }

    @Test public void readOnlyMetricRetriesOnceAfterConfirmedUnauthorizedSession() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        AtomicInteger renewals = new AtomicInteger(), gets = new AtomicInteger();
        GarminHealthClient client = new GarminHealthClient((url, token, csrf) -> {
            gets.incrementAndGet();
            return new GarminHealthClient.Response(token.equals(OLD) ? 401 : 200, "{\"reading\":42}");
        });
        JSONObject result = GarminCloudPlugin.readHealthOnce(store, store.sessionId(), "2026-01-02", "weight", client, renewal(renewals));
        assertEquals("available", result.getString("status"));
        assertEquals(1, renewals.get());
        assertEquals(3, gets.get()); // Rejected metric, authoritative account probe, one repeated metric.
        assertEquals(FRESH, open(disk, clock).token());
    }

    @Test public void repeatedUnauthorizedReadCannotLoopOrEraseCredentials() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        AtomicInteger renewals = new AtomicInteger(), gets = new AtomicInteger();
        GarminHealthClient client = new GarminHealthClient((url, token, csrf) -> {
            gets.incrementAndGet(); return new GarminHealthClient.Response(401, null);
        });
        assertEquals("auth_required", GarminCloudPlugin.readHealthOnce(store, store.sessionId(), "2026-01-02", "weight",
            client, renewal(renewals)).getString("error"));
        assertEquals(1, renewals.get());
        assertEquals(4, gets.get());
        assertEquals(FRESH, open(disk, clock).token());
        assertFalse(open(disk, clock).renewalAvailable());
    }

    @Test public void expiredReadRenewsBeforeFirstGetAndDoesNotRefreshAgainOn401() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        clock.addAndGet(3600000);
        AtomicInteger renewals = new AtomicInteger(), gets = new AtomicInteger();
        GarminHealthClient client = new GarminHealthClient((url, token, csrf) -> {
            gets.incrementAndGet(); assertEquals(FRESH, token); return new GarminHealthClient.Response(401, null);
        });
        assertEquals("auth_required", GarminCloudPlugin.readHealthOnce(store, store.sessionId(), "2026-01-02", "weight",
            client, renewal(renewals)).getString("error"));
        assertEquals(1, renewals.get());
        assertEquals(2, gets.get());
    }

    @Test public void logoutOrNewLoginDuringRenewalCannotResurrectTheOldSession() throws Exception {
        for (boolean newerLogin : new boolean[]{false, true}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            AtomicLong clock = new AtomicLong(NOW);
            GarminCloudStore stale = login(disk, clock);
            String oldSession = stale.sessionId();
            clock.addAndGet(3600000);
            assertEquals("auth_required", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudSession.ready(stale, oldSession, previous -> {
                    try {
                        GarminCloudStore current = open(disk, clock);
                        current.disconnect();
                        if (newerLogin) current.finishLogin(current.startLogin(), new GarminCloudSession.Credentials(FRESH, "new-account-refresh", GarminCloudAuth.CLIENT_ID, 1800007200000L));
                    } catch (Exception failure) { throw new AssertionError(failure); }
                    return new GarminCloudSession.Credentials(FRESH, "fresh-refresh", GarminCloudAuth.CLIENT_ID, 1800007200000L);
                }, false)).code);
            GarminCloudStore current = open(disk, clock);
            assertEquals(newerLogin, current.connected());
            assertNotEquals(oldSession, current.sessionId());
            if (newerLogin) assertEquals("new-account-refresh", current.refreshToken());
        }
    }

    @Test public void staleConcurrentRenewalCannotReplaceANewerToken() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        String session = store.sessionId();
        GarminCloudStore stale = open(disk, clock);
        store.finishRenewal(session, GarminCloudStoreTest.credentials(OLD), new GarminCloudSession.Credentials(FRESH, "fresh-refresh", GarminCloudAuth.CLIENT_ID, 1800007200000L));
        assertEquals("cancelled", assertThrows(GarminCloudClient.Failure.class,
            () -> stale.finishRenewal(session, GarminCloudStoreTest.credentials(OLD), new GarminCloudSession.Credentials(token(1800010000), "stale-refresh", GarminCloudAuth.CLIENT_ID, 1800010000000L))).code);
        assertEquals(FRESH, open(disk, clock).token());
        assertEquals("fresh-refresh", open(disk, clock).refreshToken());
    }

    @Test public void revokedOperationCannotRenewCommitOrPostEvenBeforeDurableDisconnectRuns() throws Exception {
        for (boolean revokeDuringFetch : new boolean[]{false, true}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            AtomicLong clock = new AtomicLong(NOW);
            GarminCloudStore store = login(disk, clock);
            if (revokeDuringFetch) clock.addAndGet(3600000);
            String before = disk.value;
            AtomicInteger posts = new AtomicInteger();
            GarminCloudSession.Renewal revoked = new GarminCloudSession.Renewal() {
                boolean cancelled = !revokeDuringFetch;
                @Override public GarminCloudSession.Credentials fetch(GarminCloudSession.Credentials previous) {
                    cancelled = true;
                    return new GarminCloudSession.Credentials(FRESH, "fresh-refresh", GarminCloudAuth.CLIENT_ID, 1800007200000L);
                }
                @Override public void check() throws GarminCloudClient.Failure {
                    if (cancelled) throw new GarminCloudClient.Failure("cancelled");
                }
            };
            assertEquals("cancelled", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, false,
                    () -> { posts.incrementAndGet(); return null; }, revoked)).code);
            assertEquals(0, posts.get());
            assertEquals(before, disk.value);
        }
    }

    @Test public void failedRenewalPersistenceCannotPermitAPost() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        clock.addAndGet(3600000);
        String before = disk.value;
        disk.fail = true;
        AtomicInteger posts = new AtomicInteger();
        assertThrows(java.io.IOException.class, () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, false,
            () -> { posts.incrementAndGet(); return null; }, renewal(new AtomicInteger())));
        assertEquals(0, posts.get());
        assertEquals(before, disk.value);
    }

    @Test public void rotatedRefreshGrantFencesAStaleResultEvenWhenAccessTokenDidNotChange() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong clock = new AtomicLong(NOW);
        GarminCloudStore store = login(disk, clock);
        String session = store.sessionId();
        GarminCloudStore stale = open(disk, clock);
        GarminCloudSession.Credentials previous = store.credentials();
        store.finishRenewal(session, previous,
            new GarminCloudSession.Credentials(OLD, "rotated-refresh", GarminCloudAuth.CLIENT_ID, 1800007200000L));
        assertEquals("cancelled", assertThrows(GarminCloudClient.Failure.class,
            () -> stale.finishRenewal(session, previous,
                new GarminCloudSession.Credentials(FRESH, "stale-refresh", GarminCloudAuth.CLIENT_ID, 1800007200000L))).code);
        assertEquals(OLD, open(disk, clock).token());
        assertEquals("rotated-refresh", open(disk, clock).refreshToken());
        assertEquals(session, open(disk, clock).sessionId());
    }
}
