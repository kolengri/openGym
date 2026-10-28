import Toybox.Graphics;
import Toybox.WatchUi;
import Toybox.Lang;
import Toybox.System;

class WorkoutView extends WatchUi.View {
    var app;
    function initialize(owner) { View.initialize(); app = owner; }
    function onShow() { app.enableTouch(); }
    function text(dc, x, y, value, font, color, width) {
        dc.setColor(color, Graphics.COLOR_TRANSPARENT);
        // A smaller font before truncation keeps values and long names readable.
        if (dc.getTextWidthInPixels(value,font) > width) { font = Graphics.FONT_XTINY; }
        width = width < WorkoutLayout.roundWidth(dc.getWidth(),dc.getHeight(),y,dc.getFontHeight(font)) ? width : WorkoutLayout.roundWidth(dc.getWidth(),dc.getHeight(),y,dc.getFontHeight(font));
        value = WorkoutLayout.ellipsis(dc,value,font,width);
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
        var layout = WorkoutLayout.metrics(dc,w,h);
        // The reference's divided dashboard, using measured HR and workout data.
        dc.setColor(green,Graphics.COLOR_TRANSPARENT);
        dc.drawLine(w*0.40,h*0.055,w*0.60,h*0.055);
        var headerWidth = WorkoutLayout.roundWidth(w,h,layout["headerY"],dc.getFontHeight(tiny));
        var hrLabel = WorkoutLayout.header(dc,GymUi.string(Rez.Strings.HeartRate),GymUi.string(Rez.Strings.HeartRateCompact),
            app.heartRate == null ? "--" : WorkoutControls.decimal(app.heartRate),model.data["outbox"].size(),headerWidth);
        line(dc,layout["headerY"],hrLabel,tiny,Graphics.COLOR_WHITE);
        dc.setColor(Graphics.COLOR_DK_GRAY,Graphics.COLOR_TRANSPARENT);
        dc.drawLine(w*0.16,layout["headerBottom"],w*0.84,layout["headerBottom"]);
        if (app.notice != null || app.timerAlert != null) {
            var alert = app.timerAlert;
            if (app.notice != null) {
                var msg = WorkoutLayout.normalize(GymUi.message(app.notice));
                var y = h*0.26; var height = dc.getFontHeight(tiny);
                var limit = WorkoutControls.rect("primary",w,h)[1]-layout["gap"];
                var first = true;
                while (msg.length() > 0 && y+height <= limit) {
                    var width = WorkoutLayout.roundWidth(w,h,y,height);
                    var last = y+2*height+layout["gap"] > limit;
                    var count = last ? msg.length() : WorkoutLayout.prefix(dc,msg,tiny,width);
                    line(dc,y,msg.substring(0,count),tiny,first ? Graphics.COLOR_YELLOW : Graphics.COLOR_WHITE);
                    msg = WorkoutLayout.trim(msg.substring(count,msg.length()));
                    y += height+layout["gap"]; first = false;
                }
            } else {
                line(dc,h*0.29,alert["kind"].equals("rest") ? GymUi.string(Rez.Strings.RestComplete) : GymUi.string(Rez.Strings.TargetReached),Graphics.FONT_SMALL,green);
                line(dc,h*0.43,alert["kind"].equals("rest") ? GymUi.string(Rez.Strings.ReadyNextSet) : GymUi.string(Rez.Strings.TimerContinues),tiny,Graphics.COLOR_WHITE);
                line(dc,h*0.53,GymUi.string(Rez.Strings.DismissContinue),tiny,Graphics.COLOR_LT_GRAY);
            }
            button(dc,"primary",GymUi.string(Rez.Strings.Dismiss),true,true);
            return;
        }
        if (a == null) {
            line(dc,h*0.26,"openGym",Graphics.FONT_SMALL,green);
            line(dc,h*0.39,GymUi.string(Rez.Strings.NoWorkout),tiny,Graphics.COLOR_WHITE);
            line(dc,h*0.49,GymUi.string(Rez.Strings.StartPhone),Graphics.FONT_SMALL,Graphics.COLOR_WHITE);
            line(dc,h*0.63,GymUi.message(app.recordingStatus),tiny,Graphics.COLOR_LT_GRAY);
            line(dc,h*0.63+dc.getFontHeight(tiny)+layout["gap"],WatchUi.loadResource(Rez.Strings.AppVersion)+" | "+GymUi.string(Rez.Strings.Queue)+" "+model.data["outbox"].size().toString(),tiny,Graphics.COLOR_LT_GRAY);
            return;
        }
        var e = a["entries"][a["cur"]]; var c = model.current();
        var title = WorkoutLayout.title(dc,e["name"],w,h,layout);
        dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_TRANSPARENT);
        for (var i = 0; i < title["rows"].size(); i++) {
            var rowTitle = title["rows"][i];
            dc.drawText(w/2,rowTitle[1],title["font"],rowTitle[0],Graphics.TEXT_JUSTIFY_CENTER);
        }
        dc.setColor(Graphics.COLOR_DK_GRAY,Graphics.COLOR_TRANSPARENT);
        dc.drawLine(w*0.10,layout["titleBottom"]+layout["gap"],w*0.90,layout["titleBottom"]+layout["gap"]);
        dc.drawLine(w*0.50,layout["fieldTop"],w*0.50,layout["fieldBottom"]);
        var left = w*0.28; var right = w*0.72; var width = w*0.40;
        var label = GymUi.string(Rez.Strings.Exercise)+" "+(a["cur"]+1).toString()+" / "+a["entries"].size().toString();
        var value = GymUi.string(Rez.Strings.Complete); var detail = GymUi.string(Rez.Strings.AllSetsDone);
        if (c != null) {
            var row = c["side"] == null ? c["row"] : c["row"]["sides"][c["side"]];
            label = (c["row"]["warmup"] == true ? GymUi.string(Rez.Strings.Warmup)+" " : GymUi.string(Rez.Strings.Set)+" ")+(c["setIdx"]+1).toString()+" / "+e["sets"].size().toString()+(c["side"] == null ? "" : " "+GymUi.side(c["side"]));
            value = row["w"] == null ? GymUi.string(Rez.Strings.Bodyweight) : WorkoutControls.decimal(row["w"])+" "+GymUi.unit(model.state["unit"]);
            detail = GymData.is(e["mode"],"time") ? (c["row"]["sec"] == null ? GymUi.string(Rez.Strings.Target)+" --:--" : GymUi.string(Rez.Strings.Target)+" "+WorkoutControls.clock(c["row"]["sec"])) : (row["r"] == null ? "?" : WorkoutControls.decimal(row["r"]))+" "+GymUi.string(Rez.Strings.Reps);
        }
        text(dc,left,layout["labelY"],label,tiny,Graphics.COLOR_LT_GRAY,width);
        text(dc,left,layout["valueY"],value,layout["valueFont"],Graphics.COLOR_WHITE,width);
        text(dc,left,layout["detailY"],detail,tiny,Graphics.COLOR_WHITE,width);
        var rest = model.restLeft(at);
        var timerLabel = rest > 0 ? GymUi.string(Rez.Strings.Rest) : GymUi.string(Rez.Strings.SetTime);
        var timer = rest > 0 ? rest : model.elapsed(at);
        if (model.paused()) { timerLabel = GymUi.string(Rez.Strings.Paused); }
        text(dc,right,layout["labelY"],timerLabel,tiny,green,width);
        text(dc,right,layout["valueY"],WorkoutControls.clock(timer),layout["valueFont"],Graphics.COLOR_WHITE,width);
        var timerDetail = rest > 0 ? GymUi.string(Rez.Strings.Remaining) : (model.data["timing"] == null ? GymUi.string(Rez.Strings.TapStart) : GymUi.string(Rez.Strings.Elapsed));
        text(dc,right,layout["detailY"],timerDetail,tiny,Graphics.COLOR_LT_GRAY,width);
        var command = WorkoutControls.primary(model,at);
        button(dc,"primary",WorkoutControls.label(command),command != null,true);
        button(dc,"next",GymUi.string(Rez.Strings.NextShort),true,false);
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
        if (hit.equals("next")) { app.action("next"); return true; }
        var command = WorkoutControls.primary(app.model,app.now());
        if (command != null) {
            if (command.equals("finish")) { confirmFinish(); } else { app.action(command); }
        }
        return true;
    }
    function confirmFinish() {
        WatchUi.pushView(new WatchUi.Confirmation(GymUi.string(Rez.Strings.ConfirmFinish)),new WorkoutConfirm(app,"finish",app.model.wid()),WatchUi.SLIDE_UP);
    }
    function onMenu() {
        if (dismiss()) { return true; }
        var menu = new WatchUi.Menu2({:title=>"openGym"});
        if (app.model.active() != null) {
            menu.addItem(new WatchUi.MenuItem(app.model.paused() ? GymUi.string(Rez.Strings.Resume) : GymUi.string(Rez.Strings.Pause), null, "pause", {}));
            menu.addItem(new WatchUi.MenuItem(GymUi.string(Rez.Strings.NextExercise), null, "next", {}));
            menu.addItem(new WatchUi.MenuItem(GymUi.string(Rez.Strings.SkipRest), null, "skipRest", {}));
            menu.addItem(new WatchUi.MenuItem(GymUi.string(Rez.Strings.FinishSave), null, "finish", {}));
            menu.addItem(new WatchUi.MenuItem(GymUi.string(Rez.Strings.DiscardWorkout), null, "discard", {}));
        }
        menu.addItem(new WatchUi.MenuItem(GymUi.string(Rez.Strings.Status), GymUi.message(app.recordingStatus)+" | "+GymUi.string(Rez.Strings.Queue)+" "+app.model.data["outbox"].size().toString(), "status", {}));
        menu.addItem(new WatchUi.MenuItem(GymUi.string(Rez.Strings.Reconnect), null, "reconnect", {}));
        menu.addItem(new WatchUi.MenuItem(GymUi.string(Rez.Strings.ExitSave), null, "exit", {}));
        WatchUi.pushView(menu, new WorkoutMenu(app), WatchUi.SLIDE_UP);
        return true;
    }
}
class WorkoutMenu extends WatchUi.Menu2InputDelegate {
    var app; var workout;
    function initialize(owner) { Menu2InputDelegate.initialize(); app = owner; workout = app.model.wid(); }
    function closeMenu() { WatchUi.popView(WatchUi.SLIDE_IMMEDIATE); }
    function confirm(command) {
        var text = command.equals("exit") ? GymUi.string(Rez.Strings.ConfirmExit) : command.equals("finish") ? GymUi.string(Rez.Strings.ConfirmFinish) : GymUi.string(Rez.Strings.ConfirmDiscard);
        WatchUi.pushView(new WatchUi.Confirmation(text),new WorkoutConfirm(app,command,workout),WatchUi.SLIDE_UP);
    }
    function onSelect(item) {
        var id = item.getId();
        closeMenu();
        if (!id.equals("status") && !id.equals("reconnect") && !sameWorkout(workout,app.model.wid())) {
            app.notice = GymUi.string(Rez.Strings.WorkoutChanged); WatchUi.requestUpdate(); return;
        }
        if (id.equals("status")) { app.notice = GymUi.message(app.recordingStatus)+". "+GymUi.string(Rez.Strings.PendingCommands)+" "+app.model.data["outbox"].size().toString(); WatchUi.requestUpdate(); }
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
