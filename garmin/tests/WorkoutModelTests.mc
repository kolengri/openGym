import Toybox.Lang;
import Toybox.Test;
import Toybox.Application;
import Toybox.WatchUi;

// Do not start the production sensor, timer, FIT or transport during model tests.
(:test)
class WorkoutTestsApp extends Application.AppBase {
    function initialize() { AppBase.initialize(); }
    function getInitialView() { return [new WatchUi.View()]; }
}

(:test)
module WorkoutFixtures {
    function snapshot(seq) {
        return {"v"=>1, "kind"=>"snapshot", "seq"=>seq,
            "state"=>{"v"=>1, "unit"=>"kg", "restSec"=>60,
                "settings"=>{"recording"=>true, "restHaptics"=>true},
                "active"=>{"id"=>"workout-a", "cur"=>0, "restSec"=>60,
                    "entries"=>[
                        {"id"=>"squat", "name"=>"Squat", "mode"=>"reps", "sets"=>[
                            {"w"=>80, "r"=>5, "done"=>false}, {"w"=>80,"r"=>5,"done"=>false}]},
                        {"id"=>"plank", "name"=>"Plank", "mode"=>"time", "sets"=>[
                            {"sec"=>30,"done"=>false}]}]}}};
    }
    function model() {
        var m = new WorkoutModel(null,"test-install");
        var accepted = m.snapshot(snapshot(1),1000000l);
        Test.assertMessage(accepted,m.error == null ? "Fixture rejected" : m.error);
        return m;
    }
    function ack(model, snapshot, ids) {
        return model.acknowledge({"v"=>1,"kind"=>"ack","seq"=>snapshot["seq"],"state"=>snapshot["state"],"ids"=>ids},1001000l);
    }
    function reps(id, count, rest) {
        var sets = [];
        for (var i=0;i<count;i++) { sets.add({"r"=>5,"done"=>false,"restSec"=>rest}); }
        return {"id"=>id,"name"=>id,"mode"=>"reps","sets"=>sets};
    }
    function fromEntries(entries) {
        var snap = snapshot(1); snap["state"]["active"]["entries"] = entries;
        var m = new WorkoutModel(null,"rest-test");
        Test.assertMessage(m.snapshot(snap,1000000l),"Rest fixture rejected");
        return m;
    }
}

(:test)
function offlineRebootReplaysStableEvents(logger) {
    var m = WorkoutFixtures.model();
    Test.assert(m.setDone(1000000l));
    var id = m.batch()[0]["id"];
    var rebooted = new WorkoutModel(GymData.copy(m.data),"unused");
    Test.assertEqual(rebooted.batch()[0]["id"],id);
    Test.assert(rebooted.active()["entries"][0]["sets"][0]["done"]);
    Test.assertEqual(rebooted.restLeft(1010000l),50);
    Test.assert(rebooted.next(1010000l));
    Test.assertNotEqual(rebooted.batch()[1]["id"],id);
    return true;
}

(:test)
function newerSnapshotRebasesPendingCommands(logger) {
    var m = WorkoutFixtures.model();
    Test.assert(m.setDone(1000000l));
    Test.assert(m.next(1001000l));
    var fresh = WorkoutFixtures.snapshot(8);
    fresh["state"]["active"]["entries"][0]["sets"][1]["w"] = 90;
    Test.assert(m.snapshot(fresh,1002000l));
    Test.assert(m.active()["entries"][0]["sets"][0]["done"]);
    Test.assertEqual(m.active()["entries"][0]["sets"][1]["w"],90);
    Test.assertEqual(m.active()["cur"],1);
    Test.assert(!m.snapshot(WorkoutFixtures.snapshot(7),1003000l));
    Test.assertEqual(m.active()["cur"],1);
    return true;
}

(:test)
function ackNeedsPersistedSnapshotFence(logger) {
    var m = WorkoutFixtures.model();
    Test.assert(m.setDone(1000000l));
    var id = m.batch()[0]["id"];
    Test.assert(!m.acknowledge({"v"=>1,"kind"=>"ack","ids"=>[id]},1001000l));
    Test.assertEqual(m.data["outbox"].size(),1);
    var post = WorkoutFixtures.snapshot(3);
    post["state"]["active"]["entries"][0]["sets"][0]["done"] = true;
    Test.assert(WorkoutFixtures.ack(m,post,[id]));
    Test.assertEqual(m.data["outbox"].size(),0);
    Test.assert(!m.snapshot(WorkoutFixtures.snapshot(2),1002000l));
    Test.assert(m.active()["entries"][0]["sets"][0]["done"]);
    Test.assert(WorkoutFixtures.ack(m,post,[id]));
    return true;
}

