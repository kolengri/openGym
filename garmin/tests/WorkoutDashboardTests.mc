import Toybox.Test;

(:test)
function configuredHeartRateZonesHandleBoundariesAndMissingData(logger) {
    var zones = [90,110,130,150,170,190];
    Test.assert(WorkoutDashboard.validZones(zones));
    Test.assert(WorkoutDashboard.zone(null,zones) == null);
    Test.assert(WorkoutDashboard.zone(89,zones) == null);
    Test.assertEqual(WorkoutDashboard.zone(90,zones),1);
    Test.assertEqual(WorkoutDashboard.zone(110,zones),1);
    Test.assertEqual(WorkoutDashboard.zone(111,zones),2);
    Test.assertEqual(WorkoutDashboard.zone(150,zones),3);
    Test.assertEqual(WorkoutDashboard.zone(250,zones),5);
    var invalid = [null,[],[90,110],[90,110,110,150,170,190],[90,110,130,150,170,301],[90,110,130,150,170,"190"]];
    for (var i=0; i<invalid.size(); i++) {
        Test.assert(!WorkoutDashboard.validZones(invalid[i]));
        Test.assert(WorkoutDashboard.zone(142,invalid[i]) == null);
    }
    return true;
}

(:test)
function nextSetPlanUsesUpcomingPrescriptionDuringRest(logger) {
    var m = WorkoutFixtures.model();
    m.active()["entries"][0]["sets"][1]["w"] = 90;
    m.active()["entries"][0]["sets"][1]["r"] = 6;
    var p = WorkoutDashboard.present(m,1000000l);
    Test.assertEqual(p["main"],"80"); Test.assertEqual(p["unit"],GymUi.unit("kg"));
    Test.assertEqual(p["detail"],"5 "+GymUi.string(Rez.Strings.Reps));
    Test.assert(m.startSet(1000000l)); Test.assert(m.setDone(1002000l));
    p = WorkoutDashboard.present(m,1002000l);
    Test.assertEqual(p["main"],"01:00");
    Test.assertEqual(p["phase"],"2/2");
    Test.assertEqual(p["detail"],"90 "+GymUi.unit("kg")+" × 6");
    Test.assertEqual(p["command"],"skipRest");
    Test.assert(m.queue("skipRest",{},1003000l));
    p = WorkoutDashboard.present(m,1003000l);
    Test.assertEqual(p["main"],"90"); Test.assertEqual(p["detail"],"6 "+GymUi.string(Rez.Strings.Reps));
    Test.assertEqual(p["command"],"startSet");
    return true;
}

(:test)
function bodyweightAndSidePrescriptionsKeepTheirOwnValues(logger) {
    var m = WorkoutFixtures.model(); var e = m.current()["entry"]; var row = m.current()["row"];
    e["bodyweight"] = true; row["w"] = 0;
    var p = WorkoutDashboard.present(m,1000000l);
    Test.assertEqual(p["main"],"5"); Test.assertEqual(p["unit"],GymUi.string(Rez.Strings.Reps));
    Test.assertEqual(p["detail"],GymUi.string(Rez.Strings.Bodyweight));
    e["bodyweight"] = false;
    row["sides"] = {"L"=>{"w"=>40,"r"=>8,"done"=>true},"R"=>{"w"=>42,"r"=>6,"done"=>false}};
    p = WorkoutDashboard.present(m,1000000l);
    Test.assertEqual(p["main"],"42");
    Test.assertEqual(p["detail"],"6 "+GymUi.string(Rez.Strings.Reps));
    Test.assert(p["phase"].find(GymUi.side("R")) != null);
    Test.assertEqual(WorkoutDashboard.progress(m,1000000l),0.25);
    return true;
}

