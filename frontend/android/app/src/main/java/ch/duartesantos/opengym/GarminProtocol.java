package ch.duartesantos.opengym;

import com.garmin.monkeybrains.serialization.Serializer;
import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/** Bounded, allowlisted Connect IQ dictionaries. No historical workouts or account data. */
final class GarminProtocol {
    static final String APP_ID = "6fcd6528636d4cc39c3ad1e317d7524a";
    static final int MAX_MESSAGE_BYTES = 12 * 1024;
    static final int MAX_BATCH = 32;
    static final long MAX_SAFE_INTEGER = 9_007_199_254_740_991L;

    private GarminProtocol() {}

    static JSONObject parse(String json) throws Exception {
        if (json == null || json.getBytes(StandardCharsets.UTF_8).length > 256 * 1024)
            throw new IllegalArgumentException("Garmin input is too large");
        // Bound depth before the JSON parser recurses, including ignored snapshot fields.
        int depth = 0;
        boolean quoted = false, escaped = false;
        for (int i = 0; i < json.length(); i++) {
            char c = json.charAt(i);
            if (quoted) {
                if (escaped) escaped = false;
                else if (c == '\\') escaped = true;
                else if (c == '"') quoted = false;
            } else if (c == '"') quoted = true;
            else if (c == '{' || c == '[') {
                if (++depth > 16) throw new IllegalArgumentException("Garmin input is too deeply nested");
            } else if (c == '}' || c == ']') depth--;
        }
        JSONObject result = new JSONObject(json);
        javaValue(result, 0, new int[] { 8192 });
        return result;
    }

    static JSONObject snapshot(String json, long seq) throws Exception {
        JSONObject input = parse(json);
        integer(input, "v", 1, 1);
        String unit = string(input, "unit", 2);
        if (!unit.equals("kg") && !unit.equals("lb")) fail("Invalid Garmin weight unit");
        JSONObject state = new JSONObject().put("v", 1).put("unit", unit);
        copyNumbers(input, state, 0, 86400, "restSec");
        JSONArray discarded = input.optJSONArray("discarded");
        if (discarded != null) {
            if (discarded.length() > 64) fail("Too many discarded Garmin workouts");
            for (int i = 0; i < discarded.length(); i++) id(discarded.get(i));
            state.put("discarded", discarded);
        }
        JSONObject settings = input.optJSONObject("settings");
        state.put("settings", new JSONObject().put("recording", settings == null || !settings.has("recording") || bool(settings, "recording"))
            .put("restHaptics", settings == null || !settings.has("restHaptics") || bool(settings, "restHaptics")));
        if (!input.has("active")) fail("Garmin snapshot must include active");
        if (input.isNull("active")) state.put("active", JSONObject.NULL);
        else {
            JSONObject source = input.getJSONObject("active");
            JSONObject active = new JSONObject().put("id", id(source.get("id")))
                .put("name", optionalString(source, "name", 160, ""))
                .put("unit", unit);
            copyNumbers(source, active, 0, MAX_SAFE_INTEGER, "start");
            copyNumbers(source, active, 0, 86400, "restSec");
            if (source.has("watchPaused")) active.put("watchPaused", bool(source, "watchPaused"));
            JSONArray entries = source.getJSONArray("entries");
            if (entries.length() < 1 || entries.length() > 100) fail("Invalid Garmin exercise count");
            integer(source, "cur", 0, entries.length() - 1);
            active.put("cur", source.getInt("cur"));
            JSONArray reduced = new JSONArray();
            for (int i = 0; i < entries.length(); i++) reduced.put(entry(entries.getJSONObject(i)));
            active.put("entries", reduced);
            if (source.has("rest") && !source.isNull("rest")) {
                active.put("rest", rest(source.getJSONObject("rest")));
            } else active.put("rest", JSONObject.NULL);
            state.put("active", active);
        }
        JSONObject out = new JSONObject().put("v", 1).put("kind", "snapshot").put("seq", seq).put("state", state);
        // Leave room for at least one maximum-length event ID in its acknowledgement fence.
        checkedWire(out, MAX_MESSAGE_BYTES - 256);
        return out;
    }