(:test)
function partialAckKeepsOrderedTail(logger) {
    var m = WorkoutFixtures.model();
    m.setDone(1000000l); m.next(1001000l);
    var one = m.batch()[0]["id"]; var two = m.batch()[1]["id"];
    var post = WorkoutFixtures.snapshot(2);
    post["state"]["active"]["entries"][0]["sets"][0]["done"] = true;
    Test.assert(WorkoutFixtures.ack(m,post,[one]));
    Test.assertEqual(m.batch().size(),1);
    Test.assertEqual(m.batch()[0]["id"],two);
    Test.assertEqual(m.active()["cur"],1);
    return true;
}

(:test)
function oldAckFenceAndSameSequenceChunksRemoveEventsWithoutRewind(logger) {
    var m = WorkoutFixtures.model();
    m.setDone(1000000l); m.next(1001000l);
    var first=m.batch()[0]["id"]; var second=m.batch()[1]["id"];
    var latest=WorkoutFixtures.snapshot(1800000000009l);
    latest["state"]["active"]["cur"]=1;
    latest["state"]["active"]["entries"][0]["sets"][0]["done"]=true;
    latest["state"]["active"]["entries"][0]["sets"][1]["w"]=95;
    Test.assert(m.snapshot(latest,1002000l));
    var old=WorkoutFixtures.snapshot(1800000000003l);
    old["state"]["active"]["entries"][0]["sets"][0]["done"]=true;
    Test.assert(WorkoutFixtures.ack(m,old,[first]));
    Test.assertEqual(m.data["seq"],1800000000009l);
    Test.assertEqual(m.active()["entries"][0]["sets"][1]["w"],95);
    Test.assertEqual(m.active()["cur"],1);
    Test.assertEqual(m.batch().size(),1);
    Test.assert(WorkoutFixtures.ack(m,latest,[second]));
    Test.assertEqual(m.batch().size(),0);
    Test.assertEqual(m.active()["cur"],1);
    Test.assert(WorkoutFixtures.ack(m,latest,[first]));
    return true;
}

(:test)
function pauseFreezesRestAndTimedSet(logger) {
    var m = WorkoutFixtures.model();
    m.setDone(1000000l);
    m.pause(1010000l);
    Test.assertEqual(m.restLeft(1040000l),50);
    Test.assertEqual(m.batch()[1]["rest"]["left"],50);
    Test.assertEqual(m.batch()[1]["rest"]["total"],60);
    Test.assert(m.batch()[1]["rest"]["paused"]);
    m.pause(1040000l);
    Test.assertEqual(m.restLeft(1050000l),40);
    Test.assertEqual(m.batch()[2]["rest"]["endsAt"],1090000l);
    m.next(1050000l);
    Test.assert(m.queue("skipRest",{},1050000l));
    Test.assert(m.setDone(1050000l)); // Start the timed set, do not emit completion.
    Test.assertEqual(m.data["outbox"].size(),5);
    m.pause(1060000l);
    Test.assertEqual(m.elapsed(1090000l),10);
    m.pause(1090000l);
    Test.assertEqual(m.elapsed(1105000l),25);
    Test.assert(m.setDone(1105000l));
    var events = m.data["outbox"];
    Test.assertEqual(events[events.size()-1]["sec"],25);
    return true;
}

(:test)
function perSideCompletionDoesNotInventOtherSide(logger) {
    var snapshot = WorkoutFixtures.snapshot(1);
    snapshot["state"]["active"]["entries"][0]["sets"][0]["sides"] = {
        "L"=>{"w"=>12,"r"=>8,"done"=>false},"R"=>{"w"=>12,"r"=>8,"done"=>false}};
    var m = new WorkoutModel(null,"side-test"); m.snapshot(snapshot,1000000l);
    Test.assert(m.setDone(1000000l));
    Test.assertEqual(m.batch()[0]["side"],"L");
    Test.assert(!m.active()["entries"][0]["sets"][0]["done"]);
    Test.assert(m.active()["rest"] == null);
    Test.assert(m.setDone(1002000l));
    Test.assertEqual(m.batch()[1]["side"],"R");
    Test.assert(m.active()["entries"][0]["sets"][0]["done"]);
    Test.assertEqual(m.restLeft(1002000l),60);
    return true;
}

