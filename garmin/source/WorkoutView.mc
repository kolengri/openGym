import Toybox.Graphics;
import Toybox.WatchUi;
import Toybox.Lang;
import Toybox.System;

class WorkoutView extends WatchUi.View {
    var app;
    function initialize(owner) { View.initialize(); app = owner; }
    function line(dc, y, text, font, color) {
        dc.setColor(color, Graphics.COLOR_TRANSPARENT);
        dc.drawText(dc.getWidth()/2, y, font, text, Graphics.TEXT_JUSTIFY_CENTER);
    }
    function trim(dc, text, width) {
        if (!(text instanceof String)) { return ""; }
        while (text.length() > 1 && dc.getTextWidthInPixels(text, Graphics.FONT_SMALL) > width) { text = text.substring(0, text.length()-1); }
        return text;
    }
    function onUpdate(dc) {
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_BLACK); dc.clear();
        var h = dc.getHeight(); var w = dc.getWidth();
        var tiny = Graphics.FONT_XTINY;
        var rowH = dc.getFontHeight(tiny);
        var top = (h * 0.10).toNumber();
        var model = app.model; var a = model.active();
        var color = Graphics.COLOR_GREEN;
        if (app.notice != null) {
            line(dc, top, "openGym", Graphics.FONT_SMALL, color);
            // Bounded lines fit both 454px AMOLED and 280px MIP screens.
            var msg = app.notice;
            var split = msg.find(". ");
            line(dc, h*0.38, trim(dc, split == null ? msg : msg.substring(0,split), w*0.85), tiny, Graphics.COLOR_YELLOW);
            if (split != null) { line(dc, h*0.50, trim(dc,msg.substring(split+2,msg.length()),w*0.82),tiny,Graphics.COLOR_WHITE); }
            line(dc, h*0.72, "BACK to return", tiny, Graphics.COLOR_LT_GRAY);
            return;
        }
        if (a == null) {
            line(dc, top, "openGym", Graphics.FONT_SMALL, color);
            line(dc,h*0.37,"Start on phone",Graphics.FONT_SMALL,Graphics.COLOR_WHITE);
            line(dc,h*0.52,app.recordingStatus,tiny,Graphics.COLOR_LT_GRAY);
            line(dc,h*0.66,"Pending: "+model.data["outbox"].size().toString(),tiny,Graphics.COLOR_WHITE);
            return;
        }
        var e = a["entries"][a["cur"]];
        line(dc, top, "EX "+(a["cur"]+1).toString()+" / "+a["entries"].size().toString(), tiny, color);
        line(dc, top+rowH, trim(dc,e["name"],w*0.86), Graphics.FONT_SMALL, Graphics.COLOR_WHITE);
        var c = model.current(); var at = app.now();
        var title = "Exercise complete"; var detail = "DOWN: next exercise";
        if (c != null) {
            var row = c["side"] == null ? c["row"] : c["row"]["sides"][c["side"]];
            var marker = c["row"]["warmup"] == true ? "WARMUP " : "SET ";
            title = marker+(c["setIdx"]+1).toString()+" / "+e["sets"].size().toString()+(c["side"] == null ? "" : "  "+c["side"]);
            detail = (row["w"] == null ? "BW" : row["w"].toString()+" "+model.state["unit"])+"  x  ";
            detail += GymData.is(e["mode"],"time") ? (c["row"]["sec"] == null ? "?" : c["row"]["sec"].toString())+" sec" : (row["r"] == null ? "?" : row["r"].toString())+" reps";
        }
        line(dc,h*0.36,title,tiny,Graphics.COLOR_LT_GRAY);
        line(dc,h*0.47,detail,Graphics.FONT_SMALL,Graphics.COLOR_WHITE);
        var rest = model.restLeft(at);
        var status = "START: set done";
        if (model.paused()) { status = "PAUSED - menu to resume"; }
        else if (rest > 0) { status = "REST "+rest.toString()+" sec"; }
        else if (c != null && !model.supported(c)) { status = "Unsupported set: use phone"; }
        else if (c != null && GymData.is(e["mode"],"time")) { status = model.data["timing"] == null ? "START: begin timer" : model.elapsed(at).toString()+" sec  START: done"; }
        line(dc,h*0.60,status,tiny,rest>0 ? color : Graphics.COLOR_WHITE);
        line(dc,h*0.72,(app.heartRate == null ? "HR --" : "HR "+app.heartRate.toString())+"  |  Q "+model.data["outbox"].size().toString(),tiny,Graphics.COLOR_LT_GRAY);
        line(dc,h*0.82,app.recordingStatus,tiny,Graphics.COLOR_LT_GRAY);
    }
}

class WorkoutDelegate extends WatchUi.BehaviorDelegate {
    var app;
    function initialize(owner) { BehaviorDelegate.initialize(); app = owner; }
    function onSelect() { if (app.notice != null) { app.notice = null; WatchUi.requestUpdate(); return true; } app.action("setDone"); return true; }
    function onNextPage() { app.action("next"); return true; }
    function onBack() {
        if (app.notice != null) { app.notice = null; WatchUi.requestUpdate(); return true; }
        return onMenu();
    }
    function onMenu() {
        var menu = new WatchUi.Menu2({:title=>"openGym"});
        if (app.model.active() != null) {
            menu.addItem(new WatchUi.MenuItem(app.model.paused() ? "Resume" : "Pause", null, "pause", {}));
            menu.addItem(new WatchUi.MenuItem("Next exercise", null, "next", {}));
            menu.addItem(new WatchUi.MenuItem("Skip rest", null, "skipRest", {}));
            menu.addItem(new WatchUi.MenuItem("Finish & save", null, "finish", {}));
            menu.addItem(new WatchUi.MenuItem("Discard workout", null, "discard", {}));
        }
        menu.addItem(new WatchUi.MenuItem("Reconnect phone", null, "reconnect", {}));
        menu.addItem(new WatchUi.MenuItem("Exit app (save FIT)", null, "exit", {}));
        WatchUi.pushView(menu, new WorkoutMenu(app), WatchUi.SLIDE_UP);
        return true;
    }
}
class WorkoutMenu extends WatchUi.Menu2InputDelegate {
    var app;
    function initialize(owner) { Menu2InputDelegate.initialize(); app = owner; }
    function onSelect(item) {
        var id = item.getId();
        WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        if (id.equals("finish") || id.equals("discard")) {
            var text = id.equals("finish") ? "Finish workout and save FIT?" : "Discard workout and FIT?";
            WatchUi.pushView(new WatchUi.Confirmation(text),new WorkoutConfirm(app,id,app.model.wid()),WatchUi.SLIDE_UP);
        } else if (id.equals("reconnect")) { app.lastHelloAt = 0l; app.tick(); }
        else if (id.equals("exit")) { WatchUi.pushView(new WatchUi.Confirmation("Exit app and save partial FIT?"),new WorkoutConfirm(app,id,app.model.wid()),WatchUi.SLIDE_UP); }
        else { app.action(id); }
    }
}
class WorkoutConfirm extends WatchUi.ConfirmationDelegate {
    var app; var command; var workout;
    function initialize(owner, type, id) { ConfirmationDelegate.initialize(); app = owner; command = type; workout = id; }
    function onResponse(value) {
        if (value == WatchUi.CONFIRM_YES) {
            if (command.equals("exit")) { System.exit(); }
            else if (workout != null && app.model.wid() != null && workout.equals(app.model.wid())) { app.action(command); }
        }
        return true;
    }
}
