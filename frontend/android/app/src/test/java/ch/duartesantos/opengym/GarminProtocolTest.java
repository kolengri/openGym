package ch.duartesantos.opengym;

import com.garmin.monkeybrains.serialization.Serializer;
import com.garmin.android.connectiq.IQMessageHelper;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import static org.junit.Assert.*;

public class GarminProtocolTest {
    @Test public void cardioWarmupDoesNotBlockFollowingStrengthExercises() throws Exception {
        JSONObject input = new JSONObject(snapshot());
        JSONArray entries = input.getJSONObject("active").getJSONArray("entries");
        JSONObject strength = new JSONObject(entries.getJSONObject(0).toString()).put("mode", "reps");
        entries.getJSONObject(0).put("mode", "cardio").put("id", "warmup");
        entries.put(strength);
        JSONObject envelope = GarminProtocol.snapshot(input.toString(), 8);
        JSONArray actual = envelope.getJSONObject("state").getJSONObject("active").getJSONArray("entries");
        assertEquals(2, actual.length());
        assertEquals("cardio", actual.getJSONObject(0).getString("mode"));
        assertEquals("warmup", actual.getJSONObject(0).getString("id"));
        assertEquals("reps", actual.getJSONObject(1).getString("mode"));
        assertEquals(1, actual.getJSONObject(0).getJSONArray("sets").length());
        assertTrue(Serializer.serialize(GarminProtocol.wire(envelope)).length > 0);
    }