(:test)
function nextPreservesRestThroughRestartAndAcknowledgement(logger) {
    var m = WorkoutFixtures.model();
    Test.assert(m.setDone(1000000l));
    Test.assert(m.next(1010000l));
    Test.assertEqual(m.active()["cur"],1);
    Test.assertEqual(m.active()["rest"]["endsAt"],1060000l);
    Test.assertEqual(m.restLeft(1010000l),50);
    Test.assert(!m.setDone(1010000l));
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    Test.assertEqual(m.active()["rest"]["endsAt"],1060000l);
    var post = {"seq"=>2,"state"=>GymData.copy(m.state)};
    Test.assert(WorkoutFixtures.ack(m,post,[m.batch()[0]["id"],m.batch()[1]["id"]]));
    Test.assertEqual(m.batch().size(),0);
    Test.assertEqual(m.active()["cur"],1);
    Test.assertEqual(m.restLeft(1020000l),40);
    Test.assertEqual(m.active()["rest"]["forIdx"],0);
    Test.assertEqual(m.active()["rest"]["forSet"],0);
    return true;
}

(:test)
function explicitSkipRestClearsPausedRestWithoutChangingExercise(logger) {
    var m = WorkoutFixtures.model();
    Test.assert(m.setDone(1000000l));
    Test.assert(m.pause(1010000l));
    Test.assert(m.next(1020000l));
    Test.assertEqual(m.restLeft(1020000l),50);
    Test.assert(m.queue("skipRest",{},1020000l));
    Test.assert(m.active()["rest"] == null);
    Test.assertEqual(m.active()["cur"],1);
    Test.assert(m.paused());
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    Test.assert(m.active()["rest"] == null);
    return true;
}

(:test)
function ordinaryNoTimerRowDoesNotInheritGlobalRest(logger) {
    var e = WorkoutFixtures.reps("no-timer",2,0); e["restSec"] = 0;
    var m = WorkoutFixtures.fromEntries([e,WorkoutFixtures.reps("later",1,60)]);
    Test.assert(m.setDone(1000000l));
    Test.assert(m.active()["rest"] == null);
    Test.assert(m.setDone(1001000l));
    Test.assert(m.active()["rest"] == null);
    return true;
}

(:test)
function effectiveRowZeroAndPositiveOverrideExerciseAndGlobalRest(logger) {
    var e = WorkoutFixtures.reps("squat",3,0);
    e["restSec"] = 120;
    e["sets"][1]["restSec"] = 35;
    var m = WorkoutFixtures.fromEntries([e,WorkoutFixtures.reps("later",1,60)]);
    Test.assert(m.setDone(1000000l)); // Effective No timer must not inherit 120 or 60.
    Test.assert(m.active()["rest"] == null);
    Test.assert(m.setDone(1001000l));
    Test.assertEqual(m.restLeft(1001000l),35);
    Test.assertEqual(m.active()["rest"]["total"],35);
    Test.assertEqual(m.active()["rest"]["forSet"],1);
    return true;
}

(:test)
function effectiveWarmupRowsKeepTheirResolvedRest(logger) {
    var e = WorkoutFixtures.reps("ramp",3,0);
    e["sets"][0]["warmup"] = true; e["sets"][0]["restSec"] = 20;
    e["sets"][1]["warmup"] = true; e["sets"][1]["restSec"] = 75;
    var m = WorkoutFixtures.fromEntries([e,WorkoutFixtures.reps("later",1,60)]);
    Test.assert(m.setDone(1000000l));
    Test.assertEqual(m.restLeft(1000000l),20);
    Test.assert(m.queue("skipRest",{},1001000l));
    Test.assert(m.setDone(1002000l)); // Last warm-up carries the working rest.
    Test.assertEqual(m.restLeft(1002000l),75);
    Test.assert(m.queue("skipRest",{},1003000l));
    Test.assert(m.setDone(1004000l));
    Test.assert(m.active()["rest"] == null);
    return true;
}

