import Toybox.Lang;

// All durable state lives in one journal transaction. No transport callback mutates
// the outbox: only an application-level acknowledgement does that.
module GymData {
    function copy(v) {
        if (v instanceof Dictionary) {
            var d = {};
            var keys = v.keys();
            for (var i = 0; i < keys.size(); i++) { d[keys[i]] = copy(v[keys[i]]); }
            return d;
        }
        if (v instanceof Array) {
            var a = [];
            for (var j = 0; j < v.size(); j++) { a.add(copy(v[j])); }
            return a;
        }
        return v;
    }
    function number(v) {
        return v instanceof Number || v instanceof Long || v instanceof Float || v instanceof Double;
    }
    function integer(v) { return (v instanceof Number || v instanceof Long) && v >= 0; }
    function text(v) { return v instanceof String && v.length() > 0 && v.length() <= 160; }
    function is(v, text) { return v instanceof String && v.equals(text); }
    // Upper bound for CIQ's serialized dictionary, including UTF-8 and type tags.
    // Refuse oversize input, never truncate a running workout.
    function size(v, depth) {
        if (depth > 10) { return 999999; }
        if (v == null || v instanceof Boolean) { return 5; }
        if (number(v)) { return 12; }
        if (v instanceof String) { return 5 + v.toUtf8Array().size(); }
        var n = 5;
        if (v instanceof Array) {
            for (var i = 0; i < v.size(); i++) { n += size(v[i], depth + 1); }
            return n;
        }
        if (v instanceof Dictionary) {
            var keys = v.keys();
            for (var j = 0; j < keys.size(); j++) {
                if (!(keys[j] instanceof String)) { return 999999; }
                n += size(keys[j], depth + 1) + size(v[keys[j]], depth + 1);
            }
            return n;
        }
        return 999999;
    }
    function value(v, lo, hi) { return number(v) && v >= lo && v <= hi; }
    function validRow(s) {
        if (!(s instanceof Dictionary) || !(s["done"] instanceof Boolean)) { return false; }
        if (s["unsupported"] != null && !(s["unsupported"] instanceof Boolean)) { return false; }
        if (s["warmup"] != null && !(s["warmup"] instanceof Boolean)) { return false; }
        var items1 = ["w", "r", "sec", "restSec"]; for (var idx1 = 0; idx1 < items1.size(); idx1++) { var key = items1[idx1];
            if (s[key] != null && !value(s[key], 0, key.equals("w") ? 10000 : 86400)) { return false; }
        }
        return true;
    }
    function validState(s) {
        if (!(s instanceof Dictionary) || s["v"] != 1) { return false; }
        if (!GymData.is(s["unit"],"kg") && !GymData.is(s["unit"],"lb")) { return false; }
        if (s["restSec"] != null && !value(s["restSec"],0,86400)) { return false; }
        if (s["discarded"] != null && !(s["discarded"] instanceof Array)) { return false; }
        if (s["settings"] != null && !(s["settings"] instanceof Dictionary)) { return false; }
        if (s["discarded"] != null) { for(var di=0;di<s["discarded"].size();di++){ if(!text(s["discarded"][di])){return false;} } }
        if (s["settings"] != null) {
            for(var si=0;si<2;si++){ var sk=["recording","restHaptics"][si]; if(s["settings"][sk]!=null && !(s["settings"][sk] instanceof Boolean)){return false;} }
        }
        var a = s["active"];
        if (a == null) { return true; }
        if (!(a instanceof Dictionary) || !text(a["id"]) || !(a["entries"] instanceof Array)) { return false; }
        if (a["entries"].size() == 0 || a["entries"].size() > 80 || !integer(a["cur"]) || a["cur"] >= a["entries"].size()) { return false; }
        if (a["watchPaused"] != null && !(a["watchPaused"] instanceof Boolean)) { return false; }
        if (a["restSec"] != null && !value(a["restSec"],0,86400)) { return false; }
        var rest = a["rest"];
        if (rest != null) {
            if (!(rest instanceof Dictionary)) { return false; }
            if (rest["endsAt"] != null && !value(rest["endsAt"], 0, 9999999999999l)) { return false; }
            if (rest["left"] != null && !value(rest["left"], 0, 86400)) { return false; }
            if (rest["total"] != null && !value(rest["total"], 0, 86400)) { return false; }
            if (rest["forIdx"] != null && (!integer(rest["forIdx"]) || rest["forIdx"] >= a["entries"].size())) { return false; }
            if (rest["forSet"] != null && (!integer(rest["forSet"]) || rest["forSet"] >= 80)) { return false; }
            if (rest["kind"] != null && !GymData.is(rest["kind"], "switch")) { return false; }
            if (rest["paused"] != null && !(rest["paused"] instanceof Boolean)) { return false; }
        }
        var items2 = a["entries"]; for (var idx2 = 0; idx2 < items2.size(); idx2++) { var e = items2[idx2];
            if (!(e instanceof Dictionary) || !text(e["id"]) || !text(e["name"]) || !text(e["mode"]) || !(e["sets"] instanceof Array) || e["sets"].size() > 80) { return false; }
            if (e["restSec"] != null && !value(e["restSec"], 0, 86400)) { return false; }
            if (e["sideRestSec"] != null && !value(e["sideRestSec"], 0, 86400)) { return false; }
            if (e["group"] != null && !text(e["group"])) { return false; }
            var items3 = e["sets"]; for (var idx3 = 0; idx3 < items3.size(); idx3++) { var row = items3[idx3];
                if (!validRow(row)) { return false; }
                if (row["sides"] != null) {
                    if (!(row["sides"] instanceof Dictionary) || !validRow(row["sides"]["L"]) || !validRow(row["sides"]["R"])) { return false; }
                }
            }
        }
        return true;
    }
}