    @Test public void cloudUploadCanDisableSeparateWatchRecording() throws Exception {
        JSONObject input = new JSONObject(snapshot());
        assertTrue(GarminProtocol.snapshot(input.toString(), 1).getJSONObject("state").getJSONObject("settings").getBoolean("recording"));
        input.put("settings", new JSONObject().put("recording", false));
        assertFalse(GarminProtocol.snapshot(input.toString(), 2).getJSONObject("state").getJSONObject("settings").getBoolean("recording"));
        input.getJSONObject("settings").put("recording", "false");
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.snapshot(input.toString(), 3));
    }

    private static String snapshot() throws Exception {
        JSONObject side = new JSONObject().put("w", 20).put("r", 5).put("done", false);
        JSONObject row = new JSONObject().put("w", 20).put("r", 5).put("sec", 45).put("done", false)
            .put("warmup", true).put("type", "warmup").put("unsupported", true).put("restSec", 0)
            .put("sides", new JSONObject().put("L", side).put("R", new JSONObject(side.toString())));
        JSONObject exercise = new JSONObject().put("id", "squat").put("name", "Squat").put("mode", "time")
            .put("restSec", 60).put("sideRestSec", 15).put("sets", new JSONArray().put(row)).put("last", "Private history")
            .put("best", new JSONObject().put("w", 100));
        return new JSONObject().put("v", 1).put("unit", "kg").put("ready", new JSONArray().put("Private routine"))
            .put("clips", "Private media").put("credentials", "Never transmitted")
            .put("active", new JSONObject().put("id", "session").put("name", "Workout").put("cur", 0)
                .put("start", 1_800_000_000_123L).put("watchPaused", true)
                .put("rest", new JSONObject().put("paused", true).put("left", 30000))
                .put("entries", new JSONArray().put(exercise))).toString();
    }

    @Test public void snapshotAllowlistPreservesTimedSideSetsAndPausedStateWithoutHistory() throws Exception {
        JSONObject envelope = GarminProtocol.snapshot(snapshot(), 7);
        JSONObject state = envelope.getJSONObject("state"), active = state.getJSONObject("active");
        JSONObject exercise = active.getJSONArray("entries").getJSONObject(0), row = exercise.getJSONArray("sets").getJSONObject(0);
        assertEquals(7, envelope.getLong("seq"));
        assertEquals(1_800_000_000_123L, active.getLong("start"));
        assertTrue(active.getBoolean("watchPaused"));
        assertTrue(active.getJSONObject("rest").getBoolean("paused"));
        assertEquals(30000, active.getJSONObject("rest").getInt("left"));
        assertEquals(45, row.getInt("sec"));
        assertEquals(0, row.getInt("restSec"));
        assertEquals(15, exercise.getInt("sideRestSec"));
        assertTrue(row.getBoolean("warmup"));
        assertTrue(row.getBoolean("unsupported"));
        assertTrue(row.has("sides"));
        assertFalse(state.has("ready"));
        assertFalse(state.has("credentials"));
        assertFalse(state.has("clips"));
        assertFalse(exercise.has("last"));
        assertFalse(exercise.has("best"));
    }

    @Test public void actualGarminSerializerRoundTrips64BitTimestamps() throws Exception {
        Map<String, Object> wire = GarminProtocol.wire(GarminProtocol.snapshot(snapshot(), 8));
        byte[] bytes = Serializer.serialize(wire);
        Object received = IQMessageHelper.INSTANCE.convertToJava(Serializer.deserialize(bytes).get(0));
        Map<?, ?> active = (Map<?, ?>) ((Map<?, ?>) ((Map<?, ?>) received).get("state")).get("active");
        assertEquals(1_800_000_000_123L, ((Number) active.get("start")).longValue());
        assertTrue(bytes.length < GarminProtocol.MAX_MESSAGE_BYTES);
    }

    @Test public void validatesWholeEventEnvelopeAndAllowsSupportedActionTypes() throws Exception {
        for (String type : new String[] { "setDone", "setHr", "selectExercise", "pause", "skipRest", "finish", "discard" }) {
            JSONObject event = GarminLinkStoreTest.event(1).put("type", type).put("paused", true).put("rest", JSONObject.NULL);
            Map<String, Object> message = new HashMap<>();
            message.put("v", 1);
            message.put("kind", "events");
            message.put("events", new ArrayList<>(List.of(GarminProtocol.wire(event))));
            Object callback = IQMessageHelper.INSTANCE.convertToJava(Serializer.deserialize(Serializer.serialize(message)).get(0));
            assertEquals(type, GarminProtocol.incoming(callback).getJSONArray("events").getJSONObject(0).getString("type"));
        }
    }

    @Test public void pauseCarriesAbsoluteRestWithoutPrivateFields() throws Exception {
        JSONObject event = GarminLinkStoreTest.event(1).put("type", "pause").put("paused", true)
            .put("rest", new JSONObject().put("paused", true).put("endsAt", 1_800_000_090_000L)
                .put("left", 70).put("total", 90).put("forIdx", 0).put("forSet", 1).put("kind", "switch").put("private", "excluded"));
        JSONObject clean = GarminProtocol.event(event);
        assertEquals(70, clean.getJSONObject("rest").getInt("left"));
        assertEquals(1_800_000_090_000L, clean.getJSONObject("rest").getLong("endsAt"));
        assertFalse(clean.getJSONObject("rest").has("private"));
        assertEquals("switch", clean.getJSONObject("rest").getString("kind"));
        event.getJSONObject("rest").put("paused", false);
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.event(event));
        event.remove("rest");
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.event(event));
    }

    @Test public void rejectsBadTypesNonFiniteNumbersAndExcessiveNesting() throws Exception {
        Map<String, Object> message = new HashMap<>();
        message.put("v", 1);
        message.put("kind", "hr");
        message.put("wid", "session");
        message.put("bpm", 120);
        message.put("at", 1_800_000_000_000L);
        assertEquals(120, GarminProtocol.incoming(message).getInt("bpm"));
        message.put("bpm", Double.NaN);
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.incoming(message));
        message.put("bpm", "120");
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.incoming(message));
        message.put("bpm", 120);
        message.put("secret", new Object());
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.incoming(message));
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.parse("{\"x\":" + "[".repeat(20) + "0" + "]".repeat(20) + "}"));
    }

    @Test public void oversizeAndUnsupportedModeAreRejectedWithoutTruncatingSets() throws Exception {
        JSONObject input = new JSONObject(snapshot());
        JSONArray entries = input.getJSONObject("active").getJSONArray("entries");
        JSONObject exercise = entries.getJSONObject(0);
        exercise.put("mode", "distance");
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.snapshot(input.toString(), 1));
        exercise.put("mode", "time");
        JSONObject row = exercise.getJSONArray("sets").getJSONObject(0);
        for (int i = 0; i < 99; i++) exercise.getJSONArray("sets").put(new JSONObject(row.toString()));
        assertThrows(IllegalArgumentException.class, () -> GarminProtocol.snapshot(input.toString(), 1));
        assertEquals(100, exercise.getJSONArray("sets").length());
    }
}
