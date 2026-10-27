package ch.duartesantos.opengym;

import org.json.JSONObject;
import org.junit.Test;
import java.io.IOException;
import static org.junit.Assert.*;

public class GarminCloudStoreTest {
    private static final String TOKEN = "synthetic.payload.signature";
    private static final String SHA = "a".repeat(64);
    private static final String OTHER_SHA = "b".repeat(64);

    static final class Disk implements GarminCloudStore.Storage {
        String value;
        boolean fail;
        @Override public String read() { return value; }
        @Override public void write(String value) throws Exception {
            if (fail) throw new IOException("Synthetic disk failure");
            this.value = value;
        }
        @Override public void clear() throws Exception {
            if (fail) throw new IOException("Synthetic disk failure");
            value = null;
        }
    }

    private GarminCloudStore connected(Disk disk) throws Exception {
        GarminCloudStore store = new GarminCloudStore(disk);
        store.login(TOKEN, null);
        return store;
    }

    @Test public void loginSessionSurvivesRestartAndRotatesAfterNewLogin() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        assertTrue(store.connected());
        assertTrue(GarminCloudStore.validSession(session));
        assertFalse(session.contains("synthetic"));
        GarminCloudStore restarted = new GarminCloudStore(disk);
        assertEquals(session, restarted.sessionId());
        restarted.login(TOKEN, "csrf");
        assertNotEquals(session, restarted.sessionId());
        assertEquals("csrf", restarted.csrf());
    }

    @Test public void durableReceiptPreventsPostAfterLostCallbackAndRejectsChangedContent() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        assertNull(store.begin(session, "synthetic-workout", SHA, false));
        store.complete("synthetic-workout", new GarminCloudClient.Outcome("uploaded", "12345"));
        GarminCloudStore restarted = new GarminCloudStore(disk);
        GarminCloudClient.Outcome receipt = restarted.begin(session, "synthetic-workout", SHA, false);
        assertEquals("uploaded", receipt.status);
        assertEquals("12345", receipt.activityId);
        assertEquals("content_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> restarted.begin(session, "synthetic-workout", OTHER_SHA, true)).code);
        assertFalse(disk.value.contains("synthetic-workout")); // Persist hashes rather than workout identifiers.
    }

    @Test public void uncertaintySurvivesRestartAndRequiresExplicitSameFitRetry() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        store.begin(session, "workout", SHA, false);
        GarminCloudStore restarted = new GarminCloudStore(disk);
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> restarted.begin(session, "workout", SHA, false)).code);
        assertEquals("content_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> restarted.begin(session, "workout", OTHER_SHA, true)).code);
        assertNull(restarted.begin(session, "workout", SHA, true));
        assertTrue(restarted.uncertain("workout"));
        restarted.complete("workout", new GarminCloudClient.Outcome("duplicate", null));
        assertEquals("duplicate", new GarminCloudStore(disk).begin(session, "workout", SHA, false).status);
    }

    @Test public void staleSessionCanNeverReuseOrCreateAReceiptForAnotherLogin() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String old = store.sessionId();
        store.begin(old, "workout", SHA, false);
        store.complete("workout", new GarminCloudClient.Outcome("uploaded", "123"));
        store.login(TOKEN, null);
        assertEquals("auth_required", assertThrows(GarminCloudClient.Failure.class,
            () -> store.begin(old, "workout", SHA, true)).code);
        assertEquals("session_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> store.begin(store.sessionId(), "workout", SHA, true)).code);
        assertNull(store.begin(store.sessionId(), "new-workout", SHA, false));
    }

    @Test public void definitelyRejectedRequestCanRetryAndExpiredAuthNeedsLogin() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        store.begin(session, "workout", SHA, false);
        store.definitelyFailed("workout");
        assertNull(store.begin(session, "workout", SHA, false));
        store.invalidate();
        assertFalse(store.connected());
        assertFalse(disk.value.contains(TOKEN));
        assertEquals("auth_required", assertThrows(GarminCloudClient.Failure.class,
            () -> store.begin(session, "workout", SHA, true)).code);
    }

    @Test public void failedMarkerPersistenceDoesNotPermitSending() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String before = disk.value;
        disk.fail = true;
        assertThrows(IOException.class, () -> store.begin(store.sessionId(), "workout", SHA, false));
        assertEquals(before, disk.value);
        disk.fail = false;
        assertNull(store.begin(store.sessionId(), "workout", SHA, false));
    }

    @Test public void failedReceiptPersistenceLeavesDurableUnknownMarker() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        store.begin(session, "workout", SHA, false);
        disk.fail = true;
        assertThrows(IOException.class, () -> store.complete("workout", new GarminCloudClient.Outcome("uploaded", "123")));
        disk.fail = false;
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> new GarminCloudStore(disk).begin(session, "workout", SHA, false)).code);
    }

    @Test public void boundedLedgerNeverEvictsAnAmbiguousRequest() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        for (int i = 0; i < GarminCloudStore.MAX_RECEIPTS; i++) store.begin(session, "workout-" + i, SHA, false);
        assertThrows(GarminCloudClient.Failure.class, () -> store.begin(session, "overflow", SHA, false));
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> store.begin(session, "workout-0", SHA, false)).code);
        store.complete("workout-100", new GarminCloudClient.Outcome("uploaded", "123"));
        assertEquals("receipt_limit", assertThrows(GarminCloudClient.Failure.class,
            () -> store.begin(session, "overflow", SHA, false)).code);
        assertEquals("uploaded", store.begin(session, "workout-100", SHA, false).status);
        assertEquals(GarminCloudStore.MAX_RECEIPTS, new JSONObject(disk.value).getJSONArray("receipts").length());
    }

    @Test public void disconnectRemovesCredentialsAndBindingAndCorruptionFailsClosed() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        store.disconnect();
        assertNotNull(disk.value);
        assertFalse(store.connected());
        assertNull(store.sessionId());
        disk.value = "{broken";
        assertThrows(Exception.class, () -> new GarminCloudStore(disk));
        assertEquals("{broken", disk.value);
    }

    @Test public void validatesBoundaryIdentifiersAndCredentials() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        for (String workout : new String[]{"", "a".repeat(129), "bad\nidentifier", "bad\nmultiple\ncontrols"})
            assertThrows(GarminCloudClient.Failure.class, () -> store.begin(store.sessionId(), workout, SHA, false));
        assertThrows(GarminCloudClient.Failure.class, () -> store.login("invalid", null));
        assertThrows(GarminCloudClient.Failure.class, () -> store.login(TOKEN, "bad;cookie"));
    }
    @Test public void unknownReceiptSurvivesDisconnectReloginAndCannotCrossGenerations() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String original = store.sessionId();
        store.begin(original, "unknown", SHA, false);
        store.disconnect();
        assertFalse(store.connected());
        assertTrue(new GarminCloudStore(disk).uncertain("unknown"));
        store = new GarminCloudStore(disk);
        store.login(TOKEN, null);
        GarminCloudStore active = new GarminCloudStore(disk);
        for (boolean retry : new boolean[]{false, true}) {
            assertEquals("session_changed", assertThrows(GarminCloudClient.Failure.class,
                () -> active.begin(active.sessionId(), "unknown", SHA, retry)).code);
            assertEquals("content_changed", assertThrows(GarminCloudClient.Failure.class,
                () -> active.begin(active.sessionId(), "unknown", OTHER_SHA, retry)).code);
        }
        assertEquals(original, new JSONObject(disk.value).getJSONArray("receipts").getJSONObject(0).getString("generation"));
        assertNull(active.begin(active.sessionId(), "fresh", SHA, false));
    }

    @Test public void expiredCredentialReloginRetainsUnknownGuardAndLegacyReceiptsMigrate() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String original = store.sessionId();
        store.begin(original, "legacy", SHA, false);
        JSONObject legacy = new JSONObject(disk.value);
        legacy.getJSONArray("receipts").getJSONObject(0).remove("generation");
        disk.value = legacy.toString();
        GarminCloudStore restarted = new GarminCloudStore(disk);
        restarted.invalidate();
        restarted.login(TOKEN, null);
        assertEquals("session_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> restarted.begin(restarted.sessionId(), "legacy", SHA, true)).code);
        assertEquals(original, new JSONObject(disk.value).getJSONArray("receipts").getJSONObject(0).getString("generation"));
    }

    @Test public void cancelledLoginNonceCannotSaveAfterDisconnectOrANewerLogin() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String first = store.startLogin();
        assertTrue(new GarminCloudStore(disk).pendingLogin(first));
        store.disconnect();
        GarminCloudStore restarted = new GarminCloudStore(disk);
        assertEquals("cancelled", assertThrows(GarminCloudClient.Failure.class,
            () -> restarted.finishLogin(first, TOKEN, null)).code);
        String second = restarted.startLogin();
        assertNotEquals(first, second);
        assertEquals("cancelled", assertThrows(GarminCloudClient.Failure.class,
            () -> restarted.finishLogin(first, TOKEN, null)).code);
        restarted.finishLogin(second, TOKEN, null);
        String activeSession = restarted.sessionId();
        assertTrue(new GarminCloudStore(disk).loginResultMatches(second));
        assertFalse(restarted.loginResultMatches(first));
        restarted.cancelLogin(first); // Delayed cancellation from the old Activity cannot revoke the new login.
        assertEquals(activeSession, restarted.sessionId());
        restarted.disconnect();
        assertFalse(new GarminCloudStore(disk).loginResultMatches(second));
    }

    @Test public void configurationRestartRetainsNonceButANewerLoginRevokesDelayedSuccess() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String first = store.startLogin();
        GarminCloudStore recreated = new GarminCloudStore(disk);
        recreated.finishLogin(first, TOKEN, null);
        assertTrue(new GarminCloudStore(disk).loginResultMatches(first));
        String second = recreated.startLogin();
        assertFalse(new GarminCloudStore(disk).loginResultMatches(first));
        recreated.finishLogin(second, TOKEN, null);
        assertFalse(recreated.loginResultMatches(first));
        recreated.cancelLogin(second);
        assertFalse(new GarminCloudStore(disk).connected());
    }

    @Test public void unreadableArchiveAndFailedCancellationNeverClearOrReplaceTheJournal() throws Exception {
        Disk disk = new Disk();
        disk.value = "{broken-private-journal";
        String before = disk.value;
        assertThrows(Exception.class, () -> new GarminCloudStore(disk));
        assertEquals(before, disk.value);
        disk.value = null;
        GarminCloudStore store = connected(disk);
        store.begin(store.sessionId(), "guard", SHA, false);
        String nonce = store.startLogin();
        before = disk.value;
        disk.fail = true;
        assertThrows(IOException.class, store::disconnect);
        assertEquals(before, disk.value);
        disk.fail = false;
        store.disconnect();
        assertEquals("cancelled", assertThrows(GarminCloudClient.Failure.class,
            () -> store.finishLogin(nonce, TOKEN, null)).code);
        assertTrue(new GarminCloudStore(disk).uncertain("guard"));
    }

    @Test public void completionAndDefiniteFailureCannotConsumeAnotherGenerationsReceipt() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        store.begin(store.sessionId(), "old", SHA, false);
        store.login(TOKEN, null);
        assertEquals("session_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> store.complete("old", new GarminCloudClient.Outcome("uploaded", "123"))).code);
        assertEquals("session_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> store.definitelyFailed("old")).code);
        assertTrue(new GarminCloudStore(disk).uncertain("old"));
    }

    @Test public void delayedCallbackNonceCannotMatchTheNewestOriginatingCall() throws Exception {
        Disk disk = new Disk();
        GarminCloudStore store = connected(disk);
        String oldCall = store.startLogin();
        store.disconnect();
        String newCall = store.startLogin();
        assertFalse(GarminCloudStore.sameLoginNonce(oldCall, newCall));
        assertFalse(GarminCloudStore.sameLoginNonce(null, newCall));
        assertFalse(GarminCloudStore.sameLoginNonce("", ""));
        assertTrue(GarminCloudStore.sameLoginNonce(newCall, newCall));
        store.finishLogin(newCall, TOKEN, null);
        assertTrue(store.loginResultMatches(newCall));
        assertFalse(store.loginResultMatches(oldCall));
    }

}
