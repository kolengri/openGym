import Toybox.Graphics;
import Toybox.WatchUi;
import Toybox.Lang;
import Toybox.System;

class WorkoutView extends WatchUi.View {
    var app;
    function initialize(owner) { View.initialize(); app = owner; }
    function text(dc, x, y, value, font, color, width) {
        dc.setColor(color, Graphics.COLOR_TRANSPARENT);
        // A smaller font before truncation keeps values and long names readable.
        if (dc.getTextWidthInPixels(value,font) > width) { font = Graphics.FONT_XTINY; }
        while (value.length() > 1 && dc.getTextWidthInPixels(value,font) > width) { value = value.substring(0,value.length()-1); }
        dc.drawText(x,y,font,value,Graphics.TEXT_JUSTIFY_CENTER);
    }
    function line(dc, y, value, font, color) { text(dc,dc.getWidth()/2,y,value,font,color,dc.getWidth()*0.82); }
    function button(dc, id, label, enabled, primary) {
        var r = WorkoutControls.rect(id,dc.getWidth(),dc.getHeight());
        var color = enabled ? Graphics.COLOR_GREEN : Graphics.COLOR_DK_GRAY;
        dc.setColor(primary ? color : Graphics.COLOR_BLACK,Graphics.COLOR_TRANSPARENT);
        dc.fillRoundedRectangle(r[0],r[1],r[2],r[3],5);
        dc.setColor(color,Graphics.COLOR_TRANSPARENT);
        dc.drawRoundedRectangle(r[0],r[1],r[2],r[3],5);
        var font = Graphics.FONT_XTINY;
        text(dc,r[0]+r[2]/2,r[1]+(r[3]-dc.getFontHeight(font))/2,label,font,primary ? Graphics.COLOR_BLACK : Graphics.COLOR_WHITE,r[2]-6);
    }
    function onUpdate(dc) {
        dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK); dc.clear();
        var h = dc.getHeight(); var w = dc.getWidth();
        app.viewWidth = w; app.viewHeight = h;
        var tiny = Graphics.FONT_XTINY; var green = Graphics.COLOR_GREEN;
        var model = app.model; var a = model.active(); var at = app.now();
        // The reference's divided dashboard, using measured HR and workout data.
        dc.setColor(green,Graphics.COLOR_TRANSPARENT);
        dc.drawLine(w*0.40,h*0.055,w*0.60,h*0.055);
        line(dc,h*0.075,"HR "+(app.heartRate == null ? "--" : app.heartRate.toString()),Graphics.FONT_MEDIUM,Graphics.COLOR_WHITE);
        dc.setColor(Graphics.COLOR_DK_GRAY,Graphics.COLOR_TRANSPARENT);
        dc.drawLine(w*0.16,h*0.215,w*0.84,h*0.215);
        if (app.notice != null || app.timerAlert != null) {
            var alert = app.timerAlert;
            if (app.notice != null) {
                var msg = app.notice; var split = msg.find(". ");
                line(dc,h*0.30,split == null ? msg : msg.substring(0,split),tiny,Graphics.COLOR_YELLOW);
                if (split != null) { line(dc,h*0.41,msg.substring(split+2,msg.length()),tiny,Graphics.COLOR_WHITE); }
            } else {
                line(dc,h*0.29,alert["kind"].equals("rest") ? "Rest complete" : "Set target reached",Graphics.FONT_SMALL,green);
                line(dc,h*0.43,alert["kind"].equals("rest") ? "Ready for your next set" : "Timer keeps running",tiny,Graphics.COLOR_WHITE);
                line(dc,h*0.53,"Dismiss to continue",tiny,Graphics.COLOR_LT_GRAY);
            }
            button(dc,"primary","Dismiss",true,true);
            return;
        }
        if (a == null) {
            line(dc,h*0.26,"openGym",Graphics.FONT_SMALL,green);
            line(dc,h*0.39,"No workout connected",tiny,Graphics.COLOR_WHITE);
            line(dc,h*0.49,"Start on phone",Graphics.FONT_SMALL,Graphics.COLOR_WHITE);
            line(dc,h*0.63,app.recordingStatus,tiny,Graphics.COLOR_LT_GRAY);
            line(dc,h*0.70,WatchUi.loadResource(Rez.Strings.AppVersion)+" | Q "+model.data["outbox"].size().toString(),tiny,Graphics.COLOR_LT_GRAY);
            button(dc,"menu","Menu",true,false);
            return;
        }
        var e = a["entries"][a["cur"]]; var c = model.current();
        line(dc,h*0.235,e["name"],Graphics.FONT_SMALL,Graphics.COLOR_WHITE);
        dc.setColor(Graphics.COLOR_DK_GRAY,Graphics.COLOR_TRANSPARENT);
        dc.drawLine(w*0.10,h*0.345,w*0.90,h*0.345);
        dc.drawLine(w*0.50,h*0.36,w*0.50,h*0.60);
        dc.drawLine(w*0.13,h*0.615,w*0.87,h*0.615);
        var left = w*0.28; var right = w*0.72; var width = w*0.40;
        var label = "EX "+(a["cur"]+1).toString()+" / "+a["entries"].size().toString();
        var value = "Complete"; var detail = "All sets done";
        if (c != null) {
            var row = c["side"] == null ? c["row"] : c["row"]["sides"][c["side"]];
            label = (c["row"]["warmup"] == true ? "WARM " : "SET ")+(c["setIdx"]+1).toString()+" / "+e["sets"].size().toString()+(c["side"] == null ? "" : " "+c["side"]);
            value = row["w"] == null ? "BW" : row["w"].toString()+" "+model.state["unit"];
            detail = GymData.is(e["mode"],"time") ? (c["row"]["sec"] == null ? "Target --:--" : "Target "+WorkoutControls.clock(c["row"]["sec"])) : (row["r"] == null ? "?" : row["r"].toString())+" reps";
        }
        text(dc,left,h*0.36,label,tiny,Graphics.COLOR_LT_GRAY,width);
        text(dc,left,h*0.425,value,Graphics.FONT_SMALL,Graphics.COLOR_WHITE,width);
        text(dc,left,h*0.535,detail,tiny,Graphics.COLOR_WHITE,width);
        var rest = model.restLeft(at);
        var timerLabel = rest > 0 ? "REST" : "SET TIME";
        var timer = rest > 0 ? rest : model.elapsed(at);
        if (model.paused()) { timerLabel = "PAUSED"; }
        text(dc,right,h*0.36,timerLabel,tiny,green,width);
        text(dc,right,h*0.425,WorkoutControls.clock(timer),Graphics.FONT_MEDIUM,Graphics.COLOR_WHITE,width);
        var timerDetail = rest > 0 ? "remaining" : (model.data["timing"] == null ? "tap Start set" : "elapsed");
        text(dc,right,h*0.535,timerDetail,tiny,Graphics.COLOR_LT_GRAY,width);
        var command = WorkoutControls.primary(model,at);
        button(dc,"primary",WorkoutControls.label(command),command != null,true);
        button(dc,"next","Next ex",true,false);
        button(dc,"menu","Menu",true,false);
    }
}

