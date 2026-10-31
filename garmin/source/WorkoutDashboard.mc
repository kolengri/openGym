import Toybox.Lang;

// Presentation only: prescriptions and timing remain owned by WorkoutModel.
module WorkoutDashboard {
    function clamp(value) { return value < 0 ? 0.0 : value > 1 ? 1.0 : value; }
    function validZones(zones) {
        if (!(zones instanceof Array) || zones.size() != 6) { return false; }
        for (var i=0; i<zones.size(); i++) {
            if (!GymData.value(zones[i],0,300) || (i > 0 && zones[i] <= zones[i-1])) { return false; }
        }
        return true;
    }
    function zone(bpm, zones) {
        if (!GymData.value(bpm,25,250) || !validZones(zones) || bpm < zones[0]) { return null; }
        for (var i=1; i<zones.size(); i++) { if (bpm <= zones[i]) { return i; } }
        return 5;
    }
    function progress(model, at) {
        var active = model.active();
        if (active == null) { return 0.0; }
        var rest = model.restLeft(at);
        if (rest > 0 && active["rest"] != null && GymData.value(active["rest"]["total"],1,86400)) {
            return clamp(rest.toFloat()/active["rest"]["total"]);
        }
        var c = model.current();
        if (c == null) { return 1.0; }
        if (GymData.is(c["entry"]["mode"],"cardio") || GymData.is(c["entry"]["mode"],"time")) {
            var target = c["row"]["sec"];
            return GymData.value(target,1,86400) ? clamp(model.elapsed(at).toFloat()/target) : 0.0;
        }
        var sets = c["entry"]["sets"]; var done = 0.0;
        for (var i=0; i<sets.size(); i++) {
            var row = sets[i];
            if (row["done"] == true) { done += 1; }
            else if (row["sides"] != null) {
                if (row["sides"]["L"]["done"] == true) { done += 0.5; }
                if (row["sides"]["R"]["done"] == true) { done += 0.5; }
            }
        }
        return sets.size() == 0 ? 0.0 : clamp(done/sets.size());
    }
    function restPreview(model) {
        var a = model.active(); var entries = a["entries"]; var units = model.units(entries); var currentUnit = 0;
        for (var u=0; u<units.size(); u++) { if (units[u].indexOf(a["cur"]) != -1) { currentUnit = u; break; } }
        // Follow restAfterCompletion's wrapped unit order without selecting it.
        for (var n=1; n<units.size(); n++) {
            var unit = units[(currentUnit+n)%units.size()];
            for (var x=0; x<unit.size(); x++) {
                var i = unit[x]; var e = entries[i];
                for (var j=0; j<e["sets"].size(); j++) {
                    var row = e["sets"][j];
                    if (!row["done"]) {
                        var side = row["sides"] == null ? null : (row["sides"]["L"]["done"] ? "R" : "L");
                        return {"entryIdx"=>i,"setIdx"=>j,"exId"=>e["id"],"entry"=>e,"row"=>row,"side"=>side};
                    }
                }
            }
        }
        return null;
    }
    function present(model, at) {
        var a = model.active();
        if (a == null) { return null; }
        var e = a["entries"][a["cur"]]; var c = model.current(); var rest = model.restLeft(at);
        var preview = c == null && rest > 0;
        if (preview) { c = restPreview(model); if (c != null) { e = c["entry"]; } }
        var timed = GymData.is(e["mode"],"cardio") || GymData.is(e["mode"],"time"); var warmup = false;
        var phase = GymUi.string(Rez.Strings.Complete);
        var main = e["sets"].size().toString()+"/"+e["sets"].size().toString();
        var unit = GymUi.string(Rez.Strings.Complete); var detail = GymUi.string(Rez.Strings.AllSetsDone);
        var detailIcon = "next";
        if (c != null) {
            var row = c["side"] == null ? c["row"] : c["row"]["sides"][c["side"]];
            var load = row["w"]; var reps = row["r"];
            var bw = e["bodyweight"] == true || load == null || load == 0;
            var weightUnit = GymUi.unit(model.state["unit"]);
            var prescription = WorkoutControls.prescription(c,weightUnit);
            var counter = (c["setIdx"]+1).toString()+"/"+e["sets"].size().toString();
            if (c["side"] != null) { counter += " "+GymUi.side(c["side"]); }
            // Keep the side visible within the small round header, including rest.
            phase = timed ? GymUi.string(Rez.Strings.SetTime) : counter;
            warmup = !timed && c["row"]["warmup"] == true;
            if (timed) {
                main = WorkoutControls.clock(model.elapsed(at)); unit = GymUi.string(Rez.Strings.SetTime);
                detail = GymUi.string(Rez.Strings.Target)+" "+prescription["value"];
                var km = e["goalKm"];
                if (GymData.value(c["row"]["sec"],1,86400) && km != null && km > 0) { detail += " · "+WorkoutControls.decimal(km)+" "+GymUi.string(Rez.Strings.Kilometers); }
                if (GymData.is(e["mode"],"time") && load != null && load > 0) { detail += " · "+WorkoutControls.decimal(load)+" "+weightUnit; }
                detailIcon = "target";
            } else {
                main = bw ? (reps == null ? "--" : WorkoutControls.decimal(reps)) : WorkoutControls.decimal(load);
                unit = bw ? GymUi.string(Rez.Strings.Reps) : weightUnit;
                detail = prescription["detail"]; detailIcon = bw ? "body" : "weight";
                if (!preview && model.data["timing"] != null) { detail = WorkoutControls.clock(model.elapsed(at))+" · "+detail; detailIcon = "clock"; }
                if (rest > 0) {
                    detail = (bw ? prescription["detail"] : WorkoutControls.decimal(load)+" "+weightUnit)+" × "+(reps == null ? "--" : WorkoutControls.decimal(reps));
                }
            }
            if (!model.supported(c)) { main = "--"; unit = GymUi.string(Rez.Strings.UsePhone); detail = GymUi.string(Rez.Strings.UsePhone); detailIcon = "phone"; }
        }
        if (rest > 0) { main = WorkoutControls.clock(rest); unit = GymUi.string(Rez.Strings.Rest); }
        if (model.paused()) { phase = GymUi.string(Rez.Strings.Paused); warmup = false; }
        return {"title"=>e["name"],"phase"=>phase,"warmup"=>warmup,"main"=>main,"unit"=>unit,"detail"=>detail,"detailIcon"=>detailIcon,
            "progress"=>progress(model,at),"command"=>WorkoutControls.primary(model,at)};
    }
}
