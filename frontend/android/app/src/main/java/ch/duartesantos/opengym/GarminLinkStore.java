package ch.duartesantos.opengym;

import org.json.JSONArray;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

/** Serial access only. Each mutation reaches private durable storage before becoming visible. */
final class GarminLinkStore {
    static final int MAX_EVENTS = 256;
    static final int MAX_ACKED = 1024;
    static final int MAX_STORE_BYTES = 512 * 1024;

    interface Storage {
        String read() throws Exception;
        void write(String value) throws Exception;
    }

    private final Storage storage;
    private JSONObject state;

    GarminLinkStore(Storage storage) throws Exception {
        this.storage = storage;
        String saved = storage.read();
        if (saved == null) state = empty(System.currentTimeMillis());
        else {
            if (saved.getBytes(StandardCharsets.UTF_8).length > MAX_STORE_BYTES)
                throw new IllegalStateException("Garmin queue storage is too large; disable the link to reset it");
            state = new JSONObject(saved);
            if (state.getInt("v") != 1 || !(state.get("enabled") instanceof Boolean)
                    || !(state.get("dirty") instanceof Boolean)
                    || !(state.get("seq") instanceof Number)
                    || state.getDouble("seq") != Math.rint(state.getDouble("seq"))
                    || state.getLong("seq") < 0 || state.getLong("seq") > GarminProtocol.MAX_SAFE_INTEGER
                    || state.getJSONArray("events").length() > MAX_EVENTS
                    || state.getJSONArray("acked").length() > MAX_ACKED)
                throw new IllegalStateException("Garmin queue storage is invalid; disable the link to reset it");
            if (enabled() && !deviceId().matches("-?[0-9]{1,20}"))
                throw new IllegalStateException("Garmin selection is invalid; disable the link to reset it");
            for (int i = 0; i < state.getJSONArray("events").length(); i++)
                GarminProtocol.event(state.getJSONArray("events").getJSONObject(i));
            ids(state.getJSONArray("acked"));
            for (String key : new String[] { "snapshot", "ackFence" }) {
                if (!state.has(key)) continue;
                JSONObject snapshot = state.getJSONObject(key);
                GarminProtocol.wire(snapshot);
                if (!"snapshot".equals(snapshot.getString("kind")) || snapshot.getInt("v") != 1
                        || snapshot.getLong("seq") > state.getLong("seq"))
                    throw new IllegalStateException("Garmin saved snapshot is invalid; disable the link to reset it");
            }
        }
    }

    static void reset(Storage storage) throws Exception { storage.write(empty(System.currentTimeMillis()).toString()); }

    private static JSONObject empty(long seq) throws Exception {
        return new JSONObject().put("v", 1).put("enabled", false).put("seq", seq)
            .put("events", new JSONArray()).put("acked", new JSONArray()).put("dirty", false);
    }

    boolean enabled() { return state.optBoolean("enabled", false); }
    String deviceId() { return state.optString("deviceId", ""); }
    boolean pending() { return state.optJSONArray("events").length() > 0; }
    JSONArray events() throws Exception { return new JSONArray(state.getJSONArray("events").toString()); }
    JSONObject snapshot() throws Exception {
        if (pending() || state.optBoolean("dirty") || !state.has("snapshot")) return null;
        return new JSONObject(state.getJSONObject("snapshot").toString());
    }

    boolean configure(boolean enabled, String deviceId) throws Exception {
        if (enabled && (deviceId == null || !deviceId.matches("-?[0-9]{1,20}")))
            throw new IllegalArgumentException("Select a Garmin device first");
        boolean changed = enabled != enabled() || (enabled && !deviceId.equals(deviceId()));
        if (!changed) return false;
        JSONObject next = empty(state.optLong("seq"));
        next.put("enabled", enabled);
        if (enabled) next.put("deviceId", deviceId);
        commit(next);
        return true;
    }

    JSONObject setSnapshot(String json) throws Exception {
        requireEnabled();
        JSONObject next = copy();
        JSONObject snapshot = GarminProtocol.snapshot(json, nextSequence(next));
        next.put("snapshot", snapshot).put("dirty", false);
        commit(next);
        return snapshot;
    }

    /** Whole batches are accepted or rejected; an overflow never evicts pending commands. */
    boolean receive(JSONArray incoming) throws Exception {
        requireEnabled();
        if (incoming.length() > GarminProtocol.MAX_BATCH) throw new IllegalArgumentException("Too many Garmin events");
        JSONObject next = copy();
        JSONArray queue = next.getJSONArray("events"), acked = next.getJSONArray("acked");
        Set<String> known = ids(acked);
        for (int i = 0; i < queue.length(); i++) known.add(queue.getJSONObject(i).getString("id"));
        boolean added = false;
        for (int i = 0; i < incoming.length(); i++) {
            JSONObject event = GarminProtocol.event(incoming.getJSONObject(i));
            String id = event.getString("id");
            if (known.add(id)) {
                if (queue.length() >= MAX_EVENTS)
                    throw new IllegalStateException("Garmin command queue is full; open this workout on the phone to sync");
                queue.put(event);
                added = true;
            }
        }
        if (added) {
            next.put("dirty", true);
            commit(next);
        }
        return added;
    }