class WorkoutModel {
    const MAX_EVENTS = 96;
    var data;
    var state;
    var error = null;
    function initialize(saved, installation) {
        if (saved != null && (!(saved instanceof Dictionary) || saved["schema"] != 1 ||
            !GymData.text(saved["install"]) || !GymData.integer(saved["counter"]) ||
            !GymData.number(saved["seq"]) || !(saved["outbox"] instanceof Array) ||
            !(saved["ended"] instanceof Array) || !(saved["recordings"] instanceof Array) ||
            (saved["base"] != null && !GymData.validState(saved["base"])))) {
            throw new GymError("Invalid saved workout");
        }
        data = saved == null ? {
            "schema" => 1, "install" => installation, "counter" => 0l,
            "seq" => -1l, "base" => null, "outbox" => [], "ended" => [],
            "recordings" => [], "timing" => null, "hr" => null
        } : GymData.copy(saved);
        project();
    }
    function active() { return state == null ? null : state["active"]; }
    function wid() { return active() == null ? null : active()["id"]; }
    function ended(id) {
        var items4 = data["ended"]; for (var idx4 = 0; idx4 < items4.size(); idx4++) { var item = items4[idx4]; if (item["wid"].equals(id)) { return true; } }
        return false;
    }
    function end(id, discard) {
        if (!ended(id)) {
            data["ended"].add({"wid"=>id, "discard"=>discard});
            if (data["ended"].size() > 64) { data["ended"] = data["ended"].slice(1, null); }
        }
    }
    function recordingClaim(id) {
        for (var i = 0; i < data["recordings"].size(); i++) {
            var claim = data["recordings"][i];
            if (claim["wid"].equals(id)) { return claim; }
        }
        return null;
    }
    function claimRecording(id) {
        if (recordingClaim(id) != null) { return null; }
        var claim = {"wid"=>id, "phase"=>"claimed"};
        data["recordings"].add(claim);
        // Incoming seq guards reject old snapshots; recent IDs also guard fresh
        // delayed snapshots. Keep the active claim and the latest 63 predecessors.
        if (data["recordings"].size() > 64) { data["recordings"] = data["recordings"].slice(1,null); }
        return claim;
    }
    function project() {
        state = GymData.copy(data["base"]);
        var items5 = data["outbox"]; for (var idx5 = 0; idx5 < items5.size(); idx5++) { var event = items5[idx5]; apply(state, event); }
        if (active() != null && ended(wid())) { state["active"] = null; }
    }
    function snapshot(msg, now) {
        error = null;
        if (!(msg instanceof Dictionary) || msg["v"] != 1 || !GymData.is(msg["kind"],"snapshot") || !GymData.integer(msg["seq"])) { error = "Invalid phone message"; return false; }
        if (msg["seq"] <= data["seq"]) { return false; }
        if (GymData.size(msg, 0) > 12288) { error = "Workout too large. Reduce sets on phone."; return false; }
        if (!GymData.validState(msg["state"])) { error = "Invalid workout. Check phone."; return false; }
        var old = wid();
        var incoming = GymData.copy(msg["state"]);
        var a = incoming["active"];
        if (a != null && ended(a["id"])) {
            // A delayed snapshot cannot reopen a locally finished workout.
            incoming["active"] = null;
        }
        if (old != null && (a == null || !old.equals(a["id"]))) {
            var discarded = false;
            if (incoming["discarded"] instanceof Array) {
                var items6 = incoming["discarded"]; for (var idx6 = 0; idx6 < items6.size(); idx6++) { var id = items6[idx6]; if (id.equals(old)) { discarded = true; } }
            }
            end(old, discarded);
        }
        data["seq"] = msg["seq"];
        data["base"] = incoming;
        project();
        alignTimer(now);
        return true;
    }
    function acknowledge(msg, now) {
        if (!(msg instanceof Dictionary) || msg["v"] != 1 || !GymData.is(msg["kind"],"ack") ||
            !GymData.integer(msg["seq"]) || !GymData.validState(msg["state"]) || GymData.size(msg, 0) > 12288) { return false; }
        var ids = msg["ids"];
        if (!(ids instanceof Array) || ids.size() > 256) { return false; }
        var items7 = ids; for (var idx7 = 0; idx7 < items7.size(); idx7++) { var id = items7[idx7]; if (!(id instanceof String)) { return false; } }
        if (msg["seq"] > data["seq"]) {
            snapshot({"v"=>1, "kind"=>"snapshot", "seq"=>msg["seq"], "state"=>msg["state"]}, now);
        }
        var remaining = [];
        var items8 = data["outbox"]; for (var idx8 = 0; idx8 < items8.size(); idx8++) { var ev = items8[idx8];
            if (ids.indexOf(ev["id"]) == -1) { remaining.add(ev); }
        }
        data["outbox"] = remaining;
        project();
        return true;
    }
    function queue(type, fields, now) {
        error = null;
        if (active() == null) { error = "Start a workout on phone"; return false; }
        if (data["outbox"].size() >= MAX_EVENTS) { error = "Sync queue full. Reconnect phone."; return false; }
        data["counter"] += 1l;
        var ev = {"id"=>data["install"] + "-" + data["counter"].toString(), "type"=>type, "wid"=>wid(), "at"=>now};
        var keys = fields.keys();
        var items9 = keys; for (var idx9 = 0; idx9 < items9.size(); idx9++) { var key = items9[idx9]; ev[key] = fields[key]; }
        data["outbox"].add(ev);
        apply(state, ev);
        if (type.equals("finish") || type.equals("discard")) {
            end(ev["wid"], type.equals("discard"));
            data["timing"] = null;
            data["hr"] = null;
        }
        return true;
    }
    function apply(target, ev) {
        if (target == null || target["active"] == null) { return; }
        var a = target["active"];
        if (!a["id"].equals(ev["wid"])) { return; }
        var type = ev["type"];
        if (type.equals("finish") || type.equals("discard")) { target["active"] = null; return; }
        if (type.equals("skipRest")) { a["rest"] = null; return; }
        if (type.equals("pause")) {
            a["watchPaused"] = ev["paused"];
            if (ev.hasKey("rest")) { a["rest"] = GymData.copy(ev["rest"]); return; }
            var rest = a["rest"];
            if (rest != null) {
                if (ev["paused"]) {
                    if (rest["paused"] != true) { rest["left"] = leftFor(rest, ev["at"]); }
                    rest["paused"] = true;
                } else if (rest["paused"] == true) {
                    rest["endsAt"] = ev["at"] + (rest["left"] == null ? 0 : rest["left"]) * 1000l;
                    rest["paused"] = false;
                }
            }
            return;
        }
        var i = ev["entryIdx"];
        if (!GymData.integer(i) || i >= a["entries"].size()) { return; }
        var e = a["entries"][i];
        if (!e["id"].equals(ev["exId"])) { return; }
        if (type.equals("selectExercise")) { a["cur"] = i; return; }
        var j = ev["setIdx"];
        if (!GymData.integer(j) || j >= e["sets"].size()) { return; }
        var row = e["sets"][j];
        if (type.equals("setDone")) {
            var s = row;
            if (ev["side"] != null && row["sides"] != null) { s = row["sides"][ev["side"]]; }
            s["done"] = true;
            var items10 = ["w", "r", "sec"]; for (var idx10 = 0; idx10 < items10.size(); idx10++) { var key = items10[idx10]; if (ev[key] != null) { s[key] = ev[key]; } }
            row["at"] = ev["at"];
            if (row["sides"] != null) { row["done"] = row["sides"]["L"]["done"] && row["sides"]["R"]["done"]; }
            restAfterCompletion(target, a, i, j, ev["at"]);
        }
        if (ev["hr"] != null) { row["hr"] = ev["hr"]; }
        if (ev["restHr"] != null) { row["restHr"] = ev["restHr"]; }
    }
    // Match the phone's supersetUnits: only adjacent entries with the same group
    // belong together. A repeated group after another unit is a separate unit.
    function units(entries) {
        var result = [];
        for (var i = 0; i < entries.size(); i++) {
            var group = entries[i]["group"];
            if (i > 0 && group != null && GymData.is(entries[i-1]["group"], group)) {
                result[result.size()-1].add(i);
            } else { result.add([i]); }
        }
        return result;
    }
    function hasWork(entries, i) {
        var sets = entries[i]["sets"];
        for (var j = 0; j < sets.size(); j++) { if (!sets[j]["done"]) { return true; } }
        return false;
    }
    function unitHasWork(entries, unit) {
        for (var i = 0; i < unit.size(); i++) { if (hasWork(entries, unit[i])) { return true; } }
        return false;
    }
    function startRest(a, seconds, i, j, at, kind) {
        a["rest"] = seconds != null && seconds > 0 ? {
            "endsAt"=>at + seconds * 1000l, "paused"=>false,
            "total"=>seconds, "forIdx"=>i, "forSet"=>j
        } : null;
        if (a["rest"] != null && kind != null) { a["rest"]["kind"] = kind; }
    }
    function restAfterCompletion(target, a, i, j, at) {
        var entries = a["entries"];
        var e = entries[i]; var row = e["sets"][j];
        if (row["sides"] != null && !row["done"]) {
            // Reps have no default break between sides, only an explicit switch rest.
            startRest(a, e["sideRestSec"], i, j, at, "switch");
            return;
        }
        // The phone resolves exercise, set, pyramid and warm-up policy per row.
        // Missing row metadata is supported for older snapshots and saved fixtures.
        var seconds = row["restSec"];
        if (seconds == null) { seconds = e["restSec"]; }
        if (seconds == null) { seconds = a["restSec"]; }
        if (seconds == null) { seconds = target["restSec"]; }

        var all = units(entries); var currentUnit = 0;
        for (var u = 0; u < all.size(); u++) { if (all[u].indexOf(i) != -1) { currentUnit = u; break; } }
        var unit = all[currentUnit];
        if (!unitHasWork(entries, unit)) {
            a["rest"] = null;
            // Find the next unfinished unit, wrapping once just like the phone.
            var nextUnit = null;
            for (var n = 1; n < all.size(); n++) {
                var candidate = all[(currentUnit+n) % all.size()];
                if (unitHasWork(entries, candidate)) { nextUnit = candidate; break; }
            }
            if (nextUnit == null) { return; } // No rest after the workout's last set.
            for (var x = 0; x < nextUnit.size(); x++) {
                var sets = entries[nextUnit[x]]["sets"];
                for (var y = 0; y < sets.size(); y++) {
                    if (sets[y]["warmup"] == true && !sets[y]["done"]) { return; }
                }
            }
        } else if (unit.size() > 1) {
            // supersetFlowStep: visit later unfinished members, then wrap. Rest
            // only when no later member has work, including uneven rounds.
            var pos = unit.indexOf(i); var nextIdx = null;
            for (var later = pos+1; later < unit.size(); later++) {
                if (hasWork(entries, unit[later])) { nextIdx = unit[later]; break; }
            }
            var roundDone = nextIdx == null;
            if (nextIdx == null) {
                for (var earlier = 0; earlier <= pos; earlier++) {
                    if (hasWork(entries, unit[earlier])) { nextIdx = unit[earlier]; break; }
                }
            }
            if (nextIdx != null) { a["cur"] = nextIdx; }
            if (!roundDone) { return; }
        }
        startRest(a, seconds, i, j, at, null);
    }
    function leftFor(rest, now) {
        if (rest == null) { return 0; }
        if (rest["paused"] == true) { return rest["left"] == null ? 0 : rest["left"]; }
        if (rest["endsAt"] == null || rest["endsAt"] <= now) { return 0; }
        return ((rest["endsAt"] - now + 999l) / 1000l).toNumber();
    }
    function restLeft(now) { return active() == null ? 0 : leftFor(active()["rest"], now); }
    function paused() { return active() != null && active()["watchPaused"] == true; }
    function current() {
        if (active() == null) { return null; }
        var i = active()["cur"];
        var e = active()["entries"][i];
        for (var j = 0; j < e["sets"].size(); j++) {
            var s = e["sets"][j];
            if (s["done"]) { continue; }
            var side = null;
            if (s["sides"] != null) { side = s["sides"]["L"]["done"] ? "R" : "L"; }
            return {"entryIdx"=>i, "setIdx"=>j, "exId"=>e["id"], "entry"=>e, "row"=>s, "side"=>side};
        }
        return null;
    }
    function supported(c) {
        if (c == null) { return false; }
        if (c["row"]["unsupported"] == true) { return false; }
        var mode = c["entry"]["mode"];
        var row = c["side"] == null ? c["row"] : c["row"]["sides"][c["side"]];
        // Time-per-side has no per-side seconds in the phone schema. Refuse it.
        if (GymData.is(mode,"time")) { return c["side"] == null && GymData.value(row["sec"], 1, 86400); }
        return GymData.is(mode,"reps") && GymData.value(row["r"], 1, 10000);
    }
    function identity(c) { return wid() + ":" + c["entryIdx"].toString() + ":" + c["setIdx"].toString() + ":" + (c["side"] == null ? "" : c["side"]); }
    function alignTimer(now) {
        var c = current();
        var timing = data["timing"];
        if (c == null || timing == null || !timing["key"].equals(identity(c))) { data["timing"] = null; }
        if (data["hr"] != null && (c == null || !data["hr"]["key"].equals(identity(c)))) { data["hr"] = null; }
        timing = data["timing"];
        if (timing != null) {
            if (paused() && timing["pausedAt"] == null) { timing["pausedAt"] = now; }
            else if (!paused() && timing["pausedAt"] != null) { timing["start"] += now-timing["pausedAt"]; timing["pausedAt"] = null; }
        }
    }
    function startTimed(now) {
        var c = current();
        if (!supported(c) || !GymData.is(c["entry"]["mode"],"time") || paused() || restLeft(now) > 0) { error = "Timed set unavailable"; return false; }
        data["timing"] = {"key"=>identity(c), "start"=>now, "elapsed"=>0, "pausedAt"=>null};
        return true;
    }
    function elapsed(now) {
        var t = data["timing"];
        if (t == null) { return 0; }
        return t["elapsed"] + (((t["pausedAt"] == null ? now : t["pausedAt"]) - t["start"]) / 1000l).toNumber();
    }
    function setDone(now) {
        var c = current();
        if (paused()) { error = "Resume workout first"; return false; }
        if (restLeft(now) > 0) { error = "Skip rest from menu first"; return false; }
        if (c == null) { error = "Exercise complete. Press DOWN."; return false; }
        if (!supported(c)) { error = "Unsupported set. Use phone."; return false; }
        var fields = {"exId"=>c["exId"], "entryIdx"=>c["entryIdx"], "setIdx"=>c["setIdx"]};
        if (c["side"] != null) { fields["side"] = c["side"]; }
        var row = c["side"] == null ? c["row"] : c["row"]["sides"][c["side"]];
        if (GymData.is(c["entry"]["mode"],"time")) {
            if (data["timing"] == null) { return startTimed(now); }
            if (elapsed(now) < 1) { error = "Timer just started"; return false; }
            fields["sec"] = elapsed(now);
        } else { fields["r"] = row["r"]; }
        if (row["w"] != null) { fields["w"] = row["w"]; }
        if (data["hr"] != null && data["hr"]["count"] > 0) {
            var h = data["hr"];
            fields["hr"] = {"avg"=>(h["sum"] / h["count"]).toNumber(), "max"=>h["max"]};
        }
        if (!queue("setDone", fields, now)) { return false; }
        data["timing"] = null;
        data["hr"] = null;
        return true;
    }
    function pause(now) {
        var p = !paused();
        var rest = active() == null ? null : GymData.copy(active()["rest"]);
        if (rest != null) {
            rest["left"] = leftFor(rest, now);
            rest["paused"] = p;
            if (!p) { rest["endsAt"] = now + rest["left"] * 1000l; }
        }
        if (!queue("pause", {"paused"=>p, "rest"=>rest}, now)) { return false; }
        var t = data["timing"];
        if (t != null) {
            if (p) { t["pausedAt"] = now; }
            else if (t["pausedAt"] != null) { t["start"] += now - t["pausedAt"]; t["pausedAt"] = null; }
        }
        return true;
    }
    function next(now) {
        if (active() == null) { return false; }
        var i = (active()["cur"] + 1) % active()["entries"].size();
        if (!queue("selectExercise", {"entryIdx"=>i, "exId"=>active()["entries"][i]["id"]}, now)) { return false; }
        data["timing"] = null; data["hr"] = null;
        return true;
    }
    function sample(bpm, now) {
        var c = current();
        if (c == null || paused() || restLeft(now) > 0 || !GymData.value(bpm, 25, 250)) { return; }
        if (GymData.is(c["entry"]["mode"],"time") && data["timing"] == null) { return; }
        var key = identity(c);
        if (data["hr"] == null || !data["hr"]["key"].equals(key)) { data["hr"] = {"key"=>key, "sum"=>0, "count"=>0, "max"=>0}; }
        var h = data["hr"];
        h["sum"] += bpm; h["count"] += 1; h["max"] = bpm > h["max"] ? bpm : h["max"];
    }
    function batch() { return data["outbox"].slice(0, data["outbox"].size() > 8 ? 8 : data["outbox"].size()); }
}
