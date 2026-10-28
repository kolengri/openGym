package ch.duartesantos.opengym;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import java.util.HashMap;
import java.util.Map;
import static org.junit.Assert.*;

public class GarminLinkTelemetryTest {
    private static JSONObject target(long seq, String wid) throws Exception {
        return new JSONObject().put("seq", seq).put("wid", wid == null ? JSONObject.NULL : wid);
    }

    private static JSONObject hello(long seq, String wid, int pending) throws Exception {
        return target(seq, wid).put("v", 1).put("kind", "hello").put("pending", pending);
    }

    private static JSONObject incoming(Map<String, Object> source) throws Exception {
        return GarminProtocol.incoming(source);
    }

    private static Map<String, Object> helloMap() {
        Map<String, Object> source = new HashMap<>();
        source.put("v", 1); source.put("kind", "hello");
        return source;
    }

    @Test public void onlyExactSequenceSameWorkoutAndBothEmptyQueuesConfirm() throws Exception {
        JSONObject wanted = target(10, "workout-a");
        for (long seq : new long[] { -1, 9, 10, 11 }) {
            for (String wid : new String[] { null, "workout-a", "workout-b" }) {
                for (int phonePending : new int[] { 0, 1, 256 }) {
                    for (int watchPending : new int[] { 0, 1, 256 }) {
                        GarminLinkTelemetry telemetry = new GarminLinkTelemetry();
                        telemetry.receive(hello(seq, wid, watchPending), wanted, phonePending, 100);
                        JSONObject status = telemetry.status(wanted, phonePending);
                        boolean expected = seq == 10 && "workout-a".equals(wid) && phonePending == 0 && watchPending == 0;
                        assertEquals("seq=" + seq + ", wid=" + wid + ", phone=" + phonePending + ", watch=" + watchPending,
                            expected, status.getBoolean("snapshotConfirmed"));
                        assertEquals(expected ? 100 : 0, status.getLong("lastConfirmedAt"));
                    }
                }
            }
        }
    }

    @Test public void aNewerSnapshotInvalidatesCurrentConfirmationWithoutErasingSameWorkoutHistory() throws Exception {
        GarminLinkTelemetry telemetry = new GarminLinkTelemetry();
        telemetry.receive(hello(10, "workout-a", 0), target(10, "workout-a"), 0, 100);
        JSONObject newer = telemetry.status(target(11, "workout-a"), 0);
        assertFalse(newer.getBoolean("snapshotConfirmed"));
        assertEquals(100, newer.getLong("lastConfirmedAt"));
        telemetry.receive(hello(11, "workout-a", 0), target(11, "workout-a"), 0, 200);
        assertTrue(telemetry.status(target(11, "workout-a"), 0).getBoolean("snapshotConfirmed"));
        assertEquals(200, telemetry.status(target(11, "workout-a"), 0).getLong("lastConfirmedAt"));
    }

    @Test public void anotherWorkoutAndResetCannotInheritConfirmationDates() throws Exception {
        GarminLinkTelemetry telemetry = new GarminLinkTelemetry();
        JSONObject wanted = target(10, "workout-a");
        telemetry.receive(hello(10, "workout-a", 0), wanted, 0, 100);
        for (JSONObject different : new JSONObject[] { target(10, "workout-b"), target(10, null) }) {
            JSONObject status = telemetry.status(different, 0);
            assertFalse(status.getBoolean("snapshotConfirmed"));
            assertEquals(0, status.getLong("lastConfirmedAt"));
            assertEquals(-1, status.getInt("watchPending"));
        }
        telemetry.reset();
        JSONObject reset = telemetry.status(wanted, 0);
        assertEquals(0, reset.getLong("lastMessageAt"));
        assertEquals(0, reset.getLong("lastConfirmedAt"));
        assertEquals(-1, reset.getInt("watchPending"));
        assertFalse(reset.getBoolean("snapshotConfirmed"));
    }

