package ch.duartesantos.opengym;

import android.app.Notification;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;

/**
 * One foreground card for the active workout. During a timer the system runs its Chronometer;
 * only the visible progress bar needs per-second updates (RestCountdownPlan). Rest timers keep
 * the in-app pause/−15s/+15s/skip controls; a timed work set has no rest controls.
 */
public class RestTimerService extends Service {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private long endsAt;
    private long totalMs;
    private long pausedLeft;
    private boolean paused;
    private boolean running;
    private int lastStartId;
    private boolean workoutActive;
    private String wid = "";
    private String workoutTitle = "openGym";
    private String exercise = "";
    private String detail = "";
    private int done;
    private int total;
    private String timerTitle = "Rest";
    private String timerKey = "";
    private boolean controls = true;
    private SharedPreferences saved;
    private String pauseLabel = "Pause";
    private String resumeLabel = "Resume";
    private String minusLabel = "\u2212 15s";
    private String plusLabel = "+ 15s";
    private String skipLabel = "Skip";
    private int accent = 0xFF30D158;
    private int ink = 0xFF000000;
    private PowerManager.WakeLock cpu;
    private PowerManager power;
    private BroadcastReceiver screenOn;
    private final Runnable tick = new Runnable() {
        @Override
        public void run() {
            if (!running || paused || endsAt <= 0) return;
            long left = endsAt - System.currentTimeMillis();
            if (left <= 0) {
                reachEnd();
                return;
            }
            // Screen off: nobody sees the card, and the Chronometer keeps the clock right anyway.
            // Turning the screen on runs this loop at once (screenOn), so the bar catches up.
            boolean interactive = interactive();
            if (interactive) show();
            handler.postDelayed(this, RestCountdownPlan.nextTickMs(left, interactive));
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        saved = getSharedPreferences("workout-notification", MODE_PRIVATE);
        restore();
        RestAlert.restoreSettings(this);
        // Remove a completion banner left by an older app shell; ID 41 owns this session.
        ((android.app.NotificationManager) getSystemService(NOTIFICATION_SERVICE)).cancel(RestAlert.NOTIFICATION_ID);
        power = (PowerManager) getSystemService(POWER_SERVICE);
        screenOn = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                if (!running || paused) return;
                handler.removeCallbacks(tick);
                tick.run();
            }
        };
        try {
            IntentFilter f = new IntentFilter(Intent.ACTION_SCREEN_ON);
            if (Build.VERSION.SDK_INT >= 33) registerReceiver(screenOn, f, Context.RECEIVER_NOT_EXPORTED);
            else registerReceiver(screenOn, f);
        } catch (Exception e) {
            screenOn = null;
        }
    }

    private boolean interactive() {
        try {
            return power == null || power.isInteractive();
        } catch (Exception e) {
            return true;
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        lastStartId = startId;
        String action = intent == null ? null : intent.getAction();
        if (RestAlert.ACTION_RESTORE.equals(action)) {
            if (!wid.equals(text(intent, "wid", "")) || !timerKey.equals(text(intent, "timerKey", ""))) {
                showOrStop();
                return restartMode();
            }
            if (running && !paused && endsAt <= System.currentTimeMillis()) clearTimer();
            if (intent.getBooleanExtra("restoreRest", true)) {
                if (running && controls) emit(paused ? "pause" : "adjust");
                else RestAlertPlugin.emit("skip", 0, 0, 0, false, timerKey, wid);
            }
            if (running && !paused) { holdCpuUntilEnd(); handler.removeCallbacks(tick); tick.run(); }
            persist();
            showOrStop();
            return restartMode();
        }
        if (intent == null) {
            // START_STICKY does not redeliver the last command (which may have been Pause).
            // Recover the resulting state instead; a paused timer never restarts its clock.
            if (running && !paused && endsAt > System.currentTimeMillis()) {
                holdCpuUntilEnd();
                tick.run();
            } else if (running && !paused) {
                running = false;
                persist();
            }
            showOrStop();
            return restartMode();
        }
        if (RestAlert.ACTION_WORKOUT.equals(action)) {
            boolean active = intent.getBooleanExtra("active", false);
            String nextWid = text(intent, "wid", "");
            boolean sameWorkout = workoutActive && wid.equals(nextWid);
            // A different session must not inherit a paused timer from the preceding workout.
            if (!active || (workoutActive && !wid.equals(nextWid))) clearTimer();
            workoutActive = active;
            wid = nextWid;
            workoutTitle = text(intent, "workoutTitle", "openGym");
            exercise = text(intent, "exercise", "");
            detail = text(intent, "detail", "");
            done = intent.getIntExtra("done", 0);
            total = intent.getIntExtra("total", 0);
            accent = intent.getIntExtra("accent", accent);
            ink = intent.getIntExtra("ink", ink);
            persist();
            showOrStop();
            if (active && sameWorkout && timerKey.equals(text(intent, "timerKey", "")) && intent.getBooleanExtra("reconcile", false)) {
                if (running && controls) emit(paused ? "pause" : "adjust");
                else if (!running && intent.getBooleanExtra("hasRest", false)) RestAlertPlugin.emit("skip", 0, 0, 0, false, timerKey, wid);
            }
            return restartMode();
        }
        if (RestAlert.ACTION_CLEAR.equals(action) || RestAlert.ACTION_COMPLETE.equals(action)) {
            // The tone runs off-thread: an old end finishing after a new rest started must
            // not take the new timer down. CLEAR is the explicit Skip/stop from the page.
            if (RestAlert.ACTION_CLEAR.equals(action)
                    || (!paused && endsAt == intent.getLongExtra("endsAt", -1))) clearTimer();
            persist();
            showOrStop();
            return restartMode();
        }
        if (RestAlert.ACTION_ACCENT.equals(action)) {
            if (!running && !workoutActive) {
                // Only this start: a countdown asked for right behind it must still come up.
                stopSelf(startId);
                return START_NOT_STICKY;
            }
            accent = intent.getIntExtra("accent", accent);
            ink = intent.getIntExtra("ink", ink);
            RestAlert.setAccentColor(accent, ink);
            persist();
            show();
            return restartMode();
        }
        if (RestAlert.ACTION_HOLD.equals(action)) {
            if (!running && intent.getLongExtra("leftMs", 0) > 0) {
                running = true;
                controls = true;
                timerKey = text(intent, "timerKey", "");
            }
            if (running) hold(intent.getLongExtra("leftMs", 0), intent.getLongExtra("totalMs", 0));
            else showOrStop();
            return restartMode();
        }
        if (RestAlert.ACTION_SKIP.equals(action)) {
            finishSkip();
            return restartMode();
        }
        if (RestAlert.ACTION_PAUSE.equals(action)) {
            if (running && controls) togglePause();
            return restartMode();
        }
        if (RestAlert.ACTION_MINUS.equals(action)) {
            if (running && controls) nudge(-15_000);
            return restartMode();
        }
        if (RestAlert.ACTION_PLUS.equals(action)) {
            if (running && controls) nudge(15_000);
            return restartMode();
        }
        long nextEnd = intent == null ? 0 : intent.getLongExtra("endsAt", 0);
        if (nextEnd <= System.currentTimeMillis()) {
            showOrStop();
            return restartMode();
        }
        endsAt = nextEnd;
        long passed = intent.getLongExtra("totalMs", 0);
        totalMs = passed > 0 ? passed : Math.max(1000, endsAt - System.currentTimeMillis());
        paused = false;
        running = true;
        timerTitle = text(intent, "title", "Rest");
        controls = intent.getBooleanExtra("controls", true);
        timerKey = text(intent, "timerKey", "");
        holdCpuUntilEnd();
        pauseLabel = text(intent, "pause", pauseLabel);
        resumeLabel = text(intent, "resume", resumeLabel);
        minusLabel = text(intent, "minus", minusLabel);
        plusLabel = text(intent, "plus", plusLabel);
        skipLabel = text(intent, "skip", skipLabel);
        if (intent != null && intent.hasExtra("accent")) accent = intent.getIntExtra("accent", accent);
        if (intent != null && intent.hasExtra("ink")) ink = intent.getIntExtra("ink", ink);
        persist();
        handler.removeCallbacks(tick);
        tick.run();
        // A foreground service must post its card now, whether or not the screen is on.
        if (running && !interactive()) show();
        return restartMode();
    }

    @Override
    public void onDestroy() {
        running = false;
        handler.removeCallbacks(tick);
        releaseCpu();
        if (screenOn != null) {
            try { unregisterReceiver(screenOn); } catch (Exception ignored) { /* not registered */ }
            screenOn = null;
        }
        endsAt = 0;
        stopForegroundCompat();
        super.onDestroy();
    }

    private void togglePause() {
        if (!paused) {
            pausedLeft = Math.max(0, endsAt - System.currentTimeMillis());
            paused = true;
            handler.removeCallbacks(tick);
            releaseCpu();
            RestAlert.cancelAlarmOnly(this, RestAlert.NOTIFICATION_ID);
            RestAlert.clearChain(this, endsAt);
        } else {
            endsAt = System.currentTimeMillis() + pausedLeft;
            paused = false;
            holdCpuUntilEnd();
            RestAlert.updateAlarm(this, endsAt);
            handler.removeCallbacks(tick);
            tick.run();
        }
        show();
        persist();
        emit("pause");
    }

    /**
     * Paused in the app. The clock stops at the time the app holds, so the two read the same,
     * and the button offers Resume. No event goes back: the app made this change. The plugin
     * has already called off the alarm.
     */
    private void hold(long leftMs, long total) {
        if (leftMs <= 0) return;
        RestAlert.clearChain(this, endsAt);
        paused = true;
        pausedLeft = leftMs;
        if (total > 0) totalMs = total;
        handler.removeCallbacks(tick);
        releaseCpu();
        persist();
        show();
    }

    private void nudge(long deltaMs) {
        long now = System.currentTimeMillis();
        // endsAt may already be in the past when +15 lands on the last second.
        // Adding the delta to that old deadline would leave the clock stuck.
        long left = paused ? pausedLeft : Math.max(0, endsAt - now);
        left += deltaMs;
        if (left > totalMs) totalMs = left;
        if (left <= 0) {
            finishSkip();
            return;
        }
        if (paused) pausedLeft = left;
        else {
            endsAt = now + left;
            holdCpuUntilEnd();
            RestAlert.updateAlarm(this, endsAt);
            handler.removeCallbacks(tick);
            handler.post(tick);
        }
        show();
        persist();
        emit("adjust");
    }

    /**
     * The countdown reached its end. Keep the CPU until RestAlert takes its own short tone
     * lock. It then returns this same card to workout state, retaining foreground priority.
     */
    private void reachEnd() {
        running = false;
        holdCpuBriefly();
        RestAlert.fireFromCountdown(getApplicationContext(), endsAt, !controls);
    }

    /**
     * With exact alarms allowed, the alarm wakes the phone at the end (also in Doze) and
     * RestAlert.fire holds the CPU for the alert, so the rest itself holds nothing. Without
     * them the alarm may come most of a rest late: then the CPU is kept running until the end,
     * and ten seconds past it, so this countdown sounds the end on time with the screen off.
     * Released on pause, on skip and when the service stops after the end.
     */
    private void holdCpuUntilEnd() {
        long hold = RestCountdownPlan.cpuHoldMs(
                RestAlert.exactAllowed(this), endsAt - System.currentTimeMillis());
        if (hold <= 0) {
            releaseCpu();
            return;
        }
        try {
            if (cpu == null) {
                PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
                cpu = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "opengym:rest-countdown");
                cpu.setReferenceCounted(false);
            }
            cpu.acquire(hold);
        } catch (Exception ignored) { /* the alarm is still set */ }
    }

    private void holdCpuBriefly() {
        try {
            if (cpu == null) {
                PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
                cpu = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "opengym:rest-countdown");
                cpu.setReferenceCounted(false);
            }
            if (!cpu.isHeld()) cpu.acquire(RestCountdownPlan.END_GRACE_MS);
        } catch (Exception ignored) { /* the alert takes its own */ }
    }

    private void releaseCpu() {
        try {
            if (cpu != null && cpu.isHeld()) cpu.release();
        } catch (Exception ignored) { /* already released by its timeout */ }
    }

    private void finishSkip() {
        if (!controls) return;
        boolean chained = RestAlert.hasCues();
        long now = System.currentTimeMillis();
        clearTimer();
        RestAlertPlugin.emit("skip", now, 0, 0, false, timerKey, wid);
        if (chained) RestAlert.fireFromCountdown(getApplicationContext(), now, false);
        persist();
        showOrStop();
    }

    private void emit(String type) {
        long left = paused ? pausedLeft : Math.max(0, endsAt - System.currentTimeMillis());
        RestAlertPlugin.emit(type, endsAt, totalMs, left, paused, timerKey, wid);
    }

    private void show() {
        try {
            long left = paused ? pausedLeft : Math.max(0, endsAt - System.currentTimeMillis());
            Notification n = running ? RestAlert.countdownNotification(
                    this, left, totalMs, paused, pauseLabel, resumeLabel, minusLabel, plusLabel, skipLabel,
                    accent, ink, workoutActive ? workoutTitle + " · " + timerTitle : timerTitle, exercise, detail, controls)
                    : RestAlert.workoutNotification(this, workoutTitle, exercise, detail, done, total, accent);
            if (Build.VERSION.SDK_INT >= 34) {
                startForeground(RestAlert.COUNTDOWN_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
            } else {
                startForeground(RestAlert.COUNTDOWN_ID, n);
            }
        } catch (Exception e) {
            stopSelf(lastStartId);
        }
    }

    private int restartMode() { return workoutActive || running ? START_STICKY : START_NOT_STICKY; }

    /** A freshly restored page must adopt native Pause/±15/Skip, not overwrite them. */
    static boolean restoreTimer(Context context, String wid, String timerKey, boolean rest) {
        if (wid == null || wid.isEmpty() || timerKey == null || timerKey.isEmpty()) return false;
        Context app = context.getApplicationContext();
        try {
            String raw = app.getSharedPreferences("workout-notification", MODE_PRIVATE).getString("state", null);
            if (raw == null) return false;
            Intent state = Intent.parseUri(raw, 0);
            if (!state.getBooleanExtra("workoutActive", false) || !wid.equals(state.getStringExtra("wid"))) return false;
            // A newer rest may have reached JS storage before its bridge call ran. An old
            // native Skip belongs only to its own timer, never to that pending new rest.
            if (!timerKey.equals(state.getStringExtra("timerKey"))) return false;
            Intent i = new Intent(app, RestTimerService.class).setAction(RestAlert.ACTION_RESTORE);
            i.putExtra("restoreRest", rest);
            i.putExtra("wid", wid);
            i.putExtra("timerKey", timerKey);
            if (Build.VERSION.SDK_INT >= 26) app.startForegroundService(i);
            else app.startService(i);
            return true;
        } catch (Exception e) { return false; }
    }

    private void clearTimer() {
        RestAlert.clearChain(this, endsAt);
        running = false;
        paused = false;
        endsAt = 0;
        handler.removeCallbacks(tick);
        releaseCpu();
        RestAlert.cancelAlarmOnly(this, RestAlert.NOTIFICATION_ID);
    }

    private void showOrStop() {
        if (workoutActive || running) show();
        else { stopForegroundCompat(); stopSelf(lastStartId); }
    }

    private void persist() {
        if (!workoutActive && !running) { saved.edit().remove("state").apply(); return; }
        Intent state = new Intent();
        state.putExtra("workoutActive", workoutActive).putExtra("wid", wid)
                .putExtra("workoutTitle", workoutTitle).putExtra("exercise", exercise).putExtra("detail", detail)
                .putExtra("done", done).putExtra("total", total).putExtra("accent", accent).putExtra("ink", ink)
                .putExtra("running", running).putExtra("paused", paused).putExtra("endsAt", endsAt)
                .putExtra("pausedLeft", pausedLeft).putExtra("totalMs", totalMs).putExtra("timerTitle", timerTitle)
                .putExtra("timerKey", timerKey).putExtra("controls", controls).putExtra("pause", pauseLabel).putExtra("resume", resumeLabel)
                .putExtra("minus", minusLabel).putExtra("plus", plusLabel).putExtra("skip", skipLabel);
        saved.edit().putString("state", state.toUri(0)).apply();
    }

    private void restore() {
        try {
            String raw = saved.getString("state", null);
            if (raw == null) return;
            Intent state = Intent.parseUri(raw, 0);
            workoutActive = state.getBooleanExtra("workoutActive", false);
            wid = text(state, "wid", "");
            workoutTitle = text(state, "workoutTitle", workoutTitle);
            exercise = text(state, "exercise", "");
            detail = text(state, "detail", "");
            done = state.getIntExtra("done", 0);
            total = state.getIntExtra("total", 0);
            accent = state.getIntExtra("accent", accent);
            ink = state.getIntExtra("ink", ink);
            running = state.getBooleanExtra("running", false);
            paused = state.getBooleanExtra("paused", false);
            endsAt = state.getLongExtra("endsAt", 0);
            pausedLeft = state.getLongExtra("pausedLeft", 0);
            totalMs = state.getLongExtra("totalMs", 0);
            timerTitle = text(state, "timerTitle", timerTitle);
            controls = state.getBooleanExtra("controls", true);
            timerKey = text(state, "timerKey", "");
            pauseLabel = text(state, "pause", pauseLabel);
            resumeLabel = text(state, "resume", resumeLabel);
            minusLabel = text(state, "minus", minusLabel);
            plusLabel = text(state, "plus", plusLabel);
            skipLabel = text(state, "skip", skipLabel);
        } catch (Exception e) {
            android.util.Log.w("openGym", "workout notification state could not be restored", e);
        }
    }

    private static String text(Intent intent, String key, String fallback) {
        if (intent == null) return fallback;
        String v = intent.getStringExtra(key);
        return v == null || v.isEmpty() ? fallback : v;
    }

    @SuppressWarnings("deprecation")
    private void stopForegroundCompat() {
        if (Build.VERSION.SDK_INT >= 24) stopForeground(STOP_FOREGROUND_REMOVE);
        else stopForeground(true);
    }
}
