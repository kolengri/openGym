package ch.duartesantos.opengym;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import java.io.IOException;
import static org.junit.Assert.*;

public class GarminLinkStoreTest {
    static final String SNAPSHOT = "{\"v\":1,\"unit\":\"kg\",\"active\":null}";

    static final class Disk implements GarminLinkStore.Storage {
        String saved;
        boolean fail;
        @Override public String read() { return saved; }
        @Override public void write(String value) throws Exception {
            if (fail) throw new IOException("Simulated storage failure");
            saved = value;
        }
    }

    static JSONObject event(int counter) throws Exception {
        return new JSONObject().put("id", "installation:" + counter).put("wid", "session")
            .put("type", "setDone").put("at", 1_800_000_000_000L + counter)
            .put("exId", "squat").put("entryIdx", 0).put("setIdx", 0).put("w", 50).put("r", 5);
    }

    private static GarminLinkStore enabled(Disk disk) throws Exception {
        GarminLinkStore store = new GarminLinkStore(disk);
        assertFalse(store.enabled());
        store.configure(true, "123"); // Synthetic, not a physical Garmin identifier.
        return store;
    }

    @Test public void receiptSurvivesRestartWithoutAcknowledgingOrSendingStaleSnapshot() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        store.setSnapshot(SNAPSHOT);
        store.receive(new JSONArray().put(event(1)));
        GarminLinkStore restarted = new GarminLinkStore(disk);
        assertEquals(1, restarted.events().length());
        assertEquals(0, restarted.ackPackets().length());
        assertNull(restarted.snapshot());
        assertFalse(restarted.receive(new JSONArray().put(event(1))));
        assertEquals(1, restarted.events().length());
    }

    @Test public void acknowledgementPersistsSnapshotFenceAndReplaysLostAckAfterRestart() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        store.setSnapshot(SNAPSHOT);
        store.receive(new JSONArray().put(event(1)).put(event(2)));
        store.acknowledge(new JSONArray().put("installation:1").put("installation:2"), SNAPSHOT);
        GarminLinkStore restarted = new GarminLinkStore(disk);
        assertEquals(0, restarted.events().length());
        JSONObject ack = restarted.ackPackets().getJSONObject(0);
        assertEquals("ack", ack.getString("kind"));
        assertEquals(2, ack.getJSONArray("ids").length());
        assertEquals(restarted.snapshot().getLong("seq"), ack.getLong("seq"));
        assertEquals(restarted.snapshot().getJSONObject("state").toString(), ack.getJSONObject("state").toString());
        assertFalse(restarted.receive(new JSONArray().put(event(1))));
        assertEquals(0, restarted.events().length());
        // A lost plugin response can retry the same acknowledgement as well.
        restarted.acknowledge(new JSONArray().put("installation:1"), SNAPSHOT);
        assertEquals(0, restarted.events().length());
    }

    @Test public void failedPersistenceKeepsCommandsAndProducesNoAcknowledgement() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        store.receive(new JSONArray().put(event(1)));
        String before = disk.saved;
        disk.fail = true;
        assertThrows(IOException.class, () -> store.acknowledge(new JSONArray().put("installation:1"), SNAPSHOT));
        assertEquals(before, disk.saved);
        assertEquals(1, store.events().length());
        assertEquals(0, store.ackPackets().length());
        assertThrows(IOException.class, () -> store.receive(new JSONArray().put(event(2))));
        assertEquals(1, store.events().length());
    }

    @Test public void switchingDevicesOrDisablingClearsSessionButPreservesIncreasingSequence() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        long seq = store.setSnapshot(SNAPSHOT).getLong("seq");
        store.receive(new JSONArray().put(event(1)));
        store.configure(true, "456");
        assertNull(store.snapshot());
        assertEquals(0, store.events().length());
        assertEquals(0, store.ackPackets().length());
        assertTrue(store.setSnapshot(SNAPSHOT).getLong("seq") > seq);
        store.configure(false, null);
        assertFalse(new GarminLinkStore(disk).enabled());
        assertNull(store.snapshot());
        assertThrows(IllegalStateException.class, () -> store.setSnapshot(SNAPSHOT));
        assertThrows(IllegalStateException.class, () -> store.receive(new JSONArray().put(event(2))));
    }

    @Test public void queueOverflowRejectsEntireBatchWithoutDroppingCommands() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        for (int first = 0; first < GarminLinkStore.MAX_EVENTS; first += GarminProtocol.MAX_BATCH) {
            JSONArray batch = new JSONArray();
            for (int i = first; i < first + GarminProtocol.MAX_BATCH; i++) batch.put(event(i));
            store.receive(batch);
        }
        String before = disk.saved;
        assertThrows(IllegalStateException.class, () -> store.receive(new JSONArray().put(event(999))));
        assertEquals(before, disk.saved);
        assertEquals(GarminLinkStore.MAX_EVENTS, new GarminLinkStore(disk).events().length());
    }

    @Test public void malformedBatchIsAtomicAndUnknownIdsCannotBeAcknowledged() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        JSONObject invalid = event(2).put("entryIdx", -1);
        assertThrows(IllegalArgumentException.class, () -> store.receive(new JSONArray().put(event(1)).put(invalid)));
        assertEquals(0, store.events().length());
        assertThrows(IllegalArgumentException.class, () -> store.acknowledge(new JSONArray().put("missing"), SNAPSHOT));
        assertEquals(0, store.ackPackets().length());
    }

    @Test public void oldWorkoutCommandsArePreservedForStoreLevelRejectionAndCanArriveOutOfOrder() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        store.receive(new JSONArray().put(event(3).put("wid", "previous-session")).put(event(1)));
        assertEquals("installation:3", store.events().getJSONObject(0).getString("id"));
        assertEquals("previous-session", store.events().getJSONObject(0).getString("wid"));
        store.acknowledge(new JSONArray().put("installation:3"), SNAPSHOT);
        assertEquals("installation:1", store.events().getJSONObject(0).getString("id"));
        assertNull(store.snapshot());
    }

    @Test public void invalidSnapshotDoesNotConsumeCommands() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        store.receive(new JSONArray().put(event(1)));
        String before = disk.saved;
        assertThrows(Exception.class, () -> store.acknowledge(new JSONArray().put("installation:1"), "{\"v\":2}"));
        assertEquals(before, disk.saved);
        assertEquals(1, store.events().length());
    }

    @Test public void acknowledgementHistoryChunksKeepOneCausalFence() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        JSONArray events = new JSONArray(), ids = new JSONArray();
        for (int first = 0; first < 64; first += GarminProtocol.MAX_BATCH) {
            events = new JSONArray();
            for (int i = first; i < first + GarminProtocol.MAX_BATCH; i++) {
                events.put(event(i));
                ids.put("installation:" + i);
            }
            store.receive(events);
        }
        store.acknowledge(ids, SNAPSHOT);
        JSONArray packets = new GarminLinkStore(disk).ackPackets();
        assertEquals(2, packets.length());
        for (int i = 0; i < packets.length(); i++) {
            JSONObject packet = packets.getJSONObject(i);
            assertEquals(store.snapshot().getLong("seq"), packet.getLong("seq"));
            assertEquals(32, packet.getJSONArray("ids").length());
            GarminProtocol.wire(packet);
        }
        JSONArray selective = store.ackPacketsFor(new JSONArray().put("installation:63").put("not-received"));
        assertEquals(1, selective.length());
        assertEquals(1, selective.getJSONObject(0).getJSONArray("ids").length());
        assertEquals("installation:63", selective.getJSONObject(0).getJSONArray("ids").getString(0));
    }

    @Test public void corruptedStorageDoesNotSilentlyResetPendingCommands() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = enabled(disk);
        store.receive(new JSONArray().put(event(1)));
        JSONObject damaged = new JSONObject(disk.saved).put("seq", -1);
        disk.saved = damaged.toString();
        assertThrows(IllegalStateException.class, () -> new GarminLinkStore(disk));
        assertEquals(damaged.toString(), disk.saved);
    }
}
