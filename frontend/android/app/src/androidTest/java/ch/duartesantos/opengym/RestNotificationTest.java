package ch.duartesantos.opengym;

import static org.junit.Assert.*;
import static org.junit.Assume.assumeTrue;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.provider.Settings;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;

/** Runs against Android's real notification builder, not the JVM's android.jar stubs. */
public class RestNotificationTest {
    // The platform constant is SDK 36.1; the documented extra also works on SDK 36.
    private static final String REQUEST_PROMOTED = "android.requestPromotedOngoing";
    private final Context ctx = InstrumentationRegistry.getInstrumentation().getTargetContext();

    private Notification countdown(boolean paused, boolean controls) {
        return RestAlert.countdownNotification(ctx, 90_000, 120_000, paused,
                "Pause", "Resume", "− 15s", "+ 15s", "Skip", 0xff30d158, 0xff000000,
                "Workout · Rest", "Squat", "3 × 5", controls);
    }

    private void assertOngoing(Notification n) {
        assertNotEquals(0, n.flags & Notification.FLAG_ONGOING_EVENT);
        assertNotEquals(0, n.flags & Notification.FLAG_ONLY_ALERT_ONCE);
        assertNotEquals(0, n.flags & Notification.FLAG_LOCAL_ONLY);
        assertEquals(Notification.CATEGORY_PROGRESS, n.category);
        assertEquals(RestAlert.COUNTDOWN_CHANNEL_ID, n.getChannelId());
        assertFalse(n.extras.getBoolean(Notification.EXTRA_COLORIZED));
        assertNull(n.sound);
        assertNull(n.vibrate);
    }

    private void assertPromotable(Notification n) {
        assertOngoing(n);
        assertTrue(n.extras.getBoolean(REQUEST_PROMOTED));
        assertNull(n.contentView);
        assertNull(n.bigContentView);
        assertTrue(n.hasPromotableCharacteristics());
    }

    @Test
    public void activeWorkoutAndRunningCountdownQualifyForPromotionOnAndroid16() {
        assumeTrue(Build.VERSION.SDK_INT >= 36);
        Notification workout = RestAlert.workoutNotification(ctx, "Workout", "Squat", "3 × 5", 2, 10, 0xff30d158);
        assertPromotable(workout);
        assertEquals(2, workout.extras.getInt(Notification.EXTRA_PROGRESS));
        long before = System.currentTimeMillis();
        Notification timer = countdown(false, true);
        assertPromotable(timer);
        assertTrue(timer.extras.getBoolean(Notification.EXTRA_SHOW_CHRONOMETER));
        assertTrue(timer.extras.getBoolean(Notification.EXTRA_CHRONOMETER_COUNT_DOWN));
        assertTrue(timer.when >= before + 90_999);
        assertTrue(timer.when <= System.currentTimeMillis() + 90_999);
        assertEquals(90, timer.extras.getInt(Notification.EXTRA_PROGRESS));
        assertEquals("Pause", timer.actions[0].title);
        assertEquals("Skip", timer.actions[1].title);
        assertTrue(timer.actions[timer.actions.length - 1].actionIntent.isActivity());
    }

    @Test
    public void pausedCountdownHoldsTimeAndOffersResumeWithoutAClockThatKeepsRunning() {
        assumeTrue(Build.VERSION.SDK_INT >= 36);
        Notification timer = countdown(true, true);
        assertPromotable(timer);
        assertFalse(timer.extras.getBoolean(Notification.EXTRA_SHOW_CHRONOMETER));
        assertEquals("1:30", timer.extras.getCharSequence(Notification.EXTRA_TEXT).toString());
        assertTrue(timer.extras.getCharSequence(Notification.EXTRA_BIG_TEXT).toString().startsWith("1:30\n"));
        assertEquals("Resume", timer.actions[0].title);
        assertEquals("Skip", timer.actions[1].title);
    }

    @Test
    public void timedWorkDoesNotAcquireRestControls() {
        assumeTrue(Build.VERSION.SDK_INT >= 36);
        Notification timer = countdown(false, false);
        assertPromotable(timer);
        assertEquals(1, timer.actions.length);
        assertTrue(timer.actions[0].actionIntent.isActivity());
    }

    @Test
    public void olderAndroidKeepsTheCustomCountdownAndDoesNotRequestPromotion() {
        assumeTrue(Build.VERSION.SDK_INT >= 26 && Build.VERSION.SDK_INT < 36);
        Notification timer = countdown(false, true);
        assertOngoing(timer);
        assertNotNull(timer.contentView);
        assertNotNull(timer.bigContentView);
        assertFalse(timer.extras.getBoolean(REQUEST_PROMOTED));
        assertEquals(1, timer.actions.length);
    }

    @Test
    public void buildingCardsPreservesExistingChannelPreferences() {
        assumeTrue(Build.VERSION.SDK_INT >= 26);
        NotificationManager nm = ctx.getSystemService(NotificationManager.class);
        // Create the channel through the production path, then compare all alert preferences.
        countdown(false, true);
        NotificationChannel before = nm.getNotificationChannel(RestAlert.COUNTDOWN_CHANNEL_ID);
        countdown(true, true);
        RestAlert.workoutNotification(ctx, "Workout", "Squat", "", 0, 1, 0xff30d158);
        NotificationChannel after = nm.getNotificationChannel(RestAlert.COUNTDOWN_CHANNEL_ID);
        assertEquals(before.getImportance(), after.getImportance());
        assertEquals(before.getSound(), after.getSound());
        assertEquals(before.shouldVibrate(), after.shouldVibrate());
        assertArrayEquals(before.getVibrationPattern(), after.getVibrationPattern());
        assertEquals(before.canBypassDnd(), after.canBypassDnd());
    }

    @Test
    public void settingsPreferBlockedPromotionOtherwiseTheWorkoutChannel() {
        assumeTrue(Build.VERSION.SDK_INT >= 36);
        Intent promotion = RestAlert.notificationSettingsIntent(ctx, true, intent -> true);
        assertEquals(Settings.ACTION_APP_NOTIFICATION_PROMOTION_SETTINGS, promotion.getAction());
        assertEquals(ctx.getPackageName(), promotion.getStringExtra(Settings.EXTRA_APP_PACKAGE));
        Intent channel = RestAlert.notificationSettingsIntent(ctx, false, intent -> true);
        assertEquals(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS, channel.getAction());
        assertEquals(RestAlert.COUNTDOWN_CHANNEL_ID, channel.getStringExtra(Settings.EXTRA_CHANNEL_ID));
        assertEquals(ctx.getPackageName(), channel.getStringExtra(Settings.EXTRA_APP_PACKAGE));
        assertNotEquals(0, channel.getFlags() & Intent.FLAG_ACTIVITY_NEW_TASK);
    }

    @Test
    public void settingsFallBackWhenAnOemOmitsScreensAndHandleNoSettingsActivity() {
        assumeTrue(Build.VERSION.SDK_INT >= 26);
        for (String action : new String[] { Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS,
                Settings.ACTION_APP_NOTIFICATION_SETTINGS, Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Settings.ACTION_SETTINGS }) {
            Intent intent = RestAlert.notificationSettingsIntent(ctx, true, candidate -> action.equals(candidate.getAction()));
            assertEquals(action, intent.getAction());
            if (Settings.ACTION_APPLICATION_DETAILS_SETTINGS.equals(action)) {
                assertEquals("package:" + ctx.getPackageName(), intent.getDataString());
            }
        }
        assertNull(RestAlert.notificationSettingsIntent(ctx, true, intent -> false));
    }
}