    private static JSONObject entry(JSONObject source) throws Exception {
        String mode = string(source, "mode", 16);
        // Cardio stays in the plan so indexes match the phone; completion remains phone-only.
        if (!mode.equals("reps") && !mode.equals("time") && !mode.equals("cardio")) fail("This exercise mode is not supported on Garmin");
        JSONObject out = new JSONObject().put("id", id(source.get("id")))
            .put("name", string(source, "name", 160)).put("mode", mode);
        copyNumbers(source, out, 0, 86400, "restSec", "sideRestSec");
        for (String k : new String[] { "bodyweight", "perSide", "assisted" })
            if (source.has(k)) out.put(k, bool(source, k));
        if (source.has("group")) out.put("group", string(source, "group", 128));
        copyNumbers(source, out, 0, 10000, "step");
        JSONArray sets = source.getJSONArray("sets"), reduced = new JSONArray();
        if (sets.length() > 100) fail("Too many Garmin sets");
        for (int i = 0; i < sets.length(); i++) {
            JSONObject s = sets.getJSONObject(i), row = new JSONObject();
            copyNumbers(s, row, 0, 10000, "w", "r");
            copyNumbers(s, row, 0, 86400, "sec", "restSec");
            copyNumbers(s, row, 0, MAX_SAFE_INTEGER, "at");
            row.put("done", bool(s, "done"));
            if (s.has("warmup")) row.put("warmup", bool(s, "warmup"));
            if (s.has("unsupported")) row.put("unsupported", bool(s, "unsupported"));
            if (s.has("type")) row.put("type", string(s, "type", 32));
            if (s.has("sides")) {
                JSONObject sides = s.getJSONObject("sides"), cleanSides = new JSONObject();
                for (String side : new String[] { "L", "R" }) {
                    JSONObject part = sides.getJSONObject(side), clean = new JSONObject();
                    copyNumbers(part, clean, 0, 10000, "w", "r");
                    clean.put("done", bool(part, "done"));
                    cleanSides.put(side, clean);
                }
                row.put("sides", cleanSides);
            }
            reduced.put(row);
        }
        return out.put("sets", reduced);
    }

    static JSONObject incoming(Object value) throws Exception {
        if (!(value instanceof Map)) fail("Garmin message must be a dictionary");
        // Validate while wrapping SDK containers. JSONObject(Map) omits null-valued keys,
        // but an explicit null rest is a command to clear the previous countdown.
        JSONObject message = (JSONObject) sdkValue(value, 0, new int[] { 4096 });
        wire(message);
        integer(message, "v", 1, 1);
        String kind = string(message, "kind", 16);
        if (kind.equals("hello")) return new JSONObject().put("v", 1).put("kind", "hello");
        if (kind.equals("hr")) {
            id(message.get("wid"));
            integer(message, "at", 1, MAX_SAFE_INTEGER);
            integer(message, "bpm", 25, 260);
            return new JSONObject().put("v", 1).put("kind", kind).put("wid", message.get("wid"))
                .put("at", message.get("at")).put("bpm", message.get("bpm"));
        }
        if (!kind.equals("events")) fail("Unknown Garmin message kind");
        JSONArray events = message.getJSONArray("events"), clean = new JSONArray();
        if (events.length() < 1 || events.length() > MAX_BATCH) fail("Invalid Garmin event batch size");
        for (int i = 0; i < events.length(); i++) clean.put(event(events.getJSONObject(i)));
        return new JSONObject().put("v", 1).put("kind", kind).put("events", clean);
    }

