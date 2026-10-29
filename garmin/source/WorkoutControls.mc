import Toybox.Lang;

// Rendering and hit testing share these rectangles, including on round displays.
module WorkoutControls {
    function rect(id, w, h) {
        if (id.equals("primary")) { return [(w*0.18).toNumber(), (h*0.64).toNumber(), (w*0.64).toNumber(), (h*0.13).toNumber()]; }
        if (id.equals("next")) { return [(w*0.26).toNumber(), (h*0.78).toNumber(), (w*0.48).toNumber(), (h*0.10).toNumber()]; }
        return null;
    }
    function contains(r, x, y) { return x >= r[0] && y >= r[1] && x < r[0]+r[2] && y < r[1]+r[3]; }
    function hit(w, h, x, y, active, modal) {
        if (contains(rect("primary",w,h),x,y) && (active || modal)) { return modal ? "dismiss" : "primary"; }
        if (!modal && active && contains(rect("next",w,h),x,y)) { return "next"; }
        return null;
    }
    function primary(model, at) {
        if (model.active() == null) { return null; }
        if (model.paused()) { return "pause"; }
        if (model.restLeft(at) > 0) { return "skipRest"; }
        var c = model.current();
        if (c == null) { return model.active()["cur"] == model.active()["entries"].size()-1 ? "finish" : "next"; }
        if (!model.supported(c)) { return null; }
        return model.data["timing"] == null ? "startSet" : "setDone";
    }
    function label(action) {
        if (action == null) { return GymUi.string(Rez.Strings.UsePhone); }
        if (action.equals("pause")) { return GymUi.string(Rez.Strings.Resume); }
        if (action.equals("skipRest")) { return GymUi.string(Rez.Strings.SkipRest); }
        if (action.equals("finish")) { return GymUi.string(Rez.Strings.FinishWorkout); }
        if (action.equals("next")) { return GymUi.string(Rez.Strings.NextExercise); }
        return action.equals("startSet") ? GymUi.string(Rez.Strings.StartSet) : GymUi.string(Rez.Strings.CompleteSet);
    }
    // The main number is what the exercise asks for, rather than an empty load.
    function prescription(c, unit) {
        var row = c["side"] == null ? c["row"] : c["row"]["sides"][c["side"]];
        var mode = c["entry"]["mode"];
        if (GymData.is(mode,"time") || GymData.is(mode,"cardio")) {
            var km = c["entry"]["goalKm"];
            var distance = km != null && km > 0 ? decimal(km)+" "+GymUi.string(Rez.Strings.Kilometers) : null;
            var timed = GymData.value(c["row"]["sec"],1,86400);
            var detail = GymUi.string(Rez.Strings.Target)+(!timed || distance == null ? "" : " "+distance);
            if (GymData.is(mode,"time") && row["w"] != null && row["w"] > 0) { detail += " · "+decimal(row["w"])+" "+unit; }
            return {"value"=>timed ? clock(c["row"]["sec"]) : (distance == null ? "--:--" : distance),
                "detail"=>detail};
        }
        var load = row["w"];
        var bw = c["entry"]["bodyweight"] == true || load == null || load == 0;
        var reps = row["r"] == null ? "--" : decimal(row["r"]);
        if (bw) {
            return {"value"=>reps+" "+GymUi.string(Rez.Strings.Reps),
                "detail"=>load != null && load > 0 ? "+"+decimal(load)+" "+unit : GymUi.string(Rez.Strings.Bodyweight)};
        }
        return {"value"=>decimal(load)+" "+unit, "detail"=>reps+" "+GymUi.string(Rez.Strings.Reps)};
    }
    function clock(seconds) {
        seconds = (seconds < 0 ? 0 : seconds).toNumber();
        return (seconds/60).toNumber().format("%02d")+":"+(seconds%60).format("%02d");
    }
    // Display precision only: keep stored loads and command payloads unchanged.
    function decimal(value) {
        var text = value.toDouble().format("%.2f");
        while (text.length() > 1 && text.substring(text.length()-1,text.length()).equals("0")) {
            text = text.substring(0,text.length()-1);
        }
        if (text.substring(text.length()-1,text.length()).equals(".")) { text = text.substring(0,text.length()-1); }
        return text.equals("-0") ? "0" : text;
    }
}

// Ephemeral notification state never completes a set or queues a command.
// Reconciliation can replace dictionaries; use workout/set identity, not objects.
class WorkoutAlerts {
    var restKey = null; var restDeadline = null; var restPaused = false;
    var restArmed = false; var restFired = false;
    var timedKey = null; var timedTarget = null; var timedFired = false;
    function initialize() {}
    function token(value) { return value == null ? "" : value.toString(); }
    function restIdentity(model) {
        var a = model.active();
        if (a == null || a["rest"] == null) { return null; }
        var r = a["rest"];
        var at = null;
        if (r["forIdx"] != null && r["forSet"] != null && r["forSet"] < a["entries"][r["forIdx"]]["sets"].size()) { at = a["entries"][r["forIdx"]]["sets"][r["forSet"]]["at"]; }
        return model.wid()+":"+token(r["forIdx"])+":"+token(r["forSet"])+":"+token(r["total"])+":"+token(r["kind"])+":"+token(at);
    }
    function valid(alert, model) {
        if (alert == null || !GymData.is(model.wid(),alert["wid"])) { return false; }
        if (alert["kind"].equals("rest")) { return GymData.is(restIdentity(model),alert["key"]) && model.active()["rest"]["endsAt"] == alert["endsAt"]; }
        var t = model.data["timing"];
        var c = model.current();
        return t != null && c != null && GymData.is(t["key"],alert["key"]) && c["row"]["sec"] == alert["target"];
    }
    function poll(model, at) {
        var result = null;
        var key = restIdentity(model);
        if (key == null) {
            restKey = null; restDeadline = null; restArmed = false; restFired = false; restPaused = false;
        } else {
            var r = model.active()["rest"];
            var p = model.paused() || r["paused"] == true;
            // A moved running deadline is a new rest. A pause/resume moves the
            // deadline too, but must retain the already-delivered alert fence.
            if (!GymData.is(key,restKey) || (!restPaused && !p && restDeadline != r["endsAt"])) {
                restArmed = false; restFired = false;
            }
            restKey = key; restDeadline = r["endsAt"]; restPaused = p;
            if (model.restLeft(at) > 0) { restArmed = true; }
            if (restArmed && !restFired && !p && model.restLeft(at) == 0) {
                restFired = true;
                result = {"kind"=>"rest", "wid"=>model.wid(), "key"=>key, "endsAt"=>r["endsAt"]};
            }
        }
        var t = model.data["timing"]; var c = model.current();
        key = t == null ? null : t["key"];
        var target = c == null ? null : c["row"]["sec"];
        if (!GymData.is(key,timedKey) || timedTarget != target) { timedKey = key; timedTarget = target; timedFired = false; }
        if (t != null && c != null && model.supported(c) &&
            (GymData.is(c["entry"]["mode"],"time") || GymData.is(c["entry"]["mode"],"cardio")) && GymData.value(target,1,86400) &&
            !model.paused() && !timedFired && model.elapsed(at) >= c["row"]["sec"]) {
            timedFired = true;
            result = {"kind"=>"timed", "wid"=>model.wid(), "key"=>key, "target"=>target};
        }
        return result;
    }
}
