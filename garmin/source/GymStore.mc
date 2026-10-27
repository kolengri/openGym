import Toybox.Application;
import Toybox.Lang;

class GymError extends Lang.Exception {
    function initialize(message) { Exception.initialize(); mMessage = message; }
}

// Storage values have an 8 KiB limit. Write the inactive tree in small pages,
// then switch a single root key. A failed page write leaves the prior tree live.
// Completed slots are reused, so retries do not grow storage without bound.
class GymStore {
    var backend;
    var slot;
    var count;
    function initialize(storage) { backend = storage; }
    function key(index) { return "gym-" + slot + "-" + index.toString(); }
    function save(data) {
        if (GymData.size(data, 0) > 48000) { throw new GymError("Workout storage capacity reached"); }
        var head = backend.get("gym-head");
        slot = head == null || GymData.is(head["slot"],"b") ? "a" : "b";
        var previousCount = backend.get("gym-count-" + slot);
        count = 0;
        var root = writeNode(data);
        // Delete obsolete pages from the inactive generation before publishing.
        if (previousCount != null) {
            for (var i = count; i < previousCount; i++) { backend.remove(key(i)); }
        }
        backend.put("gym-count-" + slot, count);
        backend.put("gym-head", {"slot"=>slot, "root"=>root});
    }
    function writeNode(value) {
        var index = count; count += 1;
        if (count > 256) { throw new GymError("Workout page capacity reached"); }
        var node;
        if (GymData.size(value, 0) <= 4000) { node = {"kind"=>"value", "value"=>value}; }
        else if (value instanceof Array) {
            if (value.size() == 1) {
                var child = writeNode(value[0]);
                backend.put(key(index), {"kind"=>"item", "part"=>child});
                return index;
            }
            var middle = (value.size()/2).toNumber();
            var first = writeNode(value.slice(0, middle));
            var second = writeNode(value.slice(middle, null));
            node = {"kind"=>"array", "parts"=>[first, second]};
        } else if (value instanceof Dictionary) {
            var keys = value.keys(); var left = {}; var right = {};
            if (keys.size() == 1) {
                var part = writeNode(value[keys[0]]);
                backend.put(key(index), {"kind"=>"entry", "key"=>keys[0], "part"=>part});
                return index;
            }
            for (var i = 0; i < keys.size(); i++) {
                if (i < keys.size()/2) { left[keys[i]] = value[keys[i]]; }
                else { right[keys[i]] = value[keys[i]]; }
            }
            var l = writeNode(left); var r = writeNode(right);
            node = {"kind"=>"dictionary", "parts"=>[l,r]};
        } else { throw new GymError("Unsupported storage value"); }
        backend.put(key(index), node);
        return index;
    }
    function load() {
        var head = backend.get("gym-head");
        if (head == null) { return null; }
        if (!(head instanceof Dictionary) || (!GymData.is(head["slot"],"a") && !GymData.is(head["slot"],"b")) || head["root"] != 0) { throw new GymError("Invalid storage root"); }
        slot = head["slot"];
        return readNode(head["root"], 0);
    }
    function readNode(index, depth) {
        if (depth > 32 || !GymData.integer(index) || index > 255) { throw new GymError("Invalid storage page"); }
        var node = backend.get(key(index));
        if (!(node instanceof Dictionary)) { throw new GymError("Missing storage page"); }
        if (GymData.is(node["kind"],"value")) { return GymData.copy(node["value"]); }
        if (GymData.is(node["kind"],"item")) { return [readNode(node["part"],depth+1)]; }
        if (GymData.is(node["kind"],"entry")) { var result = {}; result[node["key"]] = readNode(node["part"],depth+1); return result; }
        var parts = node["parts"];
        if (!(parts instanceof Array) || parts.size() != 2) { throw new GymError("Invalid storage parts"); }
        var a = readNode(parts[0], depth+1); var b = readNode(parts[1],depth+1);
        if (GymData.is(node["kind"],"array") && a instanceof Array && b instanceof Array) { a.addAll(b); return a; }
        if (GymData.is(node["kind"],"dictionary") && a instanceof Dictionary && b instanceof Dictionary) {
            var keys = b.keys();
            for (var i = 0; i < keys.size(); i++) { a[keys[i]] = b[keys[i]]; }
            return a;
        }
        throw new GymError("Invalid storage tree");
    }
}
class GarminStorage {
    function initialize() {}
    function get(key) { return Application.Storage.getValue(key); }
    function put(key,value) { Application.Storage.setValue(key,value); }
    function remove(key) { Application.Storage.deleteValue(key); }
}
