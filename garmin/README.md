# openGym Connect IQ companion

Local companion for the Android openGym app, application UUID
`6fcd6528636d4cc39c3ad1e317d7524a`. Start the workout on the phone, enable its Garmin
link, and open this watch app. Garmin Connect Mobile transports dictionaries over
the paired link; the companion does not contact an openGym server or require Internet
to continue an already received workout.

## Devices and building

Garmin's SDK 9.3.0 device reference identifies these grouped targets:

| SDK target | Devices covered |
| --- | --- |
| `fenix847mm` | fēnix 8 / tactix 8 AMOLED, both 47 mm and 51 mm |
| `fenix8solar51mm` | fēnix 8 Solar / tactix 8 Solar, 51 mm |

There is no separate tactix 8 compiler target. These identifiers are taken from
the [official device reference](https://developer.garmin.com/connect-iq/device-reference/),
also bundled in SDK `doc/docs/Device_Reference/`. The 47 mm solar and 43 mm AMOLED
targets are intentionally outside this companion's device scope.

Requirements: Java, OpenSSL, the official Connect IQ SDK, and both device packages
installed with [Garmin SDK Manager](https://developer.garmin.com/connect-iq/sdk/).
On macOS the SDK can be downloaded locally with:

```sh
scripts/garmin-build.sh setup
```

Read the Garmin SDK license before using the SDK. SDK Manager may require the
owner to sign in to install device packages. Its usual device directory is
`~/Library/Application Support/Garmin/ConnectIQ/Devices`. The SDK archive alone
contains reference documentation but does not install the compiler device packages.
No account or credential belongs in this repository.

```sh
# Default SDK location: .local/garmin/sdk
# Optional: export CIQ_SDK_HOME=/absolute/path/to/your/connectiq-sdk
# Optional: export CIQ_SIGNING_KEY=/absolute/path/to/your/local/key.der
scripts/garmin-build.sh syntax
scripts/garmin-build.sh build all
scripts/garmin-build.sh test all
# One signed multi-device IQ package for an owner-account beta upload:
scripts/garmin-build.sh package
```

The script generates a local signing key when none was provided. Keep that key
private and retain it for future updates. Local SDK/license files and signing
material stay under ignored `.local/garmin/`; signed `.prg` files and check receipts
stay under ignored `artifacts/garmin-companion/`. It does not publish, release or
install the app on a physical watch. Copy the matching `.prg` to the owner's watch
using Garmin's normal development sideload procedure only when authorized.

For wireless installation, the owner may upload `opengym-garmin-beta.iq` through the Garmin developer dashboard with **This app is for testing purposes only** selected. Garmin states that only that account can install the beta. Accepting the developer agreement is the owner's decision. Open the beta's app link on the Android phone under the same Garmin account, then install through Connect IQ. This does not deploy an openGym server or publish the app for everyone. A later public release needs a distinct application ID and matching Android companion configuration.

`syntax` invokes Garmin's bundled grammar parser. It checks syntax only, and is
not a substitute for a successful device compile or simulator test. `test` compiles
the Monkey C tests and executes them in the official simulator. The simulator
opens a desktop window. A successful run must report zero failed tests.

For an offline UI smoke check, set simulator **Settings → Connection Type → BLE →
Not Connected**. With SDK 9.3.0 on macOS, the simulated connected phone state without
an actual companion blocked the native hello/transmit path during this integration's
UI check. Disconnected simulation ran the complete app, set completion, pause,
confirmation and FIT save successfully. This simulator result does not validate
the physical Bluetooth transport.

## Watch controls

- **START** completes the next unfinished set. For a timed set, the first press
  starts a local timer; the next press records actual elapsed seconds.
- **DOWN** selects the next exercise, using an absolute, retry-safe selection.
- **MENU** or **BACK** opens pause/resume, skip rest, next exercise, finish,
  discard, reconnect, and exit actions.
- **Finish & save** and **Discard workout** both require explicit confirmation.
  The confirmation is bound to that workout ID, so a changed phone workout cannot
  be accidentally ended by an old confirmation.
- Rest counts down from timestamps while disconnected. Pausing freezes rest and
  timed sets. A rest-complete vibration respects the phone's haptic setting.

Per-side rep sets tick L and R independently and show the side. Warmup rows retain
their label. The companion refuses rows marked `unsupported` (for example a drop
set or rest-pause set), cardio/distance modes, time-per-side sets without per-side
seconds, and missing rep targets. Use the phone for those sets; the watch never
fabricates a rep count. Exercise animations are not included.

## Durability and recording

The protocol is [GARMIN_PROTOCOL.md](../docs/dev/GARMIN_PROTOCOL.md). Events retain
their installation ID and monotonic counter across retry and restart. Transport
success never deletes an event. Only an acknowledgement containing the phone's
post-persistence snapshot sequence and state can remove it. New snapshots rebase
all remaining pending events. Old sequences, old workout IDs and recently ended
workout tombstones cannot undo pending completions or reopen finished workouts.

The outbox holds 96 commands, sends the first eight in order, and retries while
connected. At capacity it visibly refuses new commands and preserves queued work.
It does not silently discard events. An A/B journal writes pages below the 8 KiB
Garmin storage-value limit before switching its root. Failed writes roll back
visible commands before FIT or transport side effects. An incomplete journal
write leaves the previous root readable. HR aggregates are checkpointed every
15 seconds and on commands; a sudden power loss can lose the last 15 seconds of
uncommitted samples, but not an already committed set completion.

Current HR is transient and sent at most once per five seconds, with durable
average/max HR attached to completed sets. Rest HR is not currently collected.
Keep the app running for live HR; arbitrary Connect IQ execution after exiting
the watch app is not promised.

The watch records a native FIT strength-training activity, pauses its recording
timer on pause, and saves/discards on confirmed completion. Exiting deliberately
saves a partial FIT. A durable per-workout claim prevents starting a second FIT
for the same workout after an app restart or reboot. Garmin provides no public
API for recovering a previous in-memory `ActivityRecording.Session`; the UI then
shows **Recording interrupted**, while the workout and command outbox recover.
A power loss during a save/discard call cannot be atomically coordinated with
Garmin's FIT storage. The app claims that terminal operation before invoking it
and does not retry it blindly. This favors avoiding duplicate activities; it
cannot guarantee an uninterrupted FIT across process death or prove that a
terminal FIT was saved during a power failure. The active recording claim and
63 recent claims are retained alongside recent ended-workout tombstones and the
increasing phone sequence. A deliberate restore of a much older phone backup is
a new owner decision and is outside this recent-session replay guarantee.

Garmin Connect uploads the saved native activity through Garmin's normal sync.
Strava transfer requires the owner's separate Garmin Connect–Strava connection.
No proprietary Training Effect, recovery or automatic exercise-recognition
metrics are promised. FIT appearance in Garmin Connect, transfer to Strava, HR
sensor behavior, Bluetooth operation with Android asleep, and device-specific
recording lifecycle require physical tactix 8 validation.
