import Toybox.Test;
import Toybox.WatchUi;
import Toybox.Lang;

(:test)
function cardioAcknowledgementKeepsTheNextIntervalTimer(logger) {
    var snap = WorkoutFixtures.snapshot(1);
    snap["state"]["active"]["entries"] = [{"id"=>"run", "name"=>"Run", "mode"=>"cardio", "sets"=>[
        {"sec"=>30,"done"=>false}, {"sec"=>30,"done"=>false}]}];
    var m = new WorkoutModel(null,"cardio-ack"); Test.assert(m.snapshot(snap,1000000l));
    Test.assert(m.startSet(1000000l)); Test.assert(m.setDone(1031000l));
    var doneId = m.batch()[0]["id"];
    Test.assert(m.queue("skipRest",{},1031000l)); var skipId = m.batch()[1]["id"];
    Test.assert(m.startSet(1032000l));
    snap["seq"] = 2;
    snap["state"]["active"]["entries"][0]["sets"][0] = {"sec"=>31,"done"=>true};
    Test.assert(m.acknowledge({"v"=>1,"kind"=>"ack","seq"=>2,"state"=>snap["state"],"ids"=>[doneId,skipId]},1037000l));
    Test.assertEqual(m.elapsed(1038000l),6);
    Test.assertEqual(m.batch().size(),0);
    return true;
}

(:test)
function cardioTimerMeasuresActiveTimeAcrossPauseRestartAndPhoneSnapshots(logger) {
    var snap = WorkoutFixtures.snapshot(1);
    snap["state"]["active"]["entries"] = [{"id"=>"run", "name"=>"Run", "mode"=>"cardio", "sets"=>[{"sec"=>30,"done"=>false}]}];
    var m = new WorkoutModel(null,"cardio"); Test.assert(m.snapshot(snap,1000000l));
    Test.assertEqual(WorkoutControls.primary(m,1000000l),"startSet");
    m.sample(99,1000000l); Test.assert(m.data["hr"] == null);
    // The physical START shortcut starts cardio too, without completing a row.
    Test.assert(m.setDone(1000000l)); Test.assertEqual(m.batch().size(),0);
    Test.assert(!m.setDone(1000000l));
    m.sample(140,1010000l);
    Test.assert(m.pause(1010000l)); Test.assertEqual(m.elapsed(1040000l),10);
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    snap["seq"] = 2; Test.assert(m.snapshot(snap,1040000l));
    Test.assertEqual(m.elapsed(1040000l),10);
    Test.assert(m.pause(1040000l)); Test.assertEqual(m.elapsed(1045000l),15);
    Test.assertEqual(WorkoutControls.primary(m,1045000l),"setDone");
    var alerts = new WorkoutAlerts();
    Test.assert(alerts.poll(m,1059000l) == null);
    Test.assert(alerts.poll(m,1060000l) != null);
    Test.assert(alerts.poll(m,1061000l) == null);
    Test.assert(!m.current()["row"]["done"]);
    m.sample(160,1061000l); Test.assert(m.setDone(1061000l));
    var event = m.batch()[2];
    Test.assertEqual(event["sec"],31); Test.assert(event["r"] == null); Test.assert(event["w"] == null);
    Test.assertEqual(event["hr"]["avg"],150);
    Test.assert(m.active()["entries"][0]["sets"][0]["done"]);
    return true;
}

(:test)
function cardioWithoutTargetRunsStopwatchWithoutTargetAlert(logger) {
    var m = WorkoutFixtures.model(); m.current()["entry"]["mode"] = "cardio";
    Test.assert(m.startSet(1000000l));
    var alerts = new WorkoutAlerts(); Test.assert(alerts.poll(m,1100000l) == null);
    Test.assert(m.setDone(1100000l)); Test.assertEqual(m.batch()[0]["sec"],100);
    return true;
}

