# Garmin tactix 8 companion

This fork adds a local Android/Connect IQ companion and optional direct Android uploads to Garmin Connect. Neither requires an openGym server.

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
3. Use **Settings → Garmin → Install on the watch** to open the [owner-only Connect IQ beta](https://apps.garmin.com/apps/10ea70db-ee8f-4811-9b65-ec251468afae) under the same Garmin account that uploaded it. Installation remains controlled by Garmin. Development sideload of the matching signed `.prg` is also possible. The AMOLED target is `fenix847mm` (both tactix 8 sizes), and Solar 51 mm is `fenix8solar51mm`. The fixed companion UUID is `6fcd6528636d4cc39c3ad1e317d7524a`; the store UUID is separate.
4. Open Garmin Connect Mobile and confirm the watch is paired and connected.
5. In **openGym Garmin → Settings → Garmin**, refresh devices, select the watch, and press **Connect**. Open the companion on the watch. The link is disabled until explicitly configured.
6. Start a workout on the phone. With the companion linked, Android automatically requests that Garmin open it; the watch may require confirmation. Restoring an existing session or opening history does not request a launch. Keep the watch app running while training. Use the on-screen buttons or START to complete a rep set (or start/complete a timed set), DOWN for the next exercise, and MENU/BACK for the other actions.

For updates of an already installed **openGym Garmin**, install the APK over that same app with the same application ID and signing key. Do not uninstall, clear storage or import an old backup as part of an update; those actions can remove newer local workouts.

## Direct Android upload to Garmin Connect

In **Settings → Garmin → Garmin Connect uploads**, sign in on Garmin's own page, including any MFA challenge. The browser session on a desktop is separate from the Android app's login. The password is not passed to openGym JavaScript or stored by this integration. Android captures the resulting Garmin session natively and encrypts it with AndroidKeyStore in app-private no-backup storage. WebView authentication storage is excluded from Android cloud backup and device transfer.

Enable **Upload new workouts automatically** between workouts. Completing a new workout queues its detailed FIT in the same saved state as the workout. While this mode is enabled, the companion still exchanges controls and live HR but does not start a separate native FIT recording. This avoids two upload sources for the same session. Changing this mode during a workout is disabled.

An existing completed workout also has **Upload to Garmin Connect**. Use it only for an activity that is not already in Connect. Importing a GymUp/openGym backup does not automatically publish historical workouts. A confirmed native receipt survives app restart and a lost JavaScript callback. An ambiguous network outcome is not retried automatically: check Connect before explicitly retrying, since Garmin may have accepted the original request.

Uploads contain standard FIT set messages with repetitions, durations and recognized exercise categories. **Settings → Data & backup → Include weights in Strava exports** is off by default and also governs these uploads. With it off, weight fields are absent from the uploaded FIT. Private openGym weights, the watch display and independently recorded Garmin activities retain their own data. Enabling weight sharing later cannot broaden an already queued upload; disabling it before transmission removes weights.

Real HR readings received by the phone from the watch are included as FIT records, capped at 7,200 samples. No missing Bluetooth or suspended-phone interval is interpolated. Separate watch-native recordings can retain a denser sensor stream; direct upload does not merge another activity's FIT file. No calories, GPS or Garmin proprietary physiological metrics are invented.

This uses Garmin's **unofficial** ordinary activity-upload endpoint, based on the maintained [python-garminconnect upload implementation](https://github.com/cyberjunky/python-garminconnect) and its [upload/import distinction](https://github.com/cyberjunky/python-garminconnect/issues/322). There is no Python or Node runtime dependency in the Android app. Garmin may change the endpoint or expire the login; reconnect when needed. Garmin's ordinary upload path can forward the activity to separately linked services such as Strava. The alternative import endpoint suppresses that forwarding and is deliberately not used. Actual acceptance, detail rendering and Strava forwarding still require an owner-account physical test.

The standalone **Export for Strava (.fit)** button remains available. It generates a file; Android sharing to Strava may open an ordinary post rather than import a workout. It is not the automatic upload route. A separate direct Strava API client is not required for the Garmin route.

On Android, a paused Garmin workout can also be resumed from its status row on the phone. The current HR display expires when samples stop arriving; it never presents an old value as a live reading.

## Read health data

For body weight and workout heart rate, the existing **Health Connect** integration is the simplest supported path. Garmin can write weight, body fat, sleep stages, steps, floors, heart rate and some activity data there after device sync. Garmin documents this as one-way: Health Connect cannot send openGym activities back to Garmin. See [Garmin Health Connect support](https://support.garmin.com/en-US/?faq=JToBEy0jfe6pIygark2Ui5). The existing openGym hub reader currently consumes weight and workout HR only.

The optional native direct reader has a fixed catalog of 56 health/wellness/performance categories. In **Settings → Garmin → Garmin health data**, choose a period of at most seven days per explicit batch. Reads run serially with progress and cancellation between requests; a request already in flight may take up to its deadline to stop. Authentication failure or rate limiting stops the batch. Missing or unsupported data remains unavailable; it is never replaced by zero. No background polling or account write is performed by health reads.

Raw safe responses, including dense arrays and original units, are saved with native Android `AtomicFile` replacement/recovery in a private per-profile/day/metric archive. Failed/empty later reads do not replace successful archived observations. The archive is separate from the normal workout JSON backup and is excluded from Android cloud Auto Backup to protect its size limit; device transfer retains it. Use **Export Garmin health data** for an explicit JSON export of the selected period, including when its final day has no data. Cancellation, disconnect or profile changes before sharing stop the export. Displayed details are a bounded overview; export retains the complete saved response. Current Garmin login material never enters that archive or export.

Date-range body-composition weight readings are converted from grams into the profile unit and rounded to tenths using the existing hub merge policy. Manually entered weights and deletion tombstones win. Source field-unit evidence: [weight dateRange reader](https://github.com/abrander/garmin-connect/blob/master/Weight.go) and [current protocol research](https://github.com/awronski/gconnect/blob/main/GARMIN_CONNECT_PROTOCOL.md#59-weight-and-body-composition). Body-water units are not inferred. Other proprietary metrics retain Garmin's original fields, values and units in the archive rather than inventing openGym equivalents. Account/device availability and real-response compatibility still require physical validation.

## Mixed weight units

Every workout load field has a **kg/lb** calculator. Enter a total in either unit, or select **Bar and plates** and enter the bar and combined plates on one side with independent kg/lb choices. The calculator counts both sides once and saves only the resulting total in the profile's configured unit. It never switches or converts the entire profile and does not change the logged number until Apply. Body-mass displays always round to tenths independently of the plate-weight decimal preference.

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

The public repository contains source, documentation and synthetic test fixtures. Runtime data, personal exports, SDK login state, keys and local verification artifacts do not belong in Git. The Bluetooth bridge has no cloud credentials. The optional Garmin Connect uploader makes fixed-host HTTPS requests using a native encrypted session; it never exposes the token to JavaScript, backups or logs.

Android stores connection selection, snapshots, unacknowledged commands and acknowledgement fences in app-private **no-backup** storage. The watch keeps its active session and outbox in its own application storage. Only allowlisted active-session fields cross the Bluetooth boundary; past workout history, account identifiers, credentials and media are excluded. Changing accounts disables the link so the next profile must connect deliberately.

Garmin upload is off until explicitly connected and enabled. Disconnect clears usable credentials but retains upload receipts. Reconnecting generates a new session; an old receipted workout is deliberately blocked from replay under the new generation. Changed FIT bytes cannot bypass the guard. The journal holds up to 512 receipts and does not evict them to permit duplicate replay; reaching capacity blocks further uploads pending explicit reconciliation. A live openGym profile change revokes the native connection; queued jobs are also bound to a random native session generation, so restoring a backup on another device does not authorize uploads. User-enabled server sync, Health Connect and Garmin–Strava linking remain separate choices. A public source repository does not make the phone's local workout database public.

## Limits and physical acceptance

- Drop sets, rest-pause sets, cardio/distance rows and unsupported timed side rows must be completed on the phone. The watch refuses these rather than inventing repetitions. Ordinary per-side rep sets are supported.
- Workout messages are bounded to 12 KiB, with space reserved for acknowledgements. Oversized sessions produce an error instead of losing sets. The watch's bounded outbox refuses further commands when full and retains existing work.
- Exiting the watch app saves a partial FIT. After a watch app restart/reboot, the session and outbox recover, but Garmin does not expose a public API to reconnect to an earlier in-memory recording session. The watch shows **Recording interrupted** and avoids starting a duplicate recent recording. Reboot-proof uninterrupted FIT recording is not claimed.
- No automatic rep detection, proprietary Training Effect, training-load or recovery calculations are promised. Standard Garmin and Strava displays may contain less detail than openGym's log.

Local compiler, JVM, frontend, browser and simulator checks do not prove physical Bluetooth/sensor/cloud behavior. On the owner's tactix 8, validate a short session with the phone locked, a Bluetooth disconnect/reconnect, completion of a set while offline, pause/resume, and finish. Check one activity in Garmin Connect and one in Strava, with no duplicate activity or missing openGym set. Keep these results and health exports private.

## Hosting later

The existing Node API, file-based data storage and Docker deployment are preserved. This change does not migrate them to Cloudflare Workers/D1, create infrastructure, or deploy anything. The watch link works in standalone phone mode; hosting can be decided independently after physical validation.
