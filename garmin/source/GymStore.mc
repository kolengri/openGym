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
        var sizes = {};
        if (GymData.measuredSize(data, 0, sizes) > 48000) { throw new GymError("Workout storage capacity reached"); }
        var head = backend.get("gym-head");
        slot = head == null || GymData.is(head["slot"],"b") ? "a" : "b";
        var previousCount = backend.get("gym-count-" + slot);
        count = 0;
        var root = writeNode(data, sizes);
        // Delete obsolete pages from the inactive generation before publishing.
        if (previousCount != null) {
            for (var i = count; i < previousCount; i++) { backend.remove(key(i)); }
        }
        backend.put("gym-count-" + slot, count);
        backend.put("gym-head", {"slot"=>slot, "root"=>root});
    }
    function reservePage() {
        var index = count; count += 1;
        if (count > 256) { throw new GymError("Workout page capacity reached"); }
        return index;
    }
    function writeNode(value, sizes) {
        var root = reservePage();
        var pending = [[root, value]];
        // Only the inactive slot is written here. Parent pages may precede their
        // children; save publishes the root only after every page succeeds.
        while (pending.size() > 0) {
            var job = pending[pending.size()-1]; pending.remove(job);
            var index = job[0]; var item = job[1]; var node;
            if (GymData.measuredSize(item, 0, sizes) <= 4000) {
                node = {"kind"=>"value", "value"=>item};
            } else if (item instanceof Array) {
                var first = reservePage();
                if (item.size() == 1) {
                    node = {"kind"=>"item", "part"=>first};
                    pending.add([first,item[0]]);
                } else {
                    var second = reservePage(); var middle = (item.size()/2).toNumber();
                    node = {"kind"=>"array", "parts"=>[first,second]};
                    pending.add([second,item.slice(middle,null)]);
                    pending.add([first,item.slice(0,middle)]);
                }
            } else if (item instanceof Dictionary) {
                var keys = item.keys(); var left = reservePage();
                if (keys.size() == 1) {
                    node = {"kind"=>"entry", "key"=>keys[0], "part"=>left};
                    pending.add([left,item[keys[0]]]);
                } else {
                    var right = reservePage(); var a = {}; var b = {};
                    for (var i=0; i<keys.size(); i++) {
                        if (i < keys.size()/2) { a[keys[i]] = item[keys[i]]; }
                        else { b[keys[i]] = item[keys[i]]; }
                    }
                    node = {"kind"=>"dictionary", "parts"=>[left,right]};
                    pending.add([right,b]); pending.add([left,a]);
                }
            } else { throw new GymError("Unsupported storage value"); }
            backend.put(key(index),node);
        }
        return root;
    }
    function load() {
        var head = backend.get("gym-head");
        if (head == null) { return null; }
        if (!(head instanceof Dictionary) || (!GymData.is(head["slot"],"a") && !GymData.is(head["slot"],"b")) || head["root"] != 0) { throw new GymError("Invalid storage root"); }
        slot = head["slot"];
        return readNode(head["root"], 0);
    }
    function readNode(index, depth) {
        var result = [null] as Array;
        var pending = [{"index"=>index,"depth"=>depth,"into"=>result,"at"=>0}] as Array<Dictionary>;
        while (pending.size() > 0) {
            var job = pending[pending.size()-1]; pending.remove(job);
            var kind = job["merge"];
            if (kind != null) {
                var a = job["parts"][0]; var b = job["parts"][1];
                if (kind.equals("array") && a instanceof Array && b instanceof Array) { a.addAll(b); }
                else if (kind.equals("dictionary") && a instanceof Dictionary && b instanceof Dictionary) {
                    var keys = b.keys();
                    for (var i=0; i<keys.size(); i++) { a[keys[i]] = b[keys[i]]; }
                } else { throw new GymError("Invalid storage tree"); }
                job["into"][job["at"]] = a;
                continue;
            }
            index = job["index"]; depth = job["depth"];
            if (depth > 32 || !GymData.integer(index) || index > 255) { throw new GymError("Invalid storage page"); }
            var node = backend.get(key(index));
            if (!(node instanceof Dictionary)) { throw new GymError("Missing storage page"); }
            kind = node["kind"];
            if (GymData.is(kind,"value")) {
                job["into"][job["at"]] = GymData.copy(node["value"]);
            } else if (GymData.is(kind,"item")) {
                var item = [null]; job["into"][job["at"]] = item;
                pending.add({"index"=>node["part"],"depth"=>depth+1,"into"=>item,"at"=>0});
            } else if (GymData.is(kind,"entry")) {
                if (!(node["key"] instanceof String)) { throw new GymError("Invalid storage entry"); }
                var entry = {}; job["into"][job["at"]] = entry;
                pending.add({"index"=>node["part"],"depth"=>depth+1,"into"=>entry,"at"=>node["key"]});
            } else {
                var parts = node["parts"];
                if (!(parts instanceof Array) || parts.size() != 2) { throw new GymError("Invalid storage parts"); }
                if (!GymData.is(kind,"array") && !GymData.is(kind,"dictionary")) { throw new GymError("Invalid storage tree"); }
                var values = [null,null];
                pending.add({"merge"=>kind,"parts"=>values,"into"=>job["into"],"at"=>job["at"]});
                pending.add({"index"=>parts[1],"depth"=>depth+1,"into"=>values,"at"=>1});
                pending.add({"index"=>parts[0],"depth"=>depth+1,"into"=>values,"at"=>0});
            }
        }
        return result[0];
    }

}
class GarminStorage {
    function initialize() {}
    function get(key) { return Application.Storage.getValue(key); }
    function put(key,value) { Application.Storage.setValue(key,value); }
    function remove(key) { Application.Storage.deleteValue(key); }
}