(:test)
function prescriptionsPrioritizeRepsAndTimedTargetsOverEmptyLoad(logger) {
    var m = WorkoutFixtures.model(); var c = m.current();
    c["entry"]["bodyweight"] = true; c["row"]["w"] = 0;
    var p = WorkoutControls.prescription(c,"kg");
    Test.assertEqual(p["value"],"5 "+GymUi.string(Rez.Strings.Reps));
    Test.assertEqual(p["detail"],GymUi.string(Rez.Strings.Bodyweight));
    c["row"]["w"] = 7.5; p = WorkoutControls.prescription(c,"kg");
    Test.assertEqual(p["detail"],"+7.5 kg");
    c["entry"]["mode"] = "cardio"; c["row"]["sec"] = 750;
    p = WorkoutControls.prescription(c,"kg"); Test.assertEqual(p["value"],"12:30");
    Test.assertEqual(p["detail"],GymUi.string(Rez.Strings.Target));
    c["entry"]["goalKm"] = 5; p = WorkoutControls.prescription(c,"kg");
    Test.assertEqual(p["detail"],GymUi.string(Rez.Strings.Target)+" 5 "+GymUi.string(Rez.Strings.Kilometers));
    c["row"]["sec"] = null; p = WorkoutControls.prescription(c,"kg");
    Test.assertEqual(p["value"],"5 "+GymUi.string(Rez.Strings.Kilometers));
    c["entry"]["mode"] = "time"; c["entry"]["goalKm"] = null;
    c["row"]["sec"] = 45; c["row"]["w"] = 20; p = WorkoutControls.prescription(c,"kg");
    Test.assertEqual(p["value"],"00:45");
    Test.assertEqual(p["detail"],GymUi.string(Rez.Strings.Target)+" · 20 kg");
    return true;
}

(:test)
function repsStartMeasuresOnlyExplicitSetAndKeepsPhonePayload(logger) {
    var m = WorkoutFixtures.model();
    Test.assertEqual(m.elapsed(1005000l),0);
    Test.assert(m.startSet(1005000l));
    Test.assert(!m.startSet(1006000l));
    Test.assertEqual(m.elapsed(1010000l),5);
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    Test.assert(m.snapshot(WorkoutFixtures.snapshot(2),1010000l));
    Test.assertEqual(m.elapsed(1011000l),6);
    Test.assert(m.pause(1011000l));
    Test.assertEqual(m.elapsed(1020000l),6);
    Test.assert(m.pause(1020000l));
    Test.assertEqual(m.elapsed(1021000l),7);
    Test.assert(m.setDone(1021000l));
    var event = m.batch()[2];
    Test.assertEqual(event["type"],"setDone");
    Test.assertEqual(event["r"],5);
    Test.assert(event["sec"] == null);
    Test.assert(m.data["timing"] == null);
    return true;
}

(:test)
function setStartRefusesPausedRestAndUnsupportedAndClearsOnIdentityChange(logger) {
    var m = WorkoutFixtures.model();
    Test.assert(m.pause(1000000l)); Test.assert(!m.startSet(1001000l));
    Test.assert(m.pause(1001000l)); Test.assert(m.setDone(1002000l));
    Test.assert(!m.startSet(1003000l)); Test.assert(m.queue("skipRest",{},1003000l));
    m.current()["row"]["unsupported"] = true; Test.assert(!m.startSet(1004000l));
    m.current()["row"]["unsupported"] = false; Test.assert(m.startSet(1005000l));
    var fresh = WorkoutFixtures.snapshot(9); fresh["state"]["active"]["cur"] = 1;
    Test.assert(m.snapshot(fresh,1006000l));
    Test.assert(m.data["timing"] == null);
    return true;
}

(:test)
function restAlertExpiresOnceAndSurvivesReconciliationAndPause(logger) {
    var m = WorkoutFixtures.model(); var alerts = new WorkoutAlerts();
    Test.assert(m.setDone(1000000l));
    Test.assert(alerts.poll(m,1059000l) == null);
    Test.assert(m.pause(1059000l)); Test.assert(alerts.poll(m,1060000l) == null);
    Test.assert(alerts.poll(m,1090000l) == null);
    Test.assert(m.pause(1090000l)); Test.assert(alerts.poll(m,1090000l) == null);
    var alert = alerts.poll(m,1091000l);
    Test.assertEqual(alert["kind"],"rest");
    Test.assert(alerts.valid(alert,m));
    Test.assert(alerts.poll(m,1092000l) == null);
    Test.assert(m.snapshot(WorkoutFixtures.snapshot(2),1093000l));
    Test.assert(alerts.poll(m,1093000l) == null);
    Test.assertEqual(m.data["outbox"].size(),3);
    Test.assert(!m.current()["row"]["done"]);
    return true;
}

