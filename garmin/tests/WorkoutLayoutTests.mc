import Toybox.Graphics;
import Toybox.System;
import Toybox.Test;

(:test)
function titleRowsUseNativeMeasurementsAndStayBetweenHeaderAndFields(logger) {
    var bitmap = Graphics.createBufferedBitmap({:width=>1,:height=>1}).get();
    var dc = bitmap.getDc();
    var settings = System.getDeviceSettings(); var w = settings.screenWidth; var h = settings.screenHeight;
    var layout = WorkoutLayout.metrics(dc,w,h);
    var tiny = dc.getFontHeight(Graphics.FONT_XTINY);
    logger.debug("Native layout "+w+"px: xtiny="+tiny+", value="+dc.getFontHeight(layout["valueFont"])+", title="+layout["titleTop"]+".."+layout["titleBottom"]+", fields="+layout["fieldTop"]+".."+layout["fieldBottom"]);
    Test.assert(layout["headerY"]+tiny < layout["titleTop"]);
    Test.assert(layout["titleBottom"] < layout["fieldTop"]);
    Test.assert(layout["labelY"]+tiny <= layout["valueY"]);
    Test.assert(layout["valueY"]+dc.getFontHeight(layout["valueFont"]) <= layout["detailY"]);
    Test.assert(layout["detailY"]+tiny < WorkoutControls.rect("primary",w,h)[1]);
    var names = ["Squat","Жим лёжа","Подъём гантелей через стороны стоя с паузой в верхней точке",
        "Very long exercise name with several words that should wrap and end with a visible ellipsis",
        "Сверхдлинноеназваниеупражнениябезпробеловдляпроверкипереноса",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ", "", "  Жим\nгантелей\tсидя  "];
    for (var i = 0; i < names.size(); i++) {
        var title = WorkoutLayout.title(dc,names[i],w,h,layout);
        Test.assert(title["rows"].size() >= 1 && title["rows"].size() <= 2);
        var lastBottom = layout["titleTop"];
        for (var j = 0; j < title["rows"].size(); j++) {
            var row = title["rows"][j]; var height = dc.getFontHeight(title["font"]);
            Test.assert(row[1] >= lastBottom);
            Test.assert(row[1]+height <= layout["titleBottom"]);
            Test.assert(dc.getTextWidthInPixels(row[0],title["font"]) <= row[2]);
            Test.assertEqual(row[2],WorkoutLayout.roundWidth(w,h,row[1],height));
            lastBottom = row[1]+height;
        }
        if (i == 2 || i == 3 || i == 5) {
            Test.assertEqual(title["rows"].size(),2);
            var last = title["rows"][1][0];
            Test.assert(last.substring(last.length()-1,last.length()).equals("…"));
        }
    }
    Test.assertEqual(WorkoutLayout.normalize("  Жим\nгантелей\tсидя  "),"Жим гантелей сидя");
    return true;
}

(:test)
class RenderFixture extends TouchFixtureApp {
    var heartRate = null;
    var heartRateZones = null;
    function initialize(w) { TouchFixtureApp.initialize(w); recordingStatus = "Recording FIT"; }
    function enableTouch() {}
}

(:test)
function nativeDashboardRendersLongNamesNoticesAlertsAndIdle(logger) {
    var settings = System.getDeviceSettings(); var w = settings.screenWidth; var h = settings.screenHeight;
    // Match the native display format: AMOLED fonts carry anti-aliasing masks.
    var bitmap = Graphics.createBufferedBitmap({:width=>w,:height=>h}).get();
    var dc = bitmap.getDc(); var app = new RenderFixture(w); var view = new WorkoutView(app);
    app.model.active()["entries"][0]["name"] = "Подъём гантелей через стороны стоя с паузой в верхней точке";
    view.onUpdate(dc);
    app.heartRateZones = [90,110,130,150,170,190]; app.heartRate = 142; view.onUpdate(dc);
    app.heartRate = 112; view.onUpdate(dc);
    var phases = ["1/10 L","10/10 R","1/10 Л","10/10 П"];
    for (var i=0; i<phases.size(); i++) {
        var phase = view.phaseLabel(dc,phases[i],true);
        Test.assert(phase.find(phases[i]) != null);
        Test.assert(dc.getTextWidthInPixels(phase,view.smallFont) <= w*0.29);
    }
    Test.assertEqual(app.viewWidth,w); Test.assertEqual(app.viewHeight,h);
    Test.assert(app.model.startSet(app.now())); view.onUpdate(dc);
    Test.assert(app.model.setDone(app.now()+2000)); view.onUpdate(dc);
    Test.assert(app.model.pause(app.now()+2000)); view.onUpdate(dc);
    app.notice = "Storage recovery failed. Keep app data."; view.onUpdate(dc);
    app.notice = null;
    app.timerAlert = {"kind"=>"rest"}; view.onUpdate(dc);
    app.timerAlert = {"kind"=>"timed"}; view.onUpdate(dc);
    app.timerAlert = null;
    var idle = WorkoutFixtures.snapshot(2); idle["state"]["active"] = null;
    Test.assert(app.model.snapshot(idle,app.now())); view.onUpdate(dc);
    return true;
}

(:test)
function resourceLanguageMatchesNativeWatchLocaleAndDiagnosticsUseResources(logger) {
    var russian = System.getDeviceSettings().systemLanguage == System.LANGUAGE_RUS;
    var label = GymUi.string(Rez.Strings.StartSet);
    Test.assertEqual(label,russian ? "Начать подход" : "Start set");
    Test.assertEqual(GymUi.message("Storage full. Reconnect phone."),GymUi.string(Rez.Strings.StorageFull));
    Test.assertEqual(GymUi.message("Recording interrupted"),GymUi.string(Rez.Strings.RecordingInterrupted));
    Test.assertEqual(GymUi.message("Unsupported set. Use phone."),GymUi.string(Rez.Strings.UnsupportedSet));
    Test.assertEqual(GymUi.message("Unknown diagnostic"),"Unknown diagnostic");
    Test.assertEqual(GymUi.side("L"),russian ? "Л" : "L");
    Test.assertEqual(GymUi.unit("kg"),russian ? "кг" : "kg");
    logger.debug("Resource language "+System.getDeviceSettings().systemLanguage+": "+label);
    return true;
}

(:test)
class PhoneStatusFixture extends OpenGymApp {
    var durable = true;
    var at = 1000000l;
    var sent;
    function initialize() { model = WorkoutFixtures.model(); sent = []; }
    function now() { return at; }
    function send(payload) { sent.add(payload); return true; }
    function persist() { return durable; }
    function reconcileRecording() {}
    function updateAlerts(at) {}
}

(:test)
function helloReportsOnlyAppliedStateAndKeepsExistingProtocol(logger) {
    var app = new PhoneStatusFixture();
    var hello = app.hello();
    Test.assertEqual(hello["v"],1); Test.assertEqual(hello["kind"],"hello");
    Test.assertEqual(hello["seq"],1); Test.assertEqual(hello["wid"],"workout-a"); Test.assertEqual(hello["pending"],0);
    Test.assert(app.model.startSet(app.now())); Test.assert(app.model.setDone(app.now()+2000));
    Test.assertEqual(app.hello()["pending"],1);
    app.lastHelloAt = 900000l;
    app.receive(WorkoutFixtures.snapshot(2));
    Test.assertEqual(app.lastHelloAt,0l); Test.assertEqual(app.hello()["seq"],2);
    app.lastHelloAt = 900000l;
    app.receive(WorkoutFixtures.snapshot(2)); Test.assertEqual(app.lastHelloAt,900000l);
    app.durable = false;
    app.receive(WorkoutFixtures.snapshot(3));
    Test.assertEqual(app.lastHelloAt,900000l); Test.assertEqual(app.hello()["seq"],2);
    app.durable = true;
    var state = WorkoutFixtures.snapshot(3); state["state"]["active"] = null;
    var ack = {"v"=>1,"kind"=>"ack","seq"=>3,"state"=>state["state"],"ids"=>[app.model.batch()[0]["id"]]};
    app.receive(ack);
    Test.assertEqual(app.lastHelloAt,0l); Test.assertEqual(app.hello()["seq"],3);
    Test.assert(app.hello()["wid"] == null); Test.assertEqual(app.hello()["pending"],0);
    app.tick();
    Test.assertEqual(app.sent.size(),1); Test.assertEqual(app.sent[0]["kind"],"hello");
    var sentAt = app.lastHelloAt;
    // The phone retains this ACK and replays it after every hello, even idle.
    app.receive(ack);
    Test.assertEqual(app.lastHelloAt,sentAt);
    app.at += 1000l; app.tick();
    Test.assertEqual(app.sent.size(),1);
    app.at += 29000l; app.tick();
    Test.assertEqual(app.sent.size(),2); Test.assertEqual(app.sent[1]["kind"],"hello");
    return true;
}

(:test)
function nativeHeaderQueueAndInactiveTimerHintFitEnglishAndRussian(logger) {
    var bitmap = Graphics.createBufferedBitmap({:width=>1,:height=>1}).get();
    var dc = bitmap.getDc(); var settings = System.getDeviceSettings();
    var w = settings.screenWidth; var h = settings.screenHeight;
    var layout = WorkoutLayout.metrics(dc,w,h); var font = Graphics.FONT_XTINY;
    var headerWidth = WorkoutLayout.roundWidth(w,h,layout["headerY"],dc.getFontHeight(font));
    var languages = [["HR","HR","tap Start"],["Пульс","ЧСС","начните"]];
    var values = ["--",WorkoutControls.decimal(25),WorkoutControls.decimal(188),WorkoutControls.decimal(250)];
    for (var i = 0; i < languages.size(); i++) {
        var language = languages[i];
        for (var j = 0; j < values.size(); j++) {
            var label = WorkoutLayout.header(dc,language[0],language[1],values[j],96,headerWidth);
            var measured = dc.getTextWidthInPixels(label,font);
            logger.debug("Header "+w+"px: "+label+" = "+measured+" / "+headerWidth);
            Test.assert(measured <= headerWidth);
            Test.assert(label.find(values[j]) != null && label.find("+96") != null);
            Test.assert(WorkoutLayout.ellipsis(dc,label,font,headerWidth).equals(label));
        }
        var hintWidth = w*0.40;
        var chord = WorkoutLayout.roundWidth(w,h,layout["detailY"],dc.getFontHeight(font));
        if (chord < hintWidth) { hintWidth = chord; }
        Test.assert(dc.getTextWidthInPixels(language[2],font) <= hintWidth);
        Test.assert(WorkoutLayout.ellipsis(dc,language[2],font,hintWidth).equals(language[2]));
    }
    var russian = settings.systemLanguage == System.LANGUAGE_RUS;
    Test.assertEqual(GymUi.string(Rez.Strings.TapStart),russian ? "начните" : "tap Start");
    return true;
}
