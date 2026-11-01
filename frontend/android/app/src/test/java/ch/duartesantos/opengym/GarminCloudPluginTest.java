package ch.duartesantos.opengym;

import org.junit.Test;
import static org.junit.Assert.*;

public class GarminCloudPluginTest {
    private static final String TOKEN = "synthetic.payload.signature";
    private static final String SHA = "a".repeat(64);

    private GarminCloudStore connected(GarminCloudStoreTest.Disk disk) throws Exception {
        GarminCloudStore store = new GarminCloudStore(disk);
        store.login(TOKEN, "synthetic-csrf");
        return store;
    }

    private String failure(GarminCloudStore store, int status, boolean wasUnknown) {
        GarminCloudClient.Failure failure = assertThrows(GarminCloudClient.Failure.class,
            () -> GarminCloudClient.response(status, "synthetic response"));
        return GarminCloudPlugin.recordUploadFailure(store, "workout", wasUnknown, failure);
    }

    @Test public void forbiddenUploadPreservesCredentialsAndAllowsDefiniteFailureRetry() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        store.begin(session, "workout", SHA, false);
        assertEquals("upload_failed", failure(store, 403, false));
        GarminCloudStore restarted = new GarminCloudStore(disk);
        assertTrue(restarted.connected());
        assertEquals(session, restarted.sessionId());
        assertEquals(TOKEN, restarted.token());
        assertEquals("synthetic-csrf", restarted.csrf());
        assertFalse(restarted.uncertain("workout"));
        assertNull(restarted.begin(session, "workout", SHA, false));
    }

    @Test public void forbiddenRetryCannotRemoveAnEarlierUnknownReceipt() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        store.begin(session, "workout", SHA, false);
        GarminCloudStore restarted = new GarminCloudStore(disk);
        restarted.begin(session, "workout", SHA, true);
        assertEquals("unknown_result", failure(restarted, 403, true));
        GarminCloudStore after = new GarminCloudStore(disk);
        assertEquals(session, after.sessionId());
        assertTrue(after.uncertain("workout"));
        assertEquals("unknown_result", assertThrows(GarminCloudClient.Failure.class,
            () -> after.begin(session, "workout", SHA, false)).code);
    }

    @Test public void unauthorizedUploadStillInvalidatesCredentialsDurably() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        store.begin(store.sessionId(), "workout", SHA, false);
        assertEquals("auth_required", failure(store, 401, false));
        GarminCloudStore restarted = new GarminCloudStore(disk);
        assertFalse(restarted.connected());
        assertNull(restarted.token());
        assertFalse(restarted.uncertain("workout"));
    }

    @Test public void unauthorizedRetryRetainsUnknownReceiptAcrossNewLogin() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        String original = store.sessionId();
        store.begin(original, "workout", SHA, false);
        assertEquals("auth_required", failure(store, 401, true));
        GarminCloudStore restarted = new GarminCloudStore(disk);
        assertFalse(restarted.connected());
        assertTrue(restarted.uncertain("workout"));
        restarted.login(TOKEN, null);
        assertEquals("session_changed", assertThrows(GarminCloudClient.Failure.class,
            () -> restarted.begin(restarted.sessionId(), "workout", SHA, true)).code);
    }

    @Test public void ambiguousResponseAndFailedJournalWritePreserveSessionAndUnknownReceipt() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        store.begin(session, "workout", SHA, false);
        assertEquals("unknown_result", failure(store, 503, false));
        disk.fail = true;
        assertEquals("unknown_result", failure(store, 403, false));
        disk.fail = false;
        GarminCloudStore restarted = new GarminCloudStore(disk);
        assertEquals(session, restarted.sessionId());
        assertTrue(restarted.uncertain("workout"));
    }

}
