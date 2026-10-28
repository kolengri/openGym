# Garmin Android updates

The Garmin Android channel uses `kolengri/openGym` GitHub Releases. It never selects
an upstream, Play or watch APK. Settings → About checks the 100 most recent releases
once per app session; a manual check clears that cache and fetches again. It selects the
highest published, non-draft, non-prerelease `garmin-android-<versionCode>` tag.

Each release must contain exactly these assets, with their exact GitHub download URLs:

- `openGym-Garmin-<versionCode>.apk`
- `openGym-Garmin-<versionCode>.apk.sha256`

The release title should equal the Android versionName, for example
`1.4.3-garmin.6`. The updater compares the installed native versionCode, independently
of upstream semantic versions and Vite build metadata. Missing native identity,
malformed responses, incomplete assets or foreign download URLs fail closed.
A checksum failure never opens the installer. The native installer also requires
the same installed package and a greater APK versionCode; Android enforces signing
compatibility before replacing the app.

## First installation

Code32 and earlier intentionally have no fork updater. Install code33 once over the
existing app. Keep package `ch.duartesantos.opengym.garmin.test` and the original
signing key. Never uninstall, clear data or change the application ID. Android may
ask the owner to allow openGym to install apps; installation remains a system UI
confirmation. No background/silent installation is promised. No training database
is uploaded by this update mechanism.

## Preparing subsequent releases

1. Increase only the Garmin flavor's versionCode and versionName in
   `frontend/android/app/build.gradle`. Build the mobile frontend and Android
   `assembleGarminDebug` with the existing local signing identity, using
   `APP_BUILD=garmin.<revision>`. Run `cap sync android`, never the iOS build.
2. Validate the package, increasing versionCode and signer with Android build tools.
   Required signer SHA256:
   `4b4ec6787f5999874eb88923e53d549246ea3b3bb0f8b87ac473b110bae33d2f`.
   Inspect the APK for accidental private database/archive/key payloads.
3. Name the reviewed APK `openGym-Garmin-<versionCode>.apk` and create its SHA256
   sidecar (`shasum -a 256 <APK> > <APK>.sha256`). Publish only these application
   artifacts, never workout exports, databases, journals, session files or keys.
4. Create a **draft** release in `kolengri/openGym` at the accepted commit with tag
   `garmin-android-<versionCode>` and title equal to versionName. Upload both files.
   Check their names and hashes, then publish the release (not as a prerelease).
   Draft-first publication keeps incomplete releases out of the updater.
5. Fetch the actual public release payload and checksum. Check that a lower native
   version receives the update, equal/newer versions do not, and the production
   download/checksum/install flow remains available. Keep physical evidence separate
   from parser/unit or APK-inspection evidence.

The shared non-Play Install plugin remains unavailable in Play builds. Ordinary
sideload builds retain their original upstream release feed and asset selection.
No GitHub token is embedded in the app and no Node/Cloudflare server is required.