(:test)
function skippedOrOldRestDoesNotAlertAndNewRestRearms(logger) {
    var m = WorkoutFixtures.model(); var alerts = new WorkoutAlerts();
    Test.assert(m.setDone(1000000l));
    Test.assert(alerts.poll(m,1000000l) == null);
    Test.assert(m.queue("skipRest",{},1001000l));
    Test.assert(alerts.poll(m,1060000l) == null);
    Test.assert(m.setDone(1061000l));
    Test.assert(alerts.poll(m,1061000l) == null);
    Test.assert(alerts.poll(m,1121000l) != null);
    Test.assert(alerts.poll(m,1122000l) == null);
    var restarted = new WorkoutAlerts();
    Test.assert(restarted.poll(m,1122000l) == null);
    return true;
}

(:test)
function restWithoutMetadataIsSafeAndRunningReplacementRearms(logger) {
    var m = WorkoutFixtures.model(); var alerts = new WorkoutAlerts();
    m.active()["rest"] = {"endsAt"=>1001000l};
    Test.assert(alerts.poll(m,1000000l) == null);
    Test.assert(alerts.poll(m,1001000l) != null);
    m.active()["rest"] = {"endsAt"=>1004000l};
    Test.assert(alerts.poll(m,1002000l) == null);
    Test.assert(alerts.poll(m,1004000l) != null);
    m.active()["rest"] = {"endsAt"=>1005000l,"forIdx"=>0,"forSet"=>79};
    Test.assert(alerts.poll(m,1004000l) == null);
    Test.assert(alerts.poll(m,1005000l) != null);
    return true;
}

(:test)
function timedTargetAlertsOnceWithoutCompletingAndFreezesOnPause(logger) {
    var m = WorkoutFixtures.model(); var alerts = new WorkoutAlerts();
    Test.assert(m.next(1000000l)); Test.assert(m.startTimed(1000000l));
    Test.assert(alerts.poll(m,1029000l) == null);
    Test.assert(m.pause(1029000l)); Test.assert(alerts.poll(m,1050000l) == null);
    Test.assert(m.pause(1050000l));
    var alert = alerts.poll(m,1051000l);
    Test.assertEqual(alert["kind"],"timed");
    Test.assert(alerts.poll(m,1052000l) == null);
    var snap = WorkoutFixtures.snapshot(4); snap["state"]["active"]["cur"] = 1;
    Test.assert(m.snapshot(snap,1053000l));
    Test.assert(alerts.poll(m,1053000l) == null);
    Test.assert(alerts.valid(alert,m));
    Test.assert(!m.current()["row"]["done"]);
    Test.assertEqual(m.elapsed(1054000l),33);
    Test.assert(m.setDone(1054000l));
    Test.assert(!alerts.valid(alert,m));
    Test.assertEqual(m.batch()[3]["sec"],33);
    return true;
}

(:test)
function repsElapsedHasNoTargetAlertAndNewWorkoutInvalidatesAlert(logger) {
    var m = WorkoutFixtures.model(); var alerts = new WorkoutAlerts();
    Test.assert(m.startSet(1000000l));
    Test.assert(alerts.poll(m,1100000l) == null);
    Test.assert(m.setDone(1100000l)); Test.assert(alerts.poll(m,1100000l) == null);
    var alert = alerts.poll(m,1160000l); Test.assert(alert != null);
    var snap = WorkoutFixtures.snapshot(2); snap["state"]["active"]["id"] = "new-workout";
    Test.assert(m.snapshot(snap,1161000l));
    Test.assert(!alerts.valid(alert,m));
    return true;
}

