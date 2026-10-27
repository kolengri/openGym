# Garmin companion protocol

The Android app and Connect IQ watch app communicate locally through Garmin's Android companion SDK and Garmin Connect. No workout data is sent to GitHub or an openGym server by this integration. It is off until enabled in Settings. Garmin Connect's own activity upload and an explicitly linked Strava account are independent services.

Application ID (Connect IQ UUID without hyphens): `6fcd6528636d4cc39c3ad1e317d7524a`.

## Transport

Messages are Connect IQ dictionaries, not JSON strings. Version `v: 1` is required. All times use Unix milliseconds (64-bit). Keep each message under 12 KiB; refuse an oversized snapshot with an actionable error, never silently remove running sets. Only active workout data is sent: no routines, past workouts, animations, credentials or account identifiers.

- Phone to watch: `{v: 1, kind: 'snapshot', seq, state}`. `seq` is a persisted increasing integer. `state` is the existing `watch-sync.js` snapshot, reduced to `v`, `unit`, `restSec`, `active`, `discarded`, `settings`. Strip `ready`, `last`, `best`, clips and Apple Health deletion data. `settings` carries `restHaptics` and `recording` (true). `active` retains its existing ID, start, current exercise index, entries and sets. Each entry includes its ID, name, mode, rest seconds and sets. Keep per-side sets, set type and timed-set seconds. `active.rest` may include `paused` and `left` as well as `endsAt`. An optional `active.watchPaused` pauses the watch recording. An explicit empty active snapshot ends the previous workout: discard if its ID is in `discarded`, save otherwise. Never accept snapshots older than the last received sequence.
- Watch to phone: `{v: 1, kind: 'hello'}` requests the latest persisted snapshot and retries pending acknowledgements.
- Watch to phone: `{v: 1, kind: 'events', events: [...]}`. Queue ordered events durably on both ends. Phone only acknowledges after application to the workout store and `saveNow` has completed. Unacknowledged watch events survive disconnect/restart and are replayed over fresh snapshots before display.
- Phone to watch: `{v: 1, kind: 'ack', ids: [...], seq, state}` atomically acknowledges commands with the resulting post-apply snapshot. Reject snapshots older than this causal fence; replay remaining local events over its state. Same-sequence acknowledgement chunks still remove their IDs. Never acknowledge merely on transport receipt. Persist and resend acknowledgement fences on hello so losing an acknowledgement is harmless.
- Watch to phone: `{v: 1, kind: 'hr', wid, bpm, at}` is a transient current heart rate, at most once per five seconds; do not append these samples to the durable command queue. Per-set aggregates are durable `setDone.hr` / `setHr` events.

Events use the existing watch-sync schema: `{id, type, wid, at, ...}`. `id` is globally unique per watch installation and durable counter, and remains identical across retries. Commands require the exact active `wid`; validate positions, exercise IDs and numeric fields. Supported events:

Garmin applied-event IDs are bounded in `S.garminAppliedEvents`, inside the same workout snapshot committed by strict `saveNow`. They must never rely on the separate legacy Apple Watch localStorage ledger: a successful ID write cannot stand in for a failed workout write. A restart replays every command absent from the restored workout's own fence.

Each set carries effective `restSec`, including explicit zero, resolved by the phone's existing set, exercise, warmup and pyramid helpers. Each entry carries effective `sideRestSec` (zero by default for rep sides). The watch respects contiguous superset rounds, skips rest after the final workout set and before a following unit's warmup, and preserves an existing rest when selecting an exercise. Side-switch rests retain `kind: 'switch'` through pause and acknowledgement.

- `setDone`: `exId`, `entryIdx`, `setIdx`, optional `w`, `r`, `sec`, `side: 'L'|'R'`, `hr: {avg,max}`. Mark done, never toggle off on replay. For timed sets record elapsed seconds; refuse unsupported set shapes instead of inventing repetitions.
- `setHr`: same set identity and optional `hr` / `restHr` aggregates.
- `selectExercise`: `exId`, `entryIdx` (absolute selection, not relative next; retry-safe).
- `pause`: `paused` boolean and `rest` (null or the resulting watch rest with `endsAt`, `left`, `paused`, optional `total`, `forIdx`, `forSet`, `kind: 'switch'`). Restore the watch's absolute rest state instead of pausing at message-receipt time; delayed/offline pause and resume retain the same remaining seconds. Pause/resume watch recording; no fabricated workout duration changes.
- `skipRest`: ends the current rest.
- `finish` / `discard`: require explicit confirmation on watch; save/discard watch recording once, queue the phone action. Keep recent ended IDs to prevent a delayed snapshot from starting the recording twice.

Newer snapshots must retain pending local commands; do not let a phone snapshot undo a set tick that has not yet been acknowledged. Starting the workout initially happens on the phone. The watch can continue the received session while Android's WebView sleeps. The next foreground/reconnection applies its queued actions. No promise of running arbitrary JavaScript continuously with Android locked is made.

## Capacitor bridge

Plugin `GarminBridge` exposes `status`, `devices`, `configure({enabled, deviceId?})`, `sendSnapshot({json})`, `drain`, `ack({ids,json})` and `openOnWatch`. The acknowledgement's `json` is freshly built from the resulting store after `saveNow` succeeds. The native bridge atomically persists it at the next sequence with acknowledgement IDs before removing those commands from its queue. A previously queued snapshot is not a valid replacement.

`status` returns `{available, activated, enabled, paired, installed, connected, deviceId?, deviceName?, error?}`; `devices` returns `{devices:[{id,name,connected}]}`. `configure` must be explicit, persist selection locally and clear user-specific queues/snapshots when changing devices or disabling the link. `drain` returns `{events}`. `sendSnapshot` accepts JSON from the existing web bridge and sends the reduced dictionary above; returns `{sent}`. `openOnWatch` requests opening the configured app, without browser/network URLs.

Emit `watchState` when link status changes, `watchEvent` after a durable command arrives and `heartRate` with the transient HR payload. Persist command queues and latest snapshot in Android app-private storage. Register only the fixed companion app UUID on the selected Garmin device. Failed sends remain retryable. Bound queues, messages, nesting and data types. Do not drop unacknowledged commands on queue overflow.

## Acceptance

Test duplicate/retried/out-of-order messages, old workout IDs, reboot/reconnect persistence, stale and oversized snapshots, no link and disabled link, malformed fields, and finish/discard confirmation. Commands have to work with Android asleep by local watch execution and eventual replay; immediate Android UI updates are best effort while its WebView is suspended. Physically validate background connection, FIT appearance in Garmin Connect and Strava transfer on the owner's tactix 8 before claiming device verification.