// BehaviorDelegate consumes tap events as onSelect before onTap can hit-test.
// Route physical keys explicitly so touch buttons retain their own actions.
class WorkoutDelegate extends WatchUi.InputDelegate {
    var app;
    function initialize(owner) { InputDelegate.initialize(); app = owner; }
    function dismiss() {
        if (app.notice == null && app.timerAlert == null) { return false; }
        if (app.notice != null) { app.notice = null; } else { app.timerAlert = null; }
        WatchUi.requestUpdate(); return true;
    }
    function onKey(event) { return keyAction(event.getKey()); }
    function keyAction(key) {
        if (key == WatchUi.KEY_ENTER) { return onSelect(); }
        if (key == WatchUi.KEY_DOWN) { return onNextPage(); }
        if (key == WatchUi.KEY_MENU) { return onMenu(); }
        if (key == WatchUi.KEY_ESC) { return onBack(); }
        return false;
    }
    function onSelect() { if (!dismiss()) { app.action("setDone"); } return true; }
    function onNextPage() { if (!dismiss()) { app.action("next"); } return true; }
    function onBack() { return dismiss() ? true : onMenu(); }
    function onTap(event) {
        var p = event.getCoordinates();
        return tapAt(p[0],p[1]);
    }
    function tapAt(x,y) {
        if (app.viewWidth == null || app.viewHeight == null) { return false; }
        var hit = WorkoutControls.hit(app.viewWidth,app.viewHeight,x,y,app.model.active() != null,app.notice != null || app.timerAlert != null);
        if (hit == null) { return false; }
        if (hit.equals("dismiss")) { return dismiss(); }
        if (hit.equals("menu")) { return onMenu(); }
        if (hit.equals("next")) { app.action("next"); return true; }
        var command = WorkoutControls.primary(app.model,app.now());
        if (command != null) {
            if (command.equals("finish")) { confirmFinish(); } else { app.action(command); }
        }
        return true;
    }
    function confirmFinish() {
        WatchUi.pushView(new WatchUi.Confirmation("Finish workout and save FIT?"),new WorkoutConfirm(app,"finish",app.model.wid()),WatchUi.SLIDE_UP);
    }
    function onMenu() {
        if (dismiss()) { return true; }
        var menu = new WatchUi.Menu2({:title=>"openGym"});
        if (app.model.active() != null) {
            menu.addItem(new WatchUi.MenuItem(app.model.paused() ? "Resume" : "Pause", null, "pause", {}));
            menu.addItem(new WatchUi.MenuItem("Next exercise", null, "next", {}));
            menu.addItem(new WatchUi.MenuItem("Skip rest", null, "skipRest", {}));
            menu.addItem(new WatchUi.MenuItem("Finish & save", null, "finish", {}));
            menu.addItem(new WatchUi.MenuItem("Discard workout", null, "discard", {}));
        }
        menu.addItem(new WatchUi.MenuItem("Status", app.recordingStatus+" | Q "+app.model.data["outbox"].size().toString(), "status", {}));
        menu.addItem(new WatchUi.MenuItem("Reconnect phone", null, "reconnect", {}));
        menu.addItem(new WatchUi.MenuItem("Exit app (save FIT)", null, "exit", {}));
        WatchUi.pushView(menu, new WorkoutMenu(app), WatchUi.SLIDE_UP);
        return true;
    }
}
class WorkoutMenu extends WatchUi.Menu2InputDelegate {
    var app; var workout;
    function initialize(owner) { Menu2InputDelegate.initialize(); app = owner; workout = app.model.wid(); }
    function closeMenu() { WatchUi.popView(WatchUi.SLIDE_IMMEDIATE); }
    function confirm(command) {
        var text = command.equals("exit") ? "Exit app and save partial FIT?" : command.equals("finish") ? "Finish workout and save FIT?" : "Discard workout and FIT?";
        WatchUi.pushView(new WatchUi.Confirmation(text),new WorkoutConfirm(app,command,workout),WatchUi.SLIDE_UP);
    }
    function onSelect(item) {
        var id = item.getId();
        closeMenu();
        if (!id.equals("status") && !id.equals("reconnect") && !sameWorkout(workout,app.model.wid())) {
            app.notice = "Workout changed. Open menu again."; WatchUi.requestUpdate(); return;
        }
        if (id.equals("status")) { app.notice = app.recordingStatus+". Pending commands: "+app.model.data["outbox"].size().toString(); WatchUi.requestUpdate(); }
        else if (id.equals("finish") || id.equals("discard")) {
            confirm(id);
        } else if (id.equals("reconnect")) { app.lastHelloAt = 0l; app.tick(); }
        else if (id.equals("exit")) { confirm(id); }
        else { app.action(id); }
    }
}
function sameWorkout(expected, current) { return expected == null ? current == null : GymData.is(current,expected); }
class WorkoutConfirm extends WatchUi.ConfirmationDelegate {
    var app; var command; var workout;
    function initialize(owner, type, id) { ConfirmationDelegate.initialize(); app = owner; command = type; workout = id; }
    function onResponse(value) {
        if (value == WatchUi.CONFIRM_YES && sameWorkout(workout,app.model.wid())) {
            if (command.equals("exit")) { exitApp(); }
            else if (workout != null) { app.action(command); }
        }
        return true;
    }
    function exitApp() { System.exit(); }
}