(:test)
class TouchFixtureApp {
    var model; var notice = null; var timerAlert = null;
    var viewWidth; var viewHeight; var calls = []; var at = 1000000l;
    var recordingStatus = "Test"; var lastHelloAt = 1l; var ticks = 0;
    function initialize(w) { model = WorkoutFixtures.model(); viewWidth = w; viewHeight = w; }
    function now() { return at; }
    function tick() { ticks += 1; }
    function action(command) {
        calls.add(command);
        if (command.equals("startSet")) { return model.startSet(at); }
        if (command.equals("setDone")) { return model.setDone(at); }
        return true;
    }
}

(:test)
class MenuFixture extends WorkoutMenu {
    var confirmations = [];
    function initialize(app) { WorkoutMenu.initialize(app); }
    function closeMenu() {}
    function confirm(command) { confirmations.add({"command"=>command,"wid"=>workout}); }
}
(:test)
class ConfirmFixture extends WorkoutConfirm {
    var exits = 0;
    function initialize(app,command,wid) { WorkoutConfirm.initialize(app,command,wid); }
    function exitApp() { exits += 1; }
}

(:test)
function staleMenuCannotControlReplacementWorkoutOrBindItsConfirmation(logger) {
    var commands = ["pause","next","skipRest","finish","discard","exit"];
    for (var i=0;i<commands.size();i++) {
        var app = new TouchFixtureApp(280); var menu = new MenuFixture(app);
        var idle = WorkoutFixtures.snapshot(2); idle["state"]["active"] = null;
        Test.assert(app.model.snapshot(idle,1001000l));
        var fresh = WorkoutFixtures.snapshot(3); fresh["state"]["active"]["id"] = "workout-b";
        Test.assert(app.model.snapshot(fresh,1002000l));
        menu.onSelect(new WatchUi.MenuItem(commands[i],null,commands[i],{}));
        Test.assertEqual(app.calls.size(),0); Test.assertEqual(menu.confirmations.size(),0);
        Test.assertEqual(app.model.wid(),"workout-b");
        Test.assertEqual(app.model.data["outbox"].size(),0);
    }
    return true;
}

(:test)
function menuKeepsCurrentActionsAndNonWorkoutActionsAvailable(logger) {
    var app = new TouchFixtureApp(280); var menu = new MenuFixture(app);
    menu.onSelect(new WatchUi.MenuItem("Pause",null,"pause",{})); Test.assertEqual(app.calls[0],"pause");
    menu.onSelect(new WatchUi.MenuItem("Finish",null,"finish",{}));
    Test.assertEqual(menu.confirmations[0]["wid"],"workout-a");
    var fresh = WorkoutFixtures.snapshot(2); fresh["state"]["active"]["id"] = "workout-b";
    Test.assert(app.model.snapshot(fresh,1001000l));
    menu.onSelect(new WatchUi.MenuItem("Status",null,"status",{})); Test.assert(app.notice != null);
    menu.onSelect(new WatchUi.MenuItem("Reconnect",null,"reconnect",{})); Test.assertEqual(app.ticks,1);
    return true;
}

(:test)
function staleFinishDiscardAndExitConfirmationsCannotAffectReplacement(logger) {
    var commands = ["finish","discard","exit"];
    for (var i=0;i<commands.size();i++) {
        var app = new TouchFixtureApp(280);
        var confirm = new ConfirmFixture(app,commands[i],app.model.wid());
        var fresh = WorkoutFixtures.snapshot(2); fresh["state"]["active"]["id"] = "workout-b";
        Test.assert(app.model.snapshot(fresh,1001000l));
        Test.assert(confirm.onResponse(WatchUi.CONFIRM_YES));
        Test.assertEqual(app.calls.size(),0); Test.assertEqual(confirm.exits,0);
    }
    var idleApp = new TouchFixtureApp(280); var idle = WorkoutFixtures.snapshot(2); idle["state"]["active"] = null;
    Test.assert(idleApp.model.snapshot(idle,1001000l));
    var exit = new ConfirmFixture(idleApp,"exit",null);
    Test.assert(exit.onResponse(WatchUi.CONFIRM_YES)); Test.assertEqual(exit.exits,1);
    return true;
}

