package ch.duartesantos.opengym;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.Test;
import static org.junit.Assert.*;

public class GarminCloudAuthTest {
    private static final long NOW = 1_800_000_000_000L;
    private static final String SHA = "a".repeat(64);
    private static String token(String payload) {
        return "e30." + Base64.getUrlEncoder().withoutPadding().encodeToString(payload.getBytes(StandardCharsets.UTF_8)) + ".synthetic";
    }
    private static String state(String payload, long now) {
        return GarminCloudClient.authState(token(payload), now, Base64.getUrlDecoder()::decode);
    }
    private static GarminCloudStore store(GarminCloudStoreTest.Disk disk, AtomicLong now) throws Exception {
        return new GarminCloudStore(disk, now::get, Base64.getUrlDecoder()::decode);
    }

    @Test public void readsNumericDateInSecondsIncludingItsExactExpiryBoundary() {
        assertEquals("ready", state("{\"exp\":1800000001}", NOW));
        assertEquals("expired", state("{\"exp\":1800000000}", NOW));
        assertEquals("ready", state("{\"exp\":1800000000.5}", NOW));
        assertEquals("expired", state("{\"exp\":1800000000.5}", NOW + 500));
        assertEquals("expired", state("{\"exp\":-1}", NOW));
    }

    @Test public void missingMalformedOrOversizedClaimsNeverPretendToBeReady() {
        for (String payload : new String[]{"{}", "{\"exp\":null}", "{\"exp\":\"1800000001\"}",
                "{broken", "{\"exp\":[]}", "{\"exp\":1800000001,\"x\":\"" + "x".repeat(8192) + "\"}"})
            assertEquals("unknown", state(payload, NOW));
        assertEquals("unknown", GarminCloudClient.authState("e30.a.synthetic", NOW, Base64.getUrlDecoder()::decode));
        assertEquals("missing", GarminCloudClient.authState(null, NOW, Base64.getUrlDecoder()::decode));
    }

    @Test public void knownExpiredSessionCannotCreateAPostMarkerOrForgetCredentials() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong now = new AtomicLong(NOW);
        GarminCloudStore store = store(disk, now);
        store.login(token("{\"exp\":1800000000}"), null);
        String before = disk.value;
        AtomicInteger posts = new AtomicInteger();
        assertEquals("auth_expired", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, false,
                () -> { posts.incrementAndGet(); return new GarminCloudClient.Outcome("uploaded", "123"); })).code);
        assertEquals(0, posts.get());
        assertEquals(before, disk.value);
        assertFalse(store.uncertain("workout"));
        assertTrue(store.connected());
        assertEquals("expired", GarminCloudPlugin.status(store).getString("authState"));
        assertTrue(GarminCloudPlugin.status(store).getBoolean("connected"));
        assertFalse(GarminCloudPlugin.status(store).has("error"));
        assertFalse(GarminCloudPlugin.status(store).toString().contains(store.token()));
    }

    @Test public void expiryDuringSuccessfulPostStillPersistsAndReconcilesTheTerminalReceipt() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong now = new AtomicLong(NOW);
        GarminCloudStore store = store(disk, now);
        store.login(token("{\"exp\":1800000001}"), null);
        String session = store.sessionId();
        AtomicInteger posts = new AtomicInteger();
        GarminCloudPlugin.uploadOnce(store, session, "workout", SHA, false, () -> {
            posts.incrementAndGet();
            now.addAndGet(2000); // The simulated POST crossed the local expiry boundary.
            return new GarminCloudClient.Outcome("uploaded", "123");
        });
        GarminCloudStore restarted = store(disk, now);
        assertEquals("expired", restarted.authState());
        GarminCloudClient.Outcome receipt = GarminCloudPlugin.uploadOnce(restarted, session, "workout", SHA, false,
            () -> { posts.incrementAndGet(); return new GarminCloudClient.Outcome("uploaded", "456"); });
        assertEquals(1, posts.get());
        assertEquals("uploaded", receipt.status);
        assertEquals("123", receipt.activityId);
        assertEquals("content_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> restarted.begin(session, "workout", "b".repeat(64), false)).code);
    }

    @Test public void expiryCannotClearAnEarlierAmbiguousReceiptOrOverrideGenerationFences() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong now = new AtomicLong(NOW);
        GarminCloudStore store = store(disk, now);
        store.login(token("{\"exp\":1800000001}"), null);
        String session = store.sessionId();
        store.begin(session, "workout", SHA, false);
        now.addAndGet(2000);
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> store.begin(session, "workout", SHA, false)).code);
        assertEquals("auth_expired", assertThrows(GarminCloudClient.Failure.class,
            () -> store.begin(session, "workout", SHA, true)).code);
        assertTrue(store.uncertain("workout"));
        store.login(token("{\"exp\":1800000001}"), null);
        assertEquals("session_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> store.begin(store.sessionId(), "workout", SHA, true)).code);
    }

    @Test public void malformedSuccessCannotPermitAnAutomaticSecondPost() throws Exception {
        for (int status : new int[]{200, 202}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            GarminCloudStore store = store(disk, new AtomicLong(NOW));
            store.login(token("{\"exp\":1800000001}"), null);
            AtomicInteger posts = new AtomicInteger();
            GarminCloudPlugin.Upload send = () -> {
                posts.incrementAndGet();
                return GarminCloudClient.response(status, "{malformed");
            };
            assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, false, send)).code);
            assertTrue(store.uncertain("workout"));
            assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "workout", SHA, false, send)).code);
            assertEquals(1, posts.get());
        }
    }

    @Test public void expiryDoesNotHideAFullReceiptJournalBehindReauthenticationAdvice() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        AtomicLong now = new AtomicLong(NOW);
        GarminCloudStore store = store(disk, now);
        store.login(token("{\"exp\":1800000001}"), null);
        for (int i = 0; i < GarminCloudStore.MAX_RECEIPTS; i++) store.begin(store.sessionId(), "workout-" + i, SHA, false);
        now.addAndGet(2000);
        assertEquals("receipt_limit", assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudPlugin.uploadOnce(store, store.sessionId(), "new-workout", SHA, false,
                () -> { fail("A full journal must never permit a POST"); return null; })).code);
    }
}