    @Test public void legacyHelloAndHeartRateProveContactWithoutInventingConfirmation() throws Exception {
        GarminLinkTelemetry telemetry = new GarminLinkTelemetry();
        JSONObject wanted = target(10, "workout-a");
        telemetry.receive(incoming(helloMap()), wanted, 0, 100);
        assertEquals(100, telemetry.status(wanted, 0).getLong("lastMessageAt"));
        assertEquals(-1, telemetry.status(wanted, 0).getInt("watchPending"));
        assertFalse(telemetry.status(wanted, 0).getBoolean("snapshotConfirmed"));
        Map<String, Object> hr = new HashMap<>();
        hr.put("v", 1); hr.put("kind", "hr"); hr.put("wid", "workout-a"); hr.put("at", 150L); hr.put("bpm", 60);
        telemetry.receive(incoming(hr), wanted, 0, 200);
        assertEquals(200, telemetry.status(wanted, 0).getLong("lastMessageAt"));
        assertEquals(0, telemetry.status(wanted, 0).getLong("lastConfirmedAt"));
        assertFalse(telemetry.status(wanted, 0).getBoolean("snapshotConfirmed"));
    }

    @Test public void idleConfirmationRequiresExplicitNullWorkoutRatherThanOmittedIdentity() throws Exception {
        GarminLinkTelemetry telemetry = new GarminLinkTelemetry();
        JSONObject idle = target(10, null);
        Map<String, Object> partial = helloMap();
        partial.put("seq", 10); partial.put("pending", 0);
        telemetry.receive(incoming(partial), idle, 0, 100);
        assertFalse("An omitted workout identity is not proof of an idle watch", telemetry.status(idle, 0).getBoolean("snapshotConfirmed"));
        assertEquals(0, telemetry.status(idle, 0).getLong("lastConfirmedAt"));
        partial.put("wid", null);
        telemetry.receive(incoming(partial), idle, 0, 200);
        assertTrue(telemetry.status(idle, 0).getBoolean("snapshotConfirmed"));
        assertEquals(200, telemetry.status(idle, 0).getLong("lastConfirmedAt"));
    }

    @Test public void incompleteDiagnosticsCannotConfirmEvenWhenAnEarlierHelloDid() throws Exception {
        for (String omitted : new String[] { "seq", "pending", "wid" }) {
            GarminLinkTelemetry telemetry = new GarminLinkTelemetry();
            JSONObject wanted = target(10, "workout-a");
            telemetry.receive(hello(10, "workout-a", 0), wanted, 0, 100);
            Map<String, Object> partial = helloMap();
            partial.put("seq", 10); partial.put("pending", 0); partial.put("wid", "workout-a"); partial.remove(omitted);
            telemetry.receive(incoming(partial), wanted, 0, 200);
            assertFalse(omitted, telemetry.status(wanted, 0).getBoolean("snapshotConfirmed"));
            assertEquals(100, telemetry.status(wanted, 0).getLong("lastConfirmedAt"));
        }
    }

    @Test public void helloOptionalIntegerBoundariesAndNullableWorkoutArePreserved() throws Exception {
        JSONObject legacy = incoming(helloMap());
        assertEquals(2, legacy.length());
        for (long seq : new long[] { -1, 0, GarminProtocol.MAX_SAFE_INTEGER }) {
            for (int pending : new int[] { 0, 256 }) {
                Map<String, Object> source = helloMap();
                source.put("seq", seq); source.put("pending", pending); source.put("wid", null);
                JSONObject clean = incoming(source);
                assertEquals(seq, clean.getLong("seq"));
                assertEquals(pending, clean.getInt("pending"));
                assertTrue(clean.has("wid"));
                assertTrue(clean.isNull("wid"));
            }
        }
        Map<String, Object> source = helloMap();
        source.put("wid", "a".repeat(128));
        assertEquals("a".repeat(128), incoming(source).getString("wid"));
    }