(:test)
function exerciseReplacementAtSameIndicesClearsElapsedHeartRateAndTargetAlert(logger) {
    var m = WorkoutFixtures.model(); var alerts = new WorkoutAlerts();
    Test.assert(m.startSet(1000000l)); m.sample(90,1001000l);
    Test.assert(alerts.poll(m,1031000l) == null);
    var fresh = WorkoutFixtures.snapshot(2);
    fresh["state"]["active"]["entries"] = [fresh["state"]["active"]["entries"][1]];
    Test.assert(m.snapshot(fresh,1031000l));
    Test.assert(m.data["timing"] == null); Test.assert(m.data["hr"] == null);
    Test.assertEqual(m.elapsed(1032000l),0);
    Test.assertEqual(WorkoutControls.primary(m,1032000l),"startSet");
    Test.assert(alerts.poll(m,1032000l) == null);
    Test.assert(m.setDone(1032000l)); Test.assert(!m.current()["row"]["done"]);
    Test.assert(m.setDone(1034000l)); Test.assertEqual(m.batch()[0]["sec"],2);
    return true;
}

(:test)
function sameIndexRowShiftAndDuplicateExerciseRemovalClearLocalMeasurement(logger) {
    var m = WorkoutFixtures.model(); Test.assert(m.startSet(1000000l)); m.sample(90,1001000l);
    var fresh = WorkoutFixtures.snapshot(2);
    fresh["state"]["active"]["entries"][0]["sets"] = fresh["state"]["active"]["entries"][0]["sets"].slice(1,null);
    Test.assert(m.snapshot(fresh,1002000l));
    Test.assert(m.data["timing"] == null); Test.assert(m.data["hr"] == null);
    m = WorkoutFixtures.model(); Test.assert(m.startSet(1000000l));
    fresh = WorkoutFixtures.snapshot(2);
    fresh["state"]["active"]["entries"].add(GymData.copy(fresh["state"]["active"]["entries"][0]));
    Test.assert(m.snapshot(fresh,1002000l)); Test.assert(m.data["timing"] == null);
    return true;
}

(:test)
function ackReplayRemovalClearsAnotherExercisesTimingHrAndAlert(logger) {
    for (var kind=0;kind<3;kind++) {
        var seed = WorkoutFixtures.snapshot(1);
        seed["state"]["active"]["entries"][0] = {"id"=>"hold-a","name"=>"Hold A","mode"=>"time","sets"=>[{"sec"=>30,"done"=>false}]};
        var m = new WorkoutModel(null,"ack-timer-test");
        Test.assert(m.snapshot(seed,1000000l)); Test.assert(m.next(1000000l));
        var eventId = m.batch()[0]["id"];
        Test.assert(m.startSet(1001000l)); m.sample(90,1002000l);
        var alerts = new WorkoutAlerts(); var oldAlert = alerts.poll(m,1032000l);
        Test.assert(oldAlert != null);
        var post = GymData.copy(seed); post["seq"] = kind == 0 ? 2 : 1;
        if (kind == 2) {
            var newer = GymData.copy(seed); newer["seq"] = 5;
            Test.assert(m.snapshot(newer,1032000l));
            post["seq"] = 4; post["state"]["active"]["cur"] = 1;
        }
        Test.assert(m.acknowledge({"v"=>1,"kind"=>"ack","seq"=>post["seq"],"state"=>post["state"],"ids"=>[eventId]},1033000l));
        Test.assertEqual(m.current()["exId"],"hold-a");
        Test.assert(m.data["timing"] == null); Test.assert(m.data["hr"] == null);
        Test.assert(!alerts.valid(oldAlert,m)); Test.assert(alerts.poll(m,1034000l) == null);
        Test.assertEqual(m.elapsed(1034000l),0); Test.assertEqual(WorkoutControls.primary(m,1034000l),"startSet");
        Test.assert(m.setDone(1034000l)); Test.assert(!m.current()["row"]["done"]);
        Test.assert(m.setDone(1036000l));
        Test.assertEqual(m.batch()[0]["sec"],2); Test.assert(m.batch()[0]["hr"] == null);
    }
    return true;
}