(:test)
function dashboardProgressUsesActualElapsedAndFreezesOnPause(logger) {
    var m = WorkoutFixtures.model(); var c = m.current();
    c["entry"]["mode"] = "cardio"; c["entry"]["goalKm"] = 2.5; c["row"]["sec"] = 120;
    var p = WorkoutDashboard.present(m,1000000l);
    Test.assertEqual(p["main"],"00:00"); Test.assertEqual(p["progress"],0.0);
    Test.assert(p["detail"].find("2.5") != null); Test.assert(p["detail"].find("02:00") != null);
    Test.assert(m.startSet(1000000l));
    Test.assertEqual(WorkoutDashboard.progress(m,1060000l),0.5);
    Test.assert(m.pause(1060000l));
    Test.assertEqual(WorkoutDashboard.progress(m,1090000l),0.5);
    Test.assertEqual(WorkoutDashboard.present(m,1090000l)["main"],"01:00");
    Test.assert(m.pause(1090000l));
    Test.assertEqual(WorkoutDashboard.progress(m,1200000l),1.0);
    c["row"]["sec"] = null;
    Test.assertEqual(WorkoutDashboard.progress(m,1200000l),0.0);
    Test.assert(!c["row"]["done"]);
    return true;
}

(:test)
function restProgressFreezesAndSupersetPlanTracksCurrentExercise(logger) {
    var a = WorkoutFixtures.reps("a",2,60); a["group"] = "pair";
    var b = WorkoutFixtures.reps("b",2,60); b["group"] = "pair";
    b["sets"][0]["w"] = 30;
    var m = WorkoutFixtures.fromEntries([a,b]);
    Test.assert(m.setDone(1000000l));
    var p = WorkoutDashboard.present(m,1000000l);
    Test.assertEqual(p["title"],"b"); Test.assertEqual(p["main"],"30");
    m = WorkoutFixtures.model(); Test.assert(m.setDone(1000000l));
    Test.assertEqual(WorkoutDashboard.progress(m,1030000l),0.5);
    Test.assert(m.pause(1030000l));
    Test.assertEqual(WorkoutDashboard.progress(m,1060000l),0.5);
    return true;
}

(:test)
function betweenExerciseRestPreviewsNextUnitWithoutSelectingIt(logger) {
    var later = WorkoutFixtures.reps("later",2,60);
    later["sets"][0]["w"] = 45; later["sets"][0]["r"] = 8;
    var m = WorkoutFixtures.fromEntries([WorkoutFixtures.reps("first",1,60),later]);
    Test.assert(m.setDone(1000000l));
    var p = WorkoutDashboard.present(m,1000000l);
    Test.assertEqual(p["title"],"later"); Test.assertEqual(p["phase"],"1/2");
    Test.assertEqual(p["detail"],"45 "+GymUi.unit("kg")+" × 8");
    Test.assertEqual(p["main"],"01:00"); Test.assertEqual(p["command"],"skipRest");
    Test.assertEqual(m.active()["cur"],0); Test.assert(m.current() == null);
    Test.assertEqual(m.batch().size(),1); Test.assert(!m.active()["entries"][1]["sets"][0]["done"]);
    // Finishing the last unit wraps to earlier unfinished work.
    m = WorkoutFixtures.fromEntries([later,WorkoutFixtures.reps("last",1,60)]);
    Test.assert(m.next(1000000l)); Test.assert(m.setDone(1000000l));
    Test.assertEqual(WorkoutDashboard.present(m,1000000l)["title"],"later");
    Test.assertEqual(m.active()["cur"],1);
    // Closing a superset also previews the following unit, not a spent member.
    var a = WorkoutFixtures.reps("a",1,60); a["group"] = "pair";
    var b = WorkoutFixtures.reps("b",1,60); b["group"] = "pair";
    m = WorkoutFixtures.fromEntries([a,b,later]);
    Test.assert(m.setDone(1000000l)); Test.assert(m.setDone(1001000l));
    Test.assertEqual(WorkoutDashboard.present(m,1001000l)["title"],"later");
    Test.assertEqual(m.active()["cur"],1); Test.assert(m.current() == null);
    return true;
}