(:test)
function explicitSideRestAndPauseSurviveOfflineAcknowledgementFence(logger) {
    var snap = WorkoutFixtures.snapshot(1);
    var e = snap["state"]["active"]["entries"][0];
    e["sideRestSec"] = 15; e["sets"][0]["restSec"] = 80;
    e["sets"][0]["sides"] = {
        "L"=>{"r"=>8,"done"=>false},"R"=>{"r"=>8,"done"=>false}};
    var m = new WorkoutModel(null,"switch-test"); Test.assert(m.snapshot(snap,1000000l));
    Test.assert(m.setDone(1000000l));
    Test.assertEqual(m.restLeft(1000000l),15);
    Test.assertEqual(m.active()["rest"]["kind"],"switch");
    Test.assertEqual(m.active()["rest"]["forIdx"],0);
    Test.assertEqual(m.active()["rest"]["forSet"],0);
    Test.assert(!m.setDone(1001000l));
    Test.assert(m.pause(1005000l));
    Test.assertEqual(m.batch()[1]["rest"]["left"],10);
    Test.assertEqual(m.batch()[1]["rest"]["total"],15);
    Test.assertEqual(m.batch()[1]["rest"]["kind"],"switch");
    // Phone's old countdown has expired before reconnect, but the pending pause
    // must restore the watch's ten seconds over the acknowledged set snapshot.
    var post = GymData.copy(snap); post["seq"] = 2;
    post["state"]["active"]["entries"][0]["sets"][0]["sides"]["L"]["done"] = true;
    post["state"]["active"]["rest"] = null;
    Test.assert(m.acknowledge({"v"=>1,"kind"=>"ack","seq"=>2,"state"=>post["state"],"ids"=>[m.batch()[0]["id"]]},1200000l));
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    Test.assert(m.paused());
    Test.assertEqual(m.restLeft(1200000l),10);
    Test.assertEqual(m.active()["rest"]["kind"],"switch");
    Test.assert(m.pause(1200000l));
    Test.assertEqual(m.active()["rest"]["endsAt"],1210000l);
    Test.assertEqual(m.batch()[1]["rest"]["kind"],"switch");
    var resume = {"seq"=>3,"state"=>GymData.copy(m.state)};
    Test.assert(WorkoutFixtures.ack(m,resume,[m.batch()[0]["id"],m.batch()[1]["id"]]));
    Test.assertEqual(m.restLeft(1205000l),5);
    Test.assert(m.setDone(1210000l));
    Test.assertEqual(m.batch()[0]["side"],"R");
    Test.assertEqual(m.restLeft(1210000l),80);
    Test.assert(m.active()["rest"]["kind"] == null);
    return true;
}

(:test)
function finalWorkoutSetHasNoRestButEarlierUnfinishedUnitStillDoes(logger) {
    var m = WorkoutFixtures.fromEntries([WorkoutFixtures.reps("earlier",1,45),WorkoutFixtures.reps("last",1,90)]);
    Test.assert(m.next(1000000l));
    Test.assert(m.setDone(1000000l)); // Earlier work means this is not the final set.
    Test.assertEqual(m.restLeft(1000000l),90);
    Test.assert(m.queue("skipRest",{},1001000l));
    Test.assert(m.next(1001000l));
    Test.assert(m.setDone(1002000l));
    Test.assert(m.active()["rest"] == null);
    return true;
}

(:test)
function supersetsAdvanceSkipSpentMembersAndRestAtRoundBoundary(logger) {
    var a = WorkoutFixtures.reps("a",2,90); a["group"] = "pair";
    var b = WorkoutFixtures.reps("b",1,90); b["group"] = "pair";
    var c = WorkoutFixtures.reps("c",2,90); c["group"] = "pair";
    var m = WorkoutFixtures.fromEntries([a,b,c,WorkoutFixtures.reps("later",1,30)]);
    Test.assert(m.setDone(1000000l));
    Test.assertEqual(m.active()["cur"],1); Test.assert(m.active()["rest"] == null);
    Test.assert(m.setDone(1001000l));
    Test.assertEqual(m.active()["cur"],2); Test.assert(m.active()["rest"] == null);
    Test.assert(m.setDone(1002000l));
    Test.assertEqual(m.active()["cur"],0); Test.assertEqual(m.restLeft(1002000l),90);
    Test.assertEqual(m.active()["rest"]["forIdx"],2);
    Test.assert(m.queue("skipRest",{},1003000l));
    Test.assert(m.setDone(1004000l));
    Test.assertEqual(m.active()["cur"],2); Test.assert(m.active()["rest"] == null);
    Test.assert(m.setDone(1005000l));
    Test.assertEqual(m.restLeft(1005000l),90); // Closing group rests before next unit.
    Test.assertEqual(m.active()["rest"]["forSet"],1);
    return true;
}