(:test)
function unchangedAckTargetKeepsElapsedAndHeartRateThroughRestart(logger) {
    var m = WorkoutFixtures.model(); Test.assert(m.next(1000000l));
    var eventId = m.batch()[0]["id"];
    Test.assert(m.startSet(1001000l)); m.sample(100,1002000l);
    var post = WorkoutFixtures.snapshot(2); post["state"]["active"]["cur"] = 1;
    Test.assert(m.acknowledge({"v"=>1,"kind"=>"ack","seq"=>2,"state"=>post["state"],"ids"=>[eventId]},1006000l));
    Test.assertEqual(m.elapsed(1006000l),5); Test.assert(m.data["hr"] != null);
    m = new WorkoutModel(GymData.copy(m.data),"unused");
    Test.assert(m.setDone(1008000l));
    Test.assertEqual(m.batch()[0]["sec"],7); Test.assertEqual(m.batch()[0]["hr"]["avg"],100);
    return true;
}
(:test)
class TouchFixtureDelegate extends WorkoutDelegate {
    var menus = 0; var finishes = 0;
    function initialize(app) { WorkoutDelegate.initialize(app); }
    function onMenu() { menus += 1; return true; }
    function confirmFinish() { finishes += 1; }
}

(:test)
function touchUsesDrawnBoundsForBothDevicesAndIgnoresBackground(logger) {
    var sizes = [280,454];
    for (var i=0;i<sizes.size();i++) {
        var w = sizes[i]; var r = WorkoutControls.rect("primary",w,w);
        var x = r[0]+r[2]/2; var y = r[1]+r[3]/2;
        Test.assertEqual(WorkoutControls.hit(w,w,x,y,true,false),"primary");
        Test.assert(WorkoutControls.hit(w,w,r[0],r[1],true,false) == null);
        Test.assert(WorkoutControls.hit(w,w,r[0]+r[2],y,true,false) == null);
        Test.assert(WorkoutControls.hit(w,w,x,r[1]+r[3],true,false) == null);
        Test.assert(WorkoutControls.hit(w,w,w/2,w/2,true,false) == null);
        Test.assert(WorkoutControls.hit(w,w,x,y,false,false) == null);
        Test.assertEqual(WorkoutControls.hit(w,w,x,y,false,true),"dismiss");
        Test.assert(WorkoutControls.rect("next",w,w) == null);
        Test.assert(WorkoutControls.rect("menu",w,w) == null);
        Test.assert(WorkoutControls.hit(w,w,(w*0.82).toNumber(),(w*0.82).toNumber(),true,false) == null);
    }
    Test.assertEqual(WorkoutControls.clock(65),"01:05"); Test.assertEqual(WorkoutControls.clock(0),"00:00");
    return true;
}

(:test)
function decimalLabelsRemoveFloatNoiseWithoutChangingStoredValues(logger) {
    var values = [7.5,7.5.toDouble(),7,7l,0,0.0,7.25,7.75,7.5000001,16.5346696635.toDouble(),9999.999.toDouble(),-0.001];
    var expected = ["7.5","7.5","7","7","0","0","7.25","7.75","7.5","16.53","10000","0"];
    for (var i=0;i<values.size();i++) { Test.assertEqual(WorkoutControls.decimal(values[i]),expected[i]); }
    var model = WorkoutFixtures.model();
    var row = model.current()["row"];
    row["w"] = 16.5346696635.toDouble();
    var original = row["w"];
    Test.assertEqual(WorkoutControls.decimal(row["w"]),"16.53");
    Test.assertEqual(row["w"],original);
    Test.assertEqual(WorkoutControls.decimal(12.0),"12");
    Test.assertEqual(WorkoutControls.clock(65.9),"01:05");
    return true;
}

(:test)
function allButtonCornersFitRoundScreenWithAnInset(logger) {
    var sizes = [280,454]; var ids = ["primary"];
    for (var i=0;i<sizes.size();i++) {
        var w = sizes[i]; var center = w/2.0; var radius = w*0.48;
        for (var j=0;j<ids.size();j++) {
            var r = WorkoutControls.rect(ids[j],w,w);
            for (var x=0;x<2;x++) {
                for (var y=0;y<2;y++) {
                    var dx = r[0]+x*r[2]-center; var dy = r[1]+y*r[3]-center;
                    Test.assert(dx*dx+dy*dy <= radius*radius);
                }
            }
        }
    }
    return true;
}