    /** Called only after JS saveNow. A failed write removes no event and produces no ack. */
    void acknowledge(JSONArray ids, String resultingSnapshot) throws Exception {
        requireEnabled();
        if (ids == null || ids.length() == 0 || ids.length() > MAX_EVENTS)
            throw new IllegalArgumentException("Invalid Garmin acknowledgement size");
        Set<String> requested = ids(ids), queued = ids(state.getJSONArray("acked"));
        JSONArray queue = state.getJSONArray("events");
        for (int i = 0; i < queue.length(); i++) queued.add(queue.getJSONObject(i).getString("id"));
        if (!queued.containsAll(requested))
            throw new IllegalArgumentException("Only received Garmin commands can be acknowledged");
        JSONObject next = copy();
        JSONObject snapshot = GarminProtocol.snapshot(resultingSnapshot, nextSequence(next));
        JSONArray remaining = new JSONArray(), acked = next.getJSONArray("acked");
        for (int i = 0; i < queue.length(); i++) {
            JSONObject event = queue.getJSONObject(i);
                if (requested.contains(event.getString("id"))) acked.put(event.getString("id"));
            else remaining.put(event);
        }
        JSONArray recent = new JSONArray();
        for (int i = Math.max(0, acked.length() - MAX_ACKED); i < acked.length(); i++) recent.put(acked.get(i));
        next.put("events", remaining).put("acked", recent).put("snapshot", snapshot)
            .put("ackFence", snapshot).put("dirty", remaining.length() > 0);
        // Size every prospective packet before committing; an unsendable fence must not consume commands.
        ackPackets(next, ids);
        commit(next);
    }

    JSONArray ackPackets() throws Exception { return ackPackets(state, state.getJSONArray("acked")); }

    JSONArray ackPacketsFor(JSONArray requested) throws Exception {
        if (requested.length() > MAX_ACKED) throw new IllegalArgumentException("Too many Garmin acknowledgement IDs");
        Set<String> acked = ids(state.getJSONArray("acked")), selected = new HashSet<>();
        JSONArray known = new JSONArray();
        for (int i = 0; i < requested.length(); i++) {
            String id = GarminProtocol.id(requested.get(i));
            if (acked.contains(id) && selected.add(id)) known.put(id);
        }
        return ackPackets(state, known);
    }

    private static JSONArray ackPackets(JSONObject state, JSONArray ids) throws Exception {
        JSONArray out = new JSONArray();
        if (ids.length() == 0 || !state.has("ackFence")) return out;
        JSONObject fence = state.getJSONObject("ackFence");
        JSONArray chunk = new JSONArray();
        for (int i = 0; i < ids.length(); i++) {
            JSONArray candidate = new JSONArray(chunk.toString()).put(ids.get(i));
            JSONObject packet = ackPacket(fence, candidate);
            boolean fits;
            try { GarminProtocol.wire(packet); fits = candidate.length() <= GarminProtocol.MAX_BATCH; }
            catch (IllegalArgumentException e) { fits = false; }
            if (!fits) {
                if (chunk.length() == 0)
                    throw new IllegalArgumentException("Garmin acknowledgement exceeds 12 KiB; shorten this workout before syncing");
                out.put(ackPacket(fence, chunk));
                chunk = new JSONArray().put(ids.get(i));
                GarminProtocol.wire(ackPacket(fence, chunk));
            } else chunk = candidate;
        }
        if (chunk.length() > 0) out.put(ackPacket(fence, chunk));
        return out;
    }

    private static JSONObject ackPacket(JSONObject fence, JSONArray ids) throws Exception {
        return new JSONObject().put("v", 1).put("kind", "ack").put("ids", ids)
            .put("seq", fence.getLong("seq")).put("state", fence.getJSONObject("state"));
    }

    private long nextSequence(JSONObject next) throws Exception {
        long seq = next.optLong("seq");
        if (seq >= GarminProtocol.MAX_SAFE_INTEGER) throw new IllegalStateException("Garmin sequence exhausted");
        next.put("seq", seq + 1);
        return seq + 1;
    }

    private static Set<String> ids(JSONArray values) throws Exception {
        Set<String> ids = new HashSet<>();
        for (int i = 0; i < values.length(); i++) ids.add(GarminProtocol.id(values.get(i)));
        return ids;
    }

    private JSONObject copy() throws Exception { return new JSONObject(state.toString()); }
    private void requireEnabled() { if (!enabled()) throw new IllegalStateException("Garmin link is disabled"); }

    private void commit(JSONObject next) throws Exception {
        String encoded = next.toString();
        if (encoded.getBytes(StandardCharsets.UTF_8).length > MAX_STORE_BYTES)
            throw new IllegalStateException("Garmin command storage is full; open the phone to sync");
        storage.write(encoded);
        state = next;
    }
}