    static JSONObject event(JSONObject source) throws Exception {
        JSONObject out = new JSONObject().put("id", id(source.get("id"))).put("wid", id(source.get("wid")));
        String type = string(source, "type", 32);
        integer(source, "at", 1, MAX_SAFE_INTEGER);
        out.put("type", type).put("at", source.get("at"));
        switch (type) {
            case "setDone":
            case "setHr":
                out.put("exId", id(source.get("exId")));
                integer(source, "entryIdx", 0, 99);
                integer(source, "setIdx", 0, 99);
                out.put("entryIdx", source.get("entryIdx")).put("setIdx", source.get("setIdx"));
                copyNumbers(source, out, 0, 10000, "w", "r");
                copyNumbers(source, out, 0, 86400, "sec");
                if (source.has("side")) {
                    String side = string(source, "side", 1);
                    if (!side.equals("L") && !side.equals("R")) fail("Invalid Garmin set side");
                    out.put("side", side);
                }
                for (String key : new String[] { "hr", "restHr" }) {
                    if (source.has(key) && !source.isNull(key)) {
                        JSONObject hr = source.getJSONObject(key);
                        double avg = number(hr, "avg", 25, 260), max = number(hr, "max", 25, 260);
                        if (avg > max) fail("Invalid Garmin heart rate aggregate");
                        out.put(key, new JSONObject().put("avg", avg).put("max", max));
                    }
                }
                break;
            case "selectExercise":
                out.put("exId", id(source.get("exId")));
                integer(source, "entryIdx", 0, 99);
                out.put("entryIdx", source.get("entryIdx"));
                break;
            case "pause":
                boolean paused = bool(source, "paused");
                out.put("paused", paused);
                if (!source.has("rest")) fail("Missing Garmin pause rest state");
                if (source.isNull("rest")) out.put("rest", JSONObject.NULL);
                else {
                    JSONObject r = rest(source.getJSONObject("rest"));
                    integer(r, "endsAt", 0, MAX_SAFE_INTEGER);
                    integer(r, "left", 0, 86400);
                    if (bool(r, "paused") != paused) fail("Invalid Garmin pause rest state");
                    out.put("rest", r);
                }
                break;
            case "skipRest":
            case "finish":
            case "discard": break;
            default: fail("Unsupported Garmin event");
        }
        return out;
    }

    private static JSONObject rest(JSONObject source) throws Exception {
        JSONObject out = new JSONObject();
        copyNumbers(source, out, 0, MAX_SAFE_INTEGER, "endsAt");
        for (String key : new String[] { "left", "total", "forIdx", "forSet" }) {
            if (source.has(key) && !source.isNull(key)) {
                integer(source, key, 0, key.startsWith("for") ? 99 : 86400);
                out.put(key, source.get(key));
            }
        }
        if (source.has("paused")) out.put("paused", bool(source, "paused"));
        if (source.has("kind")) {
            if (!"switch".equals(string(source, "kind", 16))) fail("Invalid Garmin rest kind");
            out.put("kind", "switch");
        }
        return out;
    }

    static Map<String, Object> wire(JSONObject object) throws Exception {
        return checkedWire(object, MAX_MESSAGE_BYTES);
    }

    private static Map<String, Object> checkedWire(JSONObject object, int limit) throws Exception {
        @SuppressWarnings("unchecked")
        Map<String, Object> result = (Map<String, Object>) javaValue(object, 0, new int[] { 8192 });
        if (object.toString().getBytes(StandardCharsets.UTF_8).length >= limit
                || Serializer.serialize(result).length >= limit)
            fail("Garmin message exceeds its safe 12 KiB budget; shorten this workout before syncing");
        return result;
    }