(:test)
function actualTouchDelegateStartsCompletesDismissesAndKeepsConfirmation(logger) {
    var app = new TouchFixtureApp(280); var delegate = new TouchFixtureDelegate(app);
    var p = WorkoutControls.rect("primary",280,280); var x = p[0]+p[2]/2; var y = p[1]+p[3]/2;
    Test.assert(delegate.tapAt(x,y)); Test.assertEqual(app.calls[0],"startSet");
    app.at += 5000l;
    Test.assert(delegate.tapAt(x,y)); Test.assertEqual(app.calls[1],"setDone");
    Test.assertEqual(app.model.restLeft(app.at),60);
    app.timerAlert = {"kind"=>"rest"}; var count = app.calls.size();
    Test.assert(delegate.tapAt(x,y)); Test.assert(app.timerAlert == null); Test.assertEqual(app.calls.size(),count);
    app.notice = "Test notice";
    Test.assert(delegate.onSelect()); Test.assert(app.notice == null); Test.assertEqual(app.calls.size(),count);
    Test.assert(delegate.tapAt(x,y)); Test.assertEqual(app.calls[count],"skipRest");
    Test.assert(delegate.onNextPage()); Test.assertEqual(delegate.menus,0);
    Test.assertEqual(app.calls[app.calls.size()-1],"next");
    Test.assert(!delegate.tapAt(140,140));
    app.model.active()["cur"] = 1; app.model.active()["rest"] = null;
    app.model.current()["row"]["done"] = true;
    Test.assert(delegate.tapAt(x,y)); Test.assertEqual(delegate.finishes,1);
    Test.assert(app.model.active() != null);
    return true;
}

(:test)
function physicalStartMatchesVisiblePrimaryAndNavigationRemainsAvailable(logger) {
    var app = new TouchFixtureApp(280); var delegate = new TouchFixtureDelegate(app);
    Test.assert(delegate.keyAction(WatchUi.KEY_ENTER));
    Test.assertEqual(app.calls[0],"startSet");
    Test.assert(!app.model.active()["entries"][0]["sets"][0]["done"]);
    app.at += 2000l; Test.assert(delegate.keyAction(WatchUi.KEY_ENTER));
    Test.assertEqual(app.calls[1],"setDone");
    Test.assert(app.model.active()["entries"][0]["sets"][0]["done"]);
    Test.assert(delegate.keyAction(WatchUi.KEY_DOWN)); Test.assertEqual(app.calls[2],"next");
    Test.assert(delegate.keyAction(WatchUi.KEY_MENU)); Test.assertEqual(delegate.menus,1);
    Test.assert(delegate.keyAction(WatchUi.KEY_ESC)); Test.assertEqual(delegate.menus,2);
    Test.assert(!delegate.keyAction(WatchUi.KEY_UP));
    return true;
}

(:test)
function changedTimerTargetAndRestDeadlineInvalidateOldAlerts(logger) {
    var m = WorkoutFixtures.model(); var alerts = new WorkoutAlerts();
    Test.assert(m.next(1000000l)); Test.assert(m.startSet(1000000l));
    var old = alerts.poll(m,1030000l); Test.assert(old != null);
    m.current()["row"]["sec"] = 40;
    Test.assert(!alerts.valid(old,m)); Test.assert(alerts.poll(m,1035000l) == null);
    Test.assert(alerts.poll(m,1040000l) != null);
    m = WorkoutFixtures.model(); alerts = new WorkoutAlerts();
    Test.assert(m.setDone(1000000l)); Test.assert(alerts.poll(m,1000000l) == null);
    old = alerts.poll(m,1060000l); Test.assert(old != null);
    m.active()["rest"]["endsAt"] = 1070000l;
    Test.assert(!alerts.valid(old,m)); Test.assert(alerts.poll(m,1060000l) == null);
    Test.assert(alerts.poll(m,1070000l) != null);
    return true;
}