(:test)
function supersetsUseLastActiveMemberForUnevenRoundAndSkipFinalRest(logger) {
    var a = WorkoutFixtures.reps("a",3,70); a["group"] = "pair";
    var b = WorkoutFixtures.reps("b",1,70); b["group"] = "pair";
    var m = WorkoutFixtures.fromEntries([a,b]);
    Test.assert(m.setDone(1000000l));
    Test.assert(m.setDone(1001000l));
    Test.assertEqual(m.active()["cur"],0); Test.assertEqual(m.restLeft(1001000l),70);
    Test.assert(m.queue("skipRest",{},1002000l));
    Test.assert(m.setDone(1003000l));
    Test.assertEqual(m.active()["cur"],0);
    Test.assertEqual(m.restLeft(1003000l),70); // Spent b does not hide the round boundary.
    Test.assert(m.queue("skipRest",{},1004000l));
    Test.assert(m.setDone(1005000l));
    Test.assert(m.active()["rest"] == null);
    return true;
}

(:test)
function closingUnitSkipsRestBeforeNextUnitsUnfinishedWarmup(logger) {
    var a = WorkoutFixtures.reps("a",1,70); a["group"] = "pair";
    var b = WorkoutFixtures.reps("b",1,70); b["group"] = "pair";
    var c = WorkoutFixtures.reps("ramp",2,25); c["sets"][0]["warmup"] = true;
    var m = WorkoutFixtures.fromEntries([a,b,c]);
    Test.assert(m.setDone(1000000l)); Test.assert(m.setDone(1001000l));
    Test.assert(m.active()["rest"] == null);
    var single = WorkoutFixtures.fromEntries([WorkoutFixtures.reps("single",1,70),c]);
    Test.assert(single.setDone(1000000l));
    Test.assert(single.active()["rest"] == null);
    // A completed warm-up in the next unit does not suppress the earned rest.
    c["sets"][0]["done"] = true;
    single = WorkoutFixtures.fromEntries([WorkoutFixtures.reps("single",1,70),c]);
    Test.assert(single.setDone(1000000l));
    Test.assertEqual(single.restLeft(1000000l),70);
    return true;
}

(:test)
function repeatedSupersetIdAcrossAnotherUnitDoesNotJoinGroups(logger) {
    var a = WorkoutFixtures.reps("a",1,45); a["group"] = "pair";
    var c = WorkoutFixtures.reps("c",1,90); c["group"] = "pair";
    var m = WorkoutFixtures.fromEntries([a,WorkoutFixtures.reps("single",1,30),c]);
    Test.assert(m.setDone(1000000l));
    Test.assertEqual(m.active()["cur"],0);
    Test.assertEqual(m.restLeft(1000000l),45);
    return true;
}

(:test)
function malformedRestPolicyAndMetadataDoNotReplaceSession(logger) {
    var m = WorkoutFixtures.model();
    var invalid = WorkoutFixtures.snapshot(2);
    invalid["state"]["active"]["entries"][0]["sets"][0]["restSec"] = -1;
    Test.assert(!m.snapshot(invalid,1000000l));
    invalid = WorkoutFixtures.snapshot(2);
    invalid["state"]["active"]["entries"][0]["sideRestSec"] = "15";
    Test.assert(!m.snapshot(invalid,1000000l));
    invalid = WorkoutFixtures.snapshot(2);
    invalid["state"]["active"]["entries"][0]["group"] = 1;
    Test.assert(!m.snapshot(invalid,1000000l));
    var fields = ["total","forIdx","forSet","kind"];
    var values = [86401,2,-1,"unknown"];
    for (var i=0;i<fields.size();i++) {
        invalid = WorkoutFixtures.snapshot(2);
        invalid["state"]["active"]["rest"] = {"endsAt"=>1060000l,"paused"=>false};
        invalid["state"]["active"]["rest"][fields[i]] = values[i];
        Test.assert(!m.snapshot(invalid,1000000l));
    }
    Test.assertEqual(m.data["seq"],1);
    Test.assertEqual(m.wid(),"workout-a");
    return true;
}

(:test)
function unsupportedShapesStayUnticked(logger) {
    var m = WorkoutFixtures.model();
    m.state["active"]["entries"][0]["sets"][0]["unsupported"] = true;
    Test.assert(!m.setDone(1000000l));
    Test.assertEqual(m.data["outbox"].size(),0);
    m.state["active"]["entries"][0]["mode"] = "distance";
    Test.assert(!m.setDone(1000000l));
    return true;
}

(:test)
function heartRateAggregateSurvivesRestart(logger) {
    var m = WorkoutFixtures.model();
    m.sample(100,1000000l); m.sample(120,1001000l);
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    m.sample(140,1002000l); m.setDone(1003000l);
    Test.assertEqual(m.batch()[0]["hr"]["avg"],120);
    Test.assertEqual(m.batch()[0]["hr"]["max"],140);
    Test.assertEqual(m.data["outbox"].size(),1);
    return true;
}

