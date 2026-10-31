import Toybox.Graphics;
import Toybox.WatchUi;
import Toybox.Lang;
import Toybox.System;

class WorkoutView extends WatchUi.View {
    var app; var smallFont; var titleFont; var glyphs;
    const BACKGROUND = 0x10131a;
    const INK = 0xffc96d;
    const SUBTLE = 0xd3bda3;
    const ACCENT = 0xff8d32;
    const TRACK = 0x493c30;
    function initialize(owner) {
        View.initialize(); app = owner;
        glyphs = {"0"=>"111101101101111","1"=>"010110010010111","2"=>"111001111100111","3"=>"111001111001111",
            "4"=>"101101111001001","5"=>"111100111001111","6"=>"111100111101111","7"=>"111001010010010",
            "8"=>"111101111101111","9"=>"111101111001111","/"=>"001001010100100","-"=>"000000111000000",
            ":"=>"01010","."=>"00001"};
    }
    function onShow() { app.enableTouch(); app.refreshHeartRateZones(); }
    function fonts(w) {
        if (smallFont != null) { return; }
        smallFont = WatchUi.loadResource(w > 300 ? Rez.Fonts.SmallAmoled : Rez.Fonts.SmallSolar);
        titleFont = WatchUi.loadResource(w > 300 ? Rez.Fonts.TitleAmoled : Rez.Fonts.TitleSolar);
    }
    function text(dc, x, y, value, font, color, width) {
        var chord = WorkoutLayout.roundWidth(dc.getWidth(),dc.getHeight(),y,dc.getFontHeight(font));
        if (width > chord) { width = chord; }
        value = WorkoutLayout.ellipsis(dc,value,font,width);
        dc.setColor(color,Graphics.COLOR_TRANSPARENT);
        dc.drawText(x.toNumber(),y.toNumber(),font,value,Graphics.TEXT_JUSTIFY_CENTER);
    }
    function line(dc, y, value, font, color) { text(dc,dc.getWidth()/2,y,value,font,color,dc.getWidth()*0.74); }
    function icon(dc, kind, x, y, size, color) {
        dc.setColor(color,Graphics.COLOR_TRANSPARENT);
        var s = size/2.0; dc.setPenWidth(size > 16 ? 2 : 1);
        if (kind.equals("heart")) {
            dc.drawLine(x-s,y-s/3,x-s/2,y-s*0.7); dc.drawLine(x-s/2,y-s*0.7,x,y-s/3);
            dc.drawLine(x,y-s/3,x+s/2,y-s*0.7); dc.drawLine(x+s/2,y-s*0.7,x+s,y-s/3);
            dc.drawLine(x+s,y-s/3,x+s*0.8,y+s/3); dc.drawLine(x+s*0.8,y+s/3,x,y+s);
            dc.drawLine(x,y+s,x-s*0.8,y+s/3); dc.drawLine(x-s*0.8,y+s/3,x-s,y-s/3);
        } else if (kind.equals("clock")) {
            dc.drawCircle(x,y,s); dc.drawLine(x,y,x,y-s*0.6); dc.drawLine(x,y,x+s*0.5,y+s*0.3);
        } else if (kind.equals("weight")) {
            dc.drawLine(x-s*0.5,y-s,x-s*0.5,y+s); dc.drawLine(x+s*0.5,y-s,x+s*0.5,y+s);
            dc.drawLine(x-s,y-s*0.5,x-s,y+s*0.5); dc.drawLine(x+s,y-s*0.5,x+s,y+s*0.5); dc.drawLine(x-s*0.5,y,x+s*0.5,y);
        } else if (kind.equals("target")) {
            dc.drawLine(x-s*0.5,y+s,x-s*0.5,y-s); dc.drawLine(x-s*0.5,y-s,x+s,y-s*0.5); dc.drawLine(x+s,y-s*0.5,x-s*0.5,y);
        } else if (kind.equals("body")) {
            dc.drawCircle(x,y-s*0.6,s*0.35); dc.drawLine(x-s,y+s,x-s,y+s*0.25); dc.drawLine(x-s,y+s*0.25,x,y);
            dc.drawLine(x,y,x+s,y+s*0.25); dc.drawLine(x+s,y+s*0.25,x+s,y+s);
        } else if (kind.equals("phone")) {
            dc.drawRectangle(x-s*0.6,y-s,s*1.2,s*2); dc.drawLine(x-s*0.3,y+s*0.7,x+s*0.3,y+s*0.7);
        } else if (kind.equals("queue")) {
            dc.drawLine(x-s,y,x+s,y); dc.drawLine(x+s/3,y-s*0.6,x+s,y); dc.drawLine(x+s,y,x+s/3,y+s*0.6);
        } else {
            dc.drawLine(x-s,y,x+s,y); dc.drawLine(x+s/3,y-s*0.6,x+s,y); dc.drawLine(x+s,y,x+s/3,y+s*0.6);
        }
        dc.setPenWidth(1);
    }
    function progress(dc, fraction) {
        var w = dc.getWidth(); var h = dc.getHeight(); var radius = w*0.482;
        dc.setPenWidth(w > 300 ? 7 : 4); dc.setColor(TRACK,Graphics.COLOR_TRANSPARENT); dc.drawCircle(w/2,h/2,radius);
        dc.setColor(ACCENT,Graphics.COLOR_TRANSPARENT);
        // Equal drawArc angles mean a full circle, so never draw a zero sweep.
        var sweep = (WorkoutDashboard.clamp(fraction)*360).toNumber();
        if (sweep >= 360) { dc.drawCircle(w/2,h/2,radius); }
        else if (sweep > 0) { dc.drawArc(w/2,h/2,radius,Graphics.ARC_CLOCKWISE,90,(450-sweep)%360); }
        dc.setPenWidth(1);
    }
    function phaseLabel(dc, phase, warmup) {
        var full = warmup ? GymUi.string(Rez.Strings.Warmup)+" "+phase : phase;
        return dc.getTextWidthInPixels(full,smallFont) <= dc.getWidth()*0.29 ? full : phase;
    }
    function header(dc, phase, showZones) {
        var w = dc.getWidth(); var h = dc.getHeight(); var y = h*0.13; var height = dc.getFontHeight(smallFont);
        var colors = [0xa6afb9,0x6dbbff,0x99df80,0xffb35b,0xff7781];
        var zone = WorkoutDashboard.zone(app.heartRate,app.heartRateZones);
        var color = zone == null ? SUBTLE : colors[zone-1];
        var bpm = app.heartRate == null ? "--" : WorkoutControls.decimal(app.heartRate);
        icon(dc,"heart",w*0.31,y+height*0.5,w*0.034,color);
        dc.setColor(color,Graphics.COLOR_TRANSPARENT); dc.drawText(w*0.35,y,smallFont,bpm,Graphics.TEXT_JUSTIFY_LEFT);
        text(dc,w*0.63,y,phase,smallFont,INK,w*0.29);
        var barW = w*0.069; var gap = w*0.012; var start = (w-5*barW-4*gap)/2; var bottom = h*0.375;
        var known = WorkoutDashboard.validZones(app.heartRateZones) && app.heartRate != null;
        for (var i=0; showZones && i<5; i++) {
            var selected = zone == i+1; var barH = h*(selected ? 0.026 : 0.014);
            var x = start+i*(barW+gap); var top = bottom-barH;
            dc.setColor(known ? colors[i] : TRACK,Graphics.COLOR_TRANSPARENT); dc.fillRoundedRectangle(x,top,barW,barH,2);
            if (selected) {
                dc.setColor(0xfff4df,Graphics.COLOR_TRANSPARENT); dc.drawRoundedRectangle(x,top,barW,barH,2);
                dc.fillPolygon([[x+barW/2-w*0.0065,bottom+w*0.008],[x+barW/2+w*0.0065,bottom+w*0.008],[x+barW/2,bottom+w*0.0145]]);
            }
        }
        var pending = app.model.data["outbox"].size();
        if (pending > 0) {
            icon(dc,"queue",w*0.46,h*0.072,w*0.025,SUBTLE);
            text(dc,w*0.52,h*0.05,pending.toString(),smallFont,SUBTLE,w*0.1);
        }
    }
    function title(dc, name) {
        name = WorkoutLayout.normalize(name);
        var w = dc.getWidth(); var h = dc.getHeight(); var top = h*0.205; var bottom = h*0.335;
        var font = titleFont; var height = dc.getFontHeight(font);
        if (dc.getTextWidthInPixels(name,font) <= w*0.74) { line(dc,top+(bottom-top-height)/2,name,font,INK); return; }
        font = smallFont; height = dc.getFontHeight(font); var width = w*0.76;
        if (dc.getTextWidthInPixels(name,font) <= width) { line(dc,top+(bottom-top-height)/2,name,font,INK); return; }
        var count = WorkoutLayout.prefix(dc,name,font,width);
        text(dc,w/2,top,WorkoutLayout.trim(name.substring(0,count)),font,INK,width);
        text(dc,w/2,bottom-height,WorkoutLayout.trim(name.substring(count,name.length())),font,INK,width);
    }
    function digits(dc, value) {
        var w = dc.getWidth(); var h = dc.getHeight(); var units = 0;
        for (var i=0; i<value.length(); i++) { var ch = value.substring(i,i+1); units += ch.equals(":") || ch.equals(".") ? 2 : 4; }
        var cell = w*0.036;
        if (cell*units > w*0.72) { cell = w*0.72/units; }
        var x = (w-units*cell)/2+cell/2; var top = h*0.40; var gap = cell*0.2;
        dc.setColor(INK,Graphics.COLOR_TRANSPARENT);
        for (var j=0; j<value.length(); j++) {
            var c = value.substring(j,j+1); var pattern = glyphs[c];
            var columns = c.equals(":") || c.equals(".") ? 1 : 3;
            if (pattern != null) {
                for (var row=0; row<5; row++) {
                    for (var col=0; col<columns; col++) {
                        var index = row*columns+col;
                        if (pattern.substring(index,index+1).equals("1")) { dc.fillRectangle(x+col*cell,top+row*cell,cell-gap,cell-gap); }
                    }
                }
            }
            x += (columns+1)*cell;
        }
    }
    function detail(dc, value, kind) {
        var w = dc.getWidth(); var h = dc.getHeight(); var y = h*0.674;
        var width = w*0.70; value = WorkoutLayout.ellipsis(dc,value,smallFont,width-w*0.06);
        var total = dc.getTextWidthInPixels(value,smallFont)+w*0.055; var x = (w-total)/2;
        icon(dc,kind,x+w*0.016,y+dc.getFontHeight(smallFont)/2,w*0.032,SUBTLE);
        dc.setColor(SUBTLE,Graphics.COLOR_TRANSPARENT); dc.drawText(x+w*0.05,y,smallFont,value,Graphics.TEXT_JUSTIFY_LEFT);
    }
    function button(dc, command, dismiss) {
        var r = WorkoutControls.rect("primary",dc.getWidth(),dc.getHeight());
        var x = r[0]+r[2]/2; var y = r[1]+r[3]/2; var s = r[2]*0.24;
        dc.setColor(command == null && !dismiss ? TRACK : ACCENT,Graphics.COLOR_TRANSPARENT); dc.fillCircle(x,y,r[2]/2);
        dc.setColor(BACKGROUND,Graphics.COLOR_TRANSPARENT); dc.setPenWidth(dc.getWidth() > 300 ? 4 : 3);
        if (dismiss || GymData.is(command,"setDone") || GymData.is(command,"finish")) {
            dc.drawLine(x-s,y,x-s*0.2,y+s*0.65); dc.drawLine(x-s*0.2,y+s*0.65,x+s,y-s*0.7);
        } else if (GymData.is(command,"startSet") || GymData.is(command,"pause")) {
            dc.fillPolygon([[x-s*0.6,y-s],[x+s,y],[x-s*0.6,y+s]]);
        } else if (GymData.is(command,"skipRest")) {
            dc.fillPolygon([[x-s,y-s],[x+s*0.6,y],[x-s,y+s]]); dc.drawLine(x+s,y-s,x+s,y+s);
        } else if (command != null) {
            dc.drawLine(x-s,y,x+s,y); dc.drawLine(x+s*0.2,y-s*0.8,x+s,y); dc.drawLine(x+s,y,x+s*0.2,y+s*0.8);
        } else { icon(dc,"phone",x,y,s,BACKGROUND); }
        dc.setPenWidth(1);
    }
    function onUpdate(dc) {
        var w = dc.getWidth(); var h = dc.getHeight(); fonts(w);
        app.viewWidth = w; app.viewHeight = h;
        dc.setColor(INK,BACKGROUND); dc.clear();
        var data = WorkoutDashboard.present(app.model,app.now());
        progress(dc,data == null ? 0.0 : data["progress"]);
        var overlay = app.notice != null || app.timerAlert != null;
        header(dc,data == null ? "" : phaseLabel(dc,data["phase"],data["warmup"]),data != null && !overlay);
        if (app.notice != null || app.timerAlert != null) {
            var message = app.notice == null ? GymUi.string(app.timerAlert["kind"].equals("rest") ? Rez.Strings.RestComplete : Rez.Strings.TargetReached) : GymUi.message(app.notice);
            var remaining = WorkoutLayout.normalize(message); var y = h*0.28; var height = dc.getFontHeight(smallFont);
            var end = WorkoutControls.rect("primary",w,h)[1]-h*0.02;
            while (remaining.length() > 0 && y+height <= end) {
                var last = y+2*height+4 > end;
                var count = last ? remaining.length() : WorkoutLayout.prefix(dc,remaining,smallFont,w*0.72);
                line(dc,y,remaining.substring(0,count),smallFont,INK);
                remaining = WorkoutLayout.trim(remaining.substring(count,remaining.length())); y += height+4;
            }
            button(dc,null,true); return;
        }
        if (data == null) {
            line(dc,h*0.26,"openGym",titleFont,INK);
            line(dc,h*0.44,GymUi.string(Rez.Strings.NoWorkout),smallFont,SUBTLE);
            line(dc,h*0.52,GymUi.string(Rez.Strings.StartPhone),smallFont,INK);
            line(dc,h*0.64,GymUi.message(app.recordingStatus),smallFont,SUBTLE);
            line(dc,h*0.73,WatchUi.loadResource(Rez.Strings.AppVersion),smallFont,SUBTLE); return;
        }
        title(dc,data["title"]); digits(dc,data["main"]);
        line(dc,h*0.59,data["unit"],smallFont,SUBTLE);
        detail(dc,data["detail"],data["detailIcon"]); button(dc,data["command"],false);
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
    function onSelect() { return primaryAction(); }
    function primaryAction() {
        if (dismiss()) { return true; }
        var command = WorkoutControls.primary(app.model,app.now());
        if (command != null) {
            if (command.equals("finish")) { confirmFinish(); } else { app.action(command); }
        }
        return true;
    }
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
        return primaryAction();
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
        if (id.equals("status")) { app.notice = WatchUi.loadResource(Rez.Strings.AppVersion)+". "+GymUi.message(app.recordingStatus)+". "+GymUi.string(Rez.Strings.PendingCommands)+" "+app.model.data["outbox"].size().toString(); WatchUi.requestUpdate(); }
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
