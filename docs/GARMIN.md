# Garmin tactix 8 companion

This fork adds a local Android/Connect IQ companion. Deployment of an openGym server is optional and is not part of installing this integration.

## What it does

- The phone sends the active session: exercise names, planned weight/repetitions, sets, current exercise and rest timer.
- The watch displays the session, records heart rate, completes sets and selects the next exercise. Its menu offers pause/resume, skip rest and confirmed finish/discard.
- Watch commands are stored locally until the phone applies and durably saves them. Repeated messages do not toggle a completed set off. Older snapshots cannot undo acknowledged commands.
- The watch records a native FIT activity with the sensor stream. Garmin Connect's usual sync uploads it; an independently linked Strava account receives it through Garmin's existing integration, without an openGym Strava API application or subscription requirement. This Connect IQ recording currently supplies the activity summary and heart rate, not the standard strength set messages produced by Garmin's built-in Strength app.

Garmin Connect Mobile must be installed and paired with the watch. The Android companion SDK uses it to exchange messages with our Connect IQ app. Internet is not needed to continue a session already received by the watch. When Android suspends its WebView, the watch continues locally and the phone applies queued actions when openGym resumes. Instant phone-screen updates while Android is asleep are not promised.

## Install without replacing the original app

The Garmin Android flavor uses a separate application ID (`ch.duartesantos.opengym.garmin` for release, with `.test` appended for debug) and the label **openGym Garmin**. It does not install upstream APK updates over this fork. The original openGym and its data remain separate.

1. In the original app, export a backup using **Settings → Data & backup → Export backup**. Keep it on the phone or another private destination. Do not add it to the source repository, attach it to a public issue, or upload it to GitHub.
2. Install the locally built Garmin APK. Import the backup into the new app using its backup screen. Import replaces the new app's profile, so do it before logging new sessions there.
3. Install the matching signed Connect IQ `.prg` on the watch through Garmin's development sideload procedure. The AMOLED target is `fenix847mm` (both tactix 8 sizes), and Solar 51 mm is `fenix8solar51mm`. The fixed companion UUID is `6fcd6528636d4cc39c3ad1e317d7524a`.
4. Open Garmin Connect Mobile and confirm the watch is paired and connected.
5. In **openGym Garmin → Settings → Garmin**, refresh devices, select the watch, and press **Connect**. Open the companion on the watch. The link is disabled until explicitly configured.
6. Start a workout on the phone. Keep the watch app running while training. Use START to complete a rep set (or start/complete a timed set), DOWN for the next exercise, and MENU/BACK for the other actions.

For detailed strength sets, openGym also offers **Export for Strava (.fit)** on a completed workout. It uses standard FIT set messages for repetitions, durations and recognized exercise categories. **Settings → Data & backup → Include weights in Strava exports** is off by default. This choice omits weight fields from that export; it does not remove weights from the private openGym log, the watch display, the separate Garmin export, or activities uploaded independently by another app/device. The detailed export contains no fabricated HR stream. The current Connect IQ sensor recording and the phone's detailed set export are separate files; automatic merging of those files into one cloud activity is not implemented.

Choose one upload source per workout to avoid duplicate activities. If Garmin has already forwarded the recorded activity to Strava, do not upload the detailed FIT again as though it were a second workout. A direct automated openGym-to-Strava API client would require the owner's Strava developer application and its current subscription prerequisite; it is not silently substituted for the free Garmin route.

On Android, a paused Garmin workout can also be resumed from its status row on the phone. The current HR display expires when samples stop arriving; it never presents an old value as a live reading.

## Built-in Strength alternative

The current install is a separate watch app. A Connect IQ **data field** can instead run inside
Garmin's built-in Strength activity. This is a different app type and is not enabled by this build.
The official API supports displaying phone-provided data, receiving native timer/lap/workout
callbacks and supplying a workout through `DataField.setWorkout`.

On tactix 8 profiles supporting Connect IQ 6.0.3, `Application.DynamicResource.build` can import
persisted FIT workout bytes locally. Such a plan can represent exercise categories and repetition
targets, whereas the in-memory `WorkoutStepInfo` form accepts only time/distance durations. A
local phone-to-watch plan transfer therefore does not inherently require an HTTP or Node server.
The owner's installed watch firmware must also support these APIs.