(:test)
function endedWorkoutTombstonePreventsResurrection(logger) {
    var m = WorkoutFixtures.model();
    Test.assert(m.queue("finish",{},1000000l));
    Test.assert(m.active() == null);
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    Test.assert(m.snapshot(WorkoutFixtures.snapshot(99),1001000l));
    Test.assert(m.active() == null);
    Test.assertEqual(m.batch()[0]["type"],"finish");
    return true;
}

(:test)
function oldWorkoutCommandsCannotAffectNewWorkout(logger) {
    var m = WorkoutFixtures.model(); m.setDone(1000000l);
    var newer = WorkoutFixtures.snapshot(4); newer["state"]["active"]["id"] = "workout-b";
    Test.assert(m.snapshot(newer,1001000l));
    Test.assert(!m.active()["entries"][0]["sets"][0]["done"]);
    Test.assertEqual(m.batch()[0]["wid"],"workout-a");
    return true;
}

(:test)
function malformedAndOversizedSnapshotsPreserveSession(logger) {
    var m = WorkoutFixtures.model();
    var invalid = WorkoutFixtures.snapshot(2); invalid["state"]["active"]["cur"] = 20;
    Test.assert(!m.snapshot(invalid,1001000l));
    Test.assertEqual(m.data["seq"],1);
    var large = WorkoutFixtures.snapshot(3); var text = "1234567890";
    for(var i=0;i<11;i++){ text += text; }
    large["state"]["extra"] = text;
    Test.assert(!m.snapshot(large,1001000l));
    Test.assertEqual(m.wid(),"workout-a");
    return true;
}

(:test)
function queueFullDoesNotDropOrExecuteCommand(logger) {
    var m = WorkoutFixtures.model();
    for (var i=0;i<m.MAX_EVENTS;i++) { Test.assert(m.queue("skipRest",{},1000000l+i)); }
    var first = m.batch()[0]["id"];
    Test.assert(!m.queue("finish",{},1001000l));
    Test.assert(m.active() != null);
    Test.assertEqual(m.data["outbox"].size(),m.MAX_EVENTS);
    Test.assertEqual(m.batch()[0]["id"],first);
    return true;
}

(:test)
class TestStorage {
    var values = {}; var failAfter = null; var writes = 0; var largest = 0;
    function initialize() {}
    function get(key) { return GymData.copy(values[key]); }
    function put(key,value) {
        if (failAfter != null && writes >= failAfter) { throw new GymError("Simulated power loss"); }
        writes += 1;
        largest = GymData.size(value,0)>largest ? GymData.size(value,0) : largest;
        values[key] = GymData.copy(value);
    }
    function remove(key) { values.remove(key); }
}

(:test)
function journalRebootAndInterruptedWriteKeepLastCommit(logger) {
    var storage = new TestStorage(); var store = new GymStore(storage);
    var m = WorkoutFixtures.model();
    for(var i=0;i<50;i++){ m.queue("skipRest",{},1000000l+i); }
    store.save(m.data);
    Test.assert(storage.largest < 8192);
    var restored = new WorkoutModel(new GymStore(storage).load(),"unused");
    Test.assertEqual(restored.data["outbox"].size(),50);
    m.next(1001000l);
    storage.failAfter = storage.writes+2;
    var failed = false;
    try { store.save(m.data); } catch(ex) { failed = true; }
    Test.assert(failed);
    restored = new WorkoutModel(new GymStore(storage).load(),"unused");
    Test.assertEqual(restored.data["outbox"].size(),50);
    Test.assertEqual(restored.active()["cur"],0);
    storage.failAfter = null; store.save(m.data);
    restored = new WorkoutModel(new GymStore(storage).load(),"unused");
    Test.assertEqual(restored.active()["cur"],1);
    return true;
}

(:test)
function recordingClaimsSurviveRestartWithoutLifetimeCutoff(logger) {
    var m = WorkoutFixtures.model();
    Test.assert(m.claimRecording("workout-a") != null);
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    Test.assert(m.claimRecording("workout-a") == null);
    for(var i=0;i<300;i++){ Test.assert(m.claimRecording("workout-"+i.toString()) != null); }
    Test.assertEqual(m.data["recordings"].size(),64);
    Test.assert(m.recordingClaim("workout-299") != null);
    Test.assert(m.claimRecording("workout-299") == null);
    return true;
}