    @Test public void invalidOptionalDiagnosticValuesAreRejectedRatherThanCoerced() throws Exception {
        for (String key : new String[] { "seq", "pending" }) {
            Object[] values = key.equals("seq")
                ? new Object[] { -2L, GarminProtocol.MAX_SAFE_INTEGER + 1, 0.5, "10", true, null }
                : new Object[] { -1, 257, 0.5, "0", false, null };
            for (Object value : values) {
                Map<String, Object> source = helloMap(); source.put(key, value);
                assertThrows(key + "=" + value, IllegalArgumentException.class, () -> incoming(source));
            }
        }
        for (Object value : new Object[] { "", "a".repeat(129), 123, false, new JSONArray() }) {
            Map<String, Object> source = helloMap(); source.put("wid", value);
            assertThrows("wid=" + value, IllegalArgumentException.class, () -> incoming(source));
        }
    }

    @Test public void helloAllowlistDoesNotMutateInputOrCarryCommandAcknowledgements() throws Exception {
        Map<String, Object> source = helloMap();
        source.put("seq", 10L); source.put("wid", "workout-a"); source.put("pending", 0);
        source.put("ids", java.util.List.of("command-a")); source.put("credentials", "synthetic-private");
        Map<String, Object> before = new HashMap<>(source);
        JSONObject clean = incoming(source);
        assertEquals(before, source);
        assertEquals(5, clean.length());
        assertFalse(clean.has("ids"));
        assertFalse(clean.has("credentials"));
    }

    private static final class Disk implements GarminLinkStore.Storage {
        String saved;
        int writes;
        @Override public String read() { return saved; }
        @Override public void write(String value) { writes++; saved = value; }
    }

    @Test public void diagnosticReadsAndHelloNeverPersistOrAcknowledgeQueuedCommands() throws Exception {
        Disk disk = new Disk();
        GarminLinkStore store = new GarminLinkStore(disk);
        store.configure(true, "123");
        store.setSnapshot("{\"v\":1,\"unit\":\"kg\",\"active\":null}");
        JSONObject event = new JSONObject().put("id", "installation:1").put("wid", "workout-a")
            .put("type", "setDone").put("at", 100L).put("exId", "squat").put("entryIdx", 0).put("setIdx", 0);
        store.receive(new JSONArray().put(event));
        int writes = disk.writes;
        String saved = disk.saved;
        JSONObject diagnostic = store.diagnosticTarget();
        assertNotNull(diagnostic);
        assertEquals(1, store.pendingCount());
        assertNull(store.snapshot());
        GarminLinkTelemetry telemetry = new GarminLinkTelemetry();
        telemetry.receive(hello(diagnostic.getLong("seq"), null, 0), diagnostic, store.pendingCount(), 100);
        assertFalse(telemetry.status(diagnostic, store.pendingCount()).getBoolean("snapshotConfirmed"));
        diagnostic.put("seq", -1).put("wid", "changed-copy");
        assertNotEquals(-1, store.diagnosticTarget().getLong("seq"));
        assertTrue(store.diagnosticTarget().isNull("wid"));
        assertEquals(writes, disk.writes);
        assertEquals(saved, disk.saved);
        assertEquals(1, store.events().length());
        assertEquals(0, store.ackPackets().length());
    }

    @Test public void noSnapshotHasNoDiagnosticTarget() throws Exception {
        GarminLinkStore store = new GarminLinkStore(new Disk());
        assertNull(store.diagnosticTarget());
        assertEquals(0, store.pendingCount());
        GarminLinkTelemetry telemetry = new GarminLinkTelemetry();
        telemetry.receive(hello(10, null, 0), null, 0, 100);
        assertFalse(telemetry.status(null, 0).getBoolean("snapshotConfirmed"));
        assertEquals(0, telemetry.status(null, 0).getLong("lastConfirmedAt"));
    }
}