This is not equivalent to full remote control of the native activity. Public data-field APIs do
not expose commands to advance a native strength set, pause its timer, save or discard its recording.
Native lap triggers include rep-counting and set-stop events, but their ordering and relationship
to a completed set require physical-device verification before mapping them to openGym commands.
Timer reset alone cannot distinguish save from discard. The simulator does not reproduce Garmin's
built-in Strength activity.

Only Garmin controls the native activity's recorded weights. Omitting weights from an imported
plan does not establish that Garmin will omit remembered or manually entered weights from its
final recording or cloud upload. The openGym Strava-export preference cannot filter that route.
Native Strength FIT details and their appearance in Strava therefore remain separate physical
acceptance criteria. Compiler acceptance of a data-field probe is not evidence of that behavior.

Primary references: [DataField](https://developer.garmin.com/connect-iq/api-docs/Toybox/WatchUi/DataField.html),
[DynamicResource](https://developer.garmin.com/connect-iq/api-docs/Toybox/Application/DynamicResource.html),
[WorkoutStepInfo](https://developer.garmin.com/connect-iq/api-docs/Toybox/Activity/WorkoutStepInfo.html).

## Build locally

Use the existing frontend lockfile, JDK 21 and Android SDK platform/build-tools 36. The native bridge uses `com.garmin.connectiq:ciq-companion-app-sdk:2.4.0` from Maven Central.

```sh
cd frontend
npm ci
VITE_MOBILE=1 npx vite build
node ../scripts/catalogue/stage-media.mjs dist
npx cap sync android
node scripts/check-mobile-bundle.mjs
cd android
./gradlew -Pgarmin=true testGarminDebugUnitTest assembleGarminDebug
```

The debug APK is signed with Android's local debug key and installs separately. Retain the signing key for future updates of that installation; using a different key requires a separate installation or uninstall/reimport. Release signing is a later owner-controlled step. No private signing material is committed.

For watch setup, compilation and simulator tests, follow [the companion build guide](../garmin/README.md). The build script writes SDKs/keys to ignored `.local/garmin/` and outputs to ignored `artifacts/garmin-companion/`. Garmin device packages must be installed in SDK Manager; the SDK archive alone is insufficient. Preserve the local watch signing key for future updates.

## Privacy and storage

The public repository contains source, documentation and synthetic test fixtures. Runtime data, personal exports, SDK login state, keys and local verification artifacts do not belong in Git. The integration contains no HTTP client or health-service credential exchange.

Android stores connection selection, snapshots, unacknowledged commands and acknowledgement fences in app-private **no-backup** storage. The watch keeps its active session and outbox in its own application storage. Only allowlisted active-session fields cross the Bluetooth boundary; past workout history, account identifiers, credentials and media are excluded. Changing accounts disables the link so the next profile must connect deliberately.

User-enabled server sync, Health Connect, Garmin Connect cloud upload and Garmin–Strava sync remain separate choices. A public source repository does not make the phone's local workout database public.

## Limits and physical acceptance

- Drop sets, rest-pause sets, cardio/distance rows and unsupported timed side rows must be completed on the phone. The watch refuses these rather than inventing repetitions. Ordinary per-side rep sets are supported.
- Workout messages are bounded to 12 KiB, with space reserved for acknowledgements. Oversized sessions produce an error instead of losing sets. The watch's bounded outbox refuses further commands when full and retains existing work.
- Exiting the watch app saves a partial FIT. After a watch app restart/reboot, the session and outbox recover, but Garmin does not expose a public API to reconnect to an earlier in-memory recording session. The watch shows **Recording interrupted** and avoids starting a duplicate recent recording. Reboot-proof uninterrupted FIT recording is not claimed.
- No automatic rep detection, proprietary Training Effect, training-load or recovery calculations are promised. Standard Garmin and Strava displays may contain less detail than openGym's log.

Local compiler, JVM, frontend, browser and simulator checks do not prove physical Bluetooth/sensor/cloud behavior. On the owner's tactix 8, validate a short session with the phone locked, a Bluetooth disconnect/reconnect, completion of a set while offline, pause/resume, and finish. Check one activity in Garmin Connect and one in Strava, with no duplicate activity or missing openGym set. Keep these results and health exports private.

## Hosting later

The existing Node API, file-based data storage and Docker deployment are preserved. This change does not migrate them to Cloudflare Workers/D1, create infrastructure, or deploy anything. The watch link works in standalone phone mode; hosting can be decided independently after physical validation.
