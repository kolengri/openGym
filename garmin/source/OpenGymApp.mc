import Toybox.ActivityRecording;
import Toybox.Activity;
import Toybox.Application;
import Toybox.Communications;
import Toybox.Cryptography;
import Toybox.Lang;
import Toybox.Sensor;
import Toybox.System;
import Toybox.Time;
import Toybox.Timer;
import Toybox.WatchUi;
import Toybox.Attention;

class OpenGymApp extends Application.AppBase {
    var model;
    var notice = null;
    var recording = null;
    var recordingWid = null;
    var recordingStatus = "";
    var heartRate = null;
    var viewWidth = null;
    var viewHeight = null;
    var busy = false;
    var tickTimer;
    var lastHrAt = 0l;
    var lastSendAt = 0l;
    var lastHelloAt = 0l;
    var lastPersistAt = 0l;
    var alerts;
    var timerAlert = null;
    var sender;
    var txStarted = 0l;
    var store;
    var storageFatal = false;
    function initialize() { AppBase.initialize(); }
    function now() { return Time.now().value().toLong() * 1000l; }
    function onStart(state) as Void {
        store = new GymStore(new GarminStorage());
        var saved = null;
        try { saved = store.load(); }
        catch (ex) { storageFatal = true; notice = "Storage recovery failed. Keep app data."; }
        var install = "";
        if (saved == null) {
            var random = Cryptography.randomBytes(16);
            var items1 = random; for (var idx1 = 0; idx1 < items1.size(); idx1++) { var b = items1[idx1]; install += b.format("%02x"); }
        }
        try { model = new WorkoutModel(saved, install); }
        catch (ex) {
            storageFatal = true; notice = "Storage recovery failed. Keep app data.";
            model = new WorkoutModel(null, "recovery");
        }
        if (!storageFatal) { persist(); }
        alerts = new WorkoutAlerts();
        sender = new GymConnectionListener(self);
        Communications.registerForPhoneAppMessages(method(:onPhone));
        Sensor.setEnabledSensors([Sensor.SENSOR_HEARTRATE]);
        Sensor.enableSensorEvents(method(:onSensor));
        tickTimer = new Timer.Timer();
        tickTimer.start(method(:tick), 1000, true);
        reconcileRecording();
        tick();
    }
    function getInitialView() { return [new WorkoutView(self), new WorkoutDelegate(self)]; }
    // Foreground app setting only. Do not change global device lock preferences or
    // continually override input settings from the timer/sensor callbacks.
    function enableTouch() {
        if (WatchUi has :configureTouchEvents) {
            try { WatchUi.configureTouchEvents({:enabled=>true}); } catch (ex) {}
        }
    }
    function persist() {
        if (storageFatal) { return false; }
        try { store.save(model.data); return true; }
        catch (ex) { notice = "Storage full. Reconnect phone."; return false; }
    }
    // A failed storage write rolls back the entire command before FIT side effects
    // or transport. A visible completion must always have a durable event ID.
    function action(type) {
        if (storageFatal) { return false; }
        var previous = GymData.copy(model.data);
        var ok = false;
        if (type.equals("startSet")) { ok = model.startSet(now()); }
        else if (type.equals("setDone")) { ok = model.setDone(now()); }
        else if (type.equals("next")) { ok = model.next(now()); }
        else if (type.equals("pause")) { ok = model.pause(now()); }
        else { ok = model.queue(type, {}, now()); }
        notice = model.error;
        if (ok && !persist()) {
            model = new WorkoutModel(previous, "");
            ok = false;
        }
        if (ok) { timerAlert = null; reconcileRecording(); updateAlerts(now()); flush(); }
        WatchUi.requestUpdate();
        return ok;
    }
    function onPhone(msg as Communications.PhoneAppMessage) as Void { receive(msg.data); }
    function receive(payload) {
        if (storageFatal) { return; }
        if (!(payload instanceof Dictionary) || payload["v"] != 1) { return; }
        var previous = GymData.copy(model.data);
        var reported = hello();
        var ok = false;
        if (GymData.is(payload["kind"],"snapshot")) { ok = model.snapshot(payload, now()); }
        else if (GymData.is(payload["kind"],"ack")) { ok = model.acknowledge(payload, now()); }
        notice = model.error;
        if (ok && !persist()) { model = new WorkoutModel(previous, ""); ok = false; }
        // The phone replays retained ACKs for every hello. Only changed applied
        // state needs a prompt reply; duplicate ACKs keep the normal deadline.
        if (ok) {
            var current = hello();
            var sameWid = (reported["wid"] == null && current["wid"] == null) || GymData.is(reported["wid"], current["wid"]);
            if (reported["seq"] != current["seq"] || !sameWid || reported["pending"] != current["pending"]) { lastHelloAt = 0l; }
        }
        reconcileRecording();
        updateAlerts(now());
        WatchUi.requestUpdate();
    }
    function send(payload) {
        if (busy || !System.getDeviceSettings().phoneConnected) { return false; }
        try {
            busy = true; txStarted = now();
            Communications.transmit(payload, null, sender);
            return true;
        } catch (ex) { busy = false; return false; }
    }
    function flush() {
        if (model.data["outbox"].size() > 0) {
            if (send({"v"=>1, "kind"=>"events", "events"=>model.batch()})) { lastSendAt = now(); }
        }
    }
    // Optional status fields preserve the existing v1 hello/phone compatibility.
    function hello() {
        return {"v"=>1, "kind"=>"hello", "seq"=>model.data["seq"],
            "wid"=>model.wid(), "pending"=>model.data["outbox"].size()};
    }
    function tick() as Void {
        var at = now();
        if (recording != null && (model.wid() == null || !recordingWid.equals(model.wid()))) { reconcileRecording(); }
        // Recover transport if the phone vanished without a callback.
        if (busy && at - txStarted > 15000) { busy = false; }
        if (!busy && at - lastHelloAt >= 30000) {
            if (send(hello())) { lastHelloAt = at; }
        } else if (!busy && at - lastSendAt >= 5000) { flush(); }
        updateAlerts(at);
        if (at - lastPersistAt >= 15000 && model.active() != null) { persist(); lastPersistAt = at; }
        WatchUi.requestUpdate();
    }
    function updateAlerts(at) {
        if (timerAlert != null && !alerts.valid(timerAlert,model)) { timerAlert = null; }
        var alert = alerts.poll(model,at);
        if (alert != null) {
            timerAlert = alert;
            var settings = model.state["settings"];
            if (settings == null || settings["restHaptics"] != false) {
                try { Attention.vibrate([new Attention.VibeProfile(75, 350), new Attention.VibeProfile(0, 150), new Attention.VibeProfile(75, 350)]); } catch (ex) {}
            }
        }
    }
    function onSensor(info as Sensor.Info) as Void {
        var bpm = info.heartRate;
        if (!GymData.value(bpm, 25, 250)) { heartRate = null; return; }
        heartRate = bpm;
        var at = now();
        model.sample(bpm, at);
        WatchUi.requestUpdate();
        if (model.wid() != null && at - lastHrAt >= 5000 && !busy && model.data["outbox"].size() == 0) {
            if (send({"v"=>1, "kind"=>"hr", "wid"=>model.wid(), "bpm"=>bpm, "at"=>at})) { lastHrAt = at; }
        }
    }
    function recordingClaim(id) {
        return model.recordingClaim(id);
    }
    function reconcileRecording() {
        if (recording != null && (model.wid() == null || !recordingWid.equals(model.wid()))) {
            var discard = false;
            var items3 = model.data["ended"]; for (var idx3 = 0; idx3 < items3.size(); idx3++) { var e = items3[idx3]; if (e["wid"].equals(recordingWid)) { discard = e["discard"]; } }
            completeRecording(discard);
        }
        var id = model.wid();
        if (id == null) { return; }
        if (recording == null) {
            var claimed = recordingClaim(id);
            if (claimed != null) { recordingStatus = "Recording interrupted"; return; }
            var settings = model.state["settings"];
            if (settings != null && settings["recording"] == false) { recordingStatus = "Recording off"; return; }
            var previousClaims = GymData.copy(model.data["recordings"]);
            model.claimRecording(id);
            if (!persist()) { model.data["recordings"] = previousClaims; return; }
            try {
                recording = ActivityRecording.createSession({:name=>"openGym", :sport=>Activity.SPORT_TRAINING, :subSport=>Activity.SUB_SPORT_STRENGTH_TRAINING});
                recordingWid = id;
                if (!recording.start()) { recording = null; recordingStatus = "Recording failed"; return; }
                enableTouch();
                recordingStatus = "Recording FIT";
            } catch (ex) { recording = null; recordingStatus = "Recording unavailable"; return; }
        }
        try {
            if (model.paused() && recording.isRecording()) { recording.stop(); }
            else if (!model.paused() && !recording.isRecording()) { recording.start(); enableTouch(); }
            recordingStatus = model.paused() ? "Recording paused" : "Recording FIT";
        } catch (ex) { recordingStatus = "Recording error"; }
    }
    function completeRecording(discard) {
        if (recording == null) { return; }
        var claim = recordingClaim(recordingWid);
        // Claim the terminal side effect durably before calling Garmin. A power
        // loss in this window is reported as interrupted, never retried blindly.
        if (claim != null) { claim["phase"] = discard ? "discarding" : "saving"; }
        if (!persist()) { recordingStatus = "Save pending: storage error"; return; }
        var session = recording;
        recording = null;
        recordingWid = null;
        try {
            if (session.isRecording()) { session.stop(); }
            var ok = discard ? session.discard() : session.save();
            recordingStatus = ok ? (discard ? "FIT discarded" : "FIT saved") : "FIT completion failed";
            if (claim != null) { claim["phase"] = ok ? "ended" : "interrupted"; }
        } catch (ex) { recordingStatus = "FIT completion interrupted"; if (claim != null) { claim["phase"] = "interrupted"; } }
        persist();
    }
    function onStop(state) as Void {
        if (tickTimer != null) { tickTimer.stop(); }
        Sensor.enableSensorEvents(null);
        Sensor.setEnabledSensors([]);
        persist();
        // Save the partial recording on deliberate app exit. Workout and pending
        // events survive; subsequent launches visibly report interruption.
        completeRecording(false);
    }
}

class GymConnectionListener extends Communications.ConnectionListener {
    var app;
    function initialize(owner) { ConnectionListener.initialize(); app = owner; }
    function onComplete() as Void { app.busy = false; }
    function onError() as Void { app.busy = false; }
}