    private static Object javaValue(Object value, int depth, int[] budget) throws Exception {
        if (depth > 16 || --budget[0] < 0) fail("Garmin message is too complex");
        if (value == null || value == JSONObject.NULL) return null;
        if (value instanceof JSONObject) {
            JSONObject object = (JSONObject) value;
            Map<String, Object> out = new HashMap<>();
            for (Iterator<String> keys = object.keys(); keys.hasNext();) {
                String key = keys.next();
                if (key.length() > 128) fail("Garmin key is too long");
                out.put(key, javaValue(object.get(key), depth + 1, budget));
            }
            return out;
        }
        if (value instanceof JSONArray) {
            JSONArray array = (JSONArray) value;
            List<Object> out = new ArrayList<>();
            for (int i = 0; i < array.length(); i++) out.add(javaValue(array.get(i), depth + 1, budget));
            return out;
        }
        primitive(value);
        return value;
    }

    private static Object sdkValue(Object value, int depth, int[] budget) throws Exception {
        if (depth > 16 || --budget[0] < 0) fail("Garmin message is too complex");
        if (value == null) return JSONObject.NULL;
        if (value instanceof Map) {
            JSONObject out = new JSONObject();
            for (Map.Entry<?, ?> e : ((Map<?, ?>) value).entrySet()) {
                if (!(e.getKey() instanceof String) || ((String) e.getKey()).length() > 128)
                    fail("Invalid Garmin dictionary key");
                out.put((String) e.getKey(), sdkValue(e.getValue(), depth + 1, budget));
            }
            return out;
        } else if (value instanceof List) {
            JSONArray out = new JSONArray();
            for (Object v : (List<?>) value) out.put(sdkValue(v, depth + 1, budget));
            return out;
        }
        primitive(value);
        return value;
    }

    private static void primitive(Object value) {
        if (value instanceof String) {
            if (((String) value).length() > 4096) fail("Garmin string is too long");
        } else if (value instanceof Number) {
            double n = ((Number) value).doubleValue();
            if (!Double.isFinite(n) || Math.abs(n) > MAX_SAFE_INTEGER) fail("Invalid Garmin number");
            if (!(value instanceof Integer || value instanceof Long || value instanceof Float || value instanceof Double))
                fail("Unsupported Garmin number type");
        } else if (!(value instanceof Boolean)) fail("Unsupported Garmin value type");
    }

    static String id(Object value) {
        if (!(value instanceof String) || ((String) value).isEmpty() || ((String) value).length() > 128)
            throw new IllegalArgumentException("Invalid Garmin identifier");
        return (String) value;
    }

    private static String string(JSONObject o, String key, int max) throws Exception {
        Object value = o.get(key);
        if (!(value instanceof String) || ((String) value).length() > max || ((String) value).isEmpty())
            throw new IllegalArgumentException("Invalid Garmin " + key);
        return (String) value;
    }

    private static String optionalString(JSONObject o, String key, int max, String fallback) throws Exception {
        if (!o.has(key) || o.optString(key).isEmpty()) return fallback;
        return string(o, key, max);
    }

    private static boolean bool(JSONObject o, String key) throws Exception {
        Object value = o.get(key);
        if (!(value instanceof Boolean)) throw new IllegalArgumentException("Invalid Garmin " + key);
        return (Boolean) value;
    }

    private static double number(JSONObject o, String key, double min, double max) throws Exception {
        Object value = o.get(key);
        if (!(value instanceof Number)) throw new IllegalArgumentException("Invalid Garmin " + key);
        double n = ((Number) value).doubleValue();
        if (!Double.isFinite(n) || n < min || n > max) throw new IllegalArgumentException("Invalid Garmin " + key);
        return n;
    }

    private static void integer(JSONObject o, String key, long min, long max) throws Exception {
        double n = number(o, key, min, max);
        if (n != Math.rint(n)) throw new IllegalArgumentException("Invalid Garmin " + key);
    }

    private static void copyNumbers(JSONObject source, JSONObject target, double min, double max, String... keys) throws Exception {
        for (String key : keys) if (source.has(key) && !source.isNull(key)) {
            number(source, key, min, max);
            target.put(key, source.get(key));
        }
    }

    private static void fail(String message) { throw new IllegalArgumentException(message); }
}
