# Garmin owner-only beta release MCP

This dedicated Node stdio entrypoint updates the **existing** owner-only beta listing
`10ea70db-ee8f-4811-9b65-ec251468afae`, whose watch manifest ID is
`6fcd6528636d4cc39c3ad1e317d7524a`. It never imports the workout MCP's state,
database, API client, pairing or frontend modules. Do not configure `src/index.js`
when you only want release access.

The upload implementation uses Playwright's file input and form controls. It is
exercised against mocks, including failures after file selection. The authenticated
listing and initial update form were inspected; the dedicated Playwright session,
details/submission flow, live upload and physical device behavior remain unverified.
No IQ was transmitted and no final submission was made. The artifact validator
has additionally passed a read-only compatibility check against the actual signed
beta2 IQ, without rebuilding, modifying or uploading that file.
The supplied selector example contains observed first-step controls but remains intentionally invalid until the unobserved details/submission step is configured and reviewed. This is implementation readiness, not evidence of a successful release.

## Why a browser adapter

As of 2026-10-28, no supported public Store release/upload API or upload CLI was
found in the official sources inspected:

- Garmin's [Submit an App](https://developer.garmin.com/connect-iq/submit-an-app/)
  describes exporting an IQ bundle and uploading it through the Connect IQ Store.
  It does not document an upload API, service credentials or release CLI.
  Its upload link is `https://apps.garmin.com/en-US/developer/upload`; an
  unauthenticated HEAD request returned a 307 Garmin SSO redirect. No login was attempted.
- Garmin's [reference guides](https://developer.garmin.com/connect-iq/reference-guides/)
  link Monkey C command-line tooling. The existing `scripts/garmin-build.sh` uses
  `monkeyc -e` for packaging, not uploading.
- The official [Publishing to the Store](https://developer.garmin.com/connect-iq/core-topics/publishing-to-the-store/)
  and [Beta Apps](https://developer.garmin.com/connect-iq/core-topics/beta-apps/)
  routes returned navigation without substantive article bodies during this check.
  They therefore do not establish today's exact beta form or owner-only UI text.

This is a bounded documentation finding, not proof that private/partner APIs do
not exist. Context7 lookup was attempted for Garmin, the MCP SDK and Playwright;
all returned `Monthly quota reached`. Primary documentation and installed SDK
declarations were used instead. No undocumented Garmin endpoint, token extraction
or third-party upload service is used.

We reuse the existing `@modelcontextprotocol/sdk` and Zod stack. A separate
entrypoint in the existing package keeps dependency management in one place while
avoiding the workout server's data access. Playwright is preferable to guessing
private HTTP endpoints; the tradeoff is selector maintenance and an interactive
session renewal when Garmin requires it. There is no automatic public publication,
new listing creation, beta checkbox change or watch installation step.

## Local installation and setup

Use Node 20 or newer. Install from the lockfile, then install Playwright Chromium
only on the machine that will run authorized deployments:

```sh
cd mcp
npm ci
npx playwright install chromium
```

The library install does not initialize a Garmin session. The MCP starts and
serves offline tools without a Chromium binary or Garmin SDK. Nothing edits
system MCP configuration, keychain entries or the user's normal browser profile.

IQ validation additionally requires a trusted local `7zz` executable; the tested
host has 7-Zip 26.04 at `/opt/homebrew/bin/7zz`. On another host, set
`GARMIN_RELEASE_7ZZ` to the absolute executable path in the MCP process environment
and the test runner's environment. This accepts an executable path, not shell
arguments or a command string, and cannot be supplied through a tool call. Install
the CLI separately if absent; no archive codec, SDK or binary is downloaded by the
MCP. Tests that create synthetic IQs also require this CLI, including in CI.
The GitHub Ubuntu MCP job installs `7zip-standalone`; the GitLab Alpine MCP job
installs `7zip`. Both explicitly configure `/usr/bin/7zz` and check that it is executable.

All local state is relative to this checkout, independent of the client's working
directory:

```text
artifacts/garmin-release-mcp/
  inbox/opengym-garmin-0.1.0-beta.3.iq
  releases/0.1.0-beta.3/
    opengym-garmin-0.1.0-beta.3.iq
    receipt.json
    journal.json
  private/
    browser.json
    browser-profile/
    session-ready.json
    active-deployment.json
    operation.lock
```

The repository already ignores `/artifacts/`. Release directories are created with
mode 0700, and receipt/config/journal files use 0600. The dedicated process uses
umask 077; browser state must stay inside its dedicated private profile. Existing
normal Chrome profiles, credentials, signing keys and personal exports are never
copied. The server suppresses Playwright debug environment flags and emits neither
raw browser errors nor browser console/network logs, traces, HARs or screenshots.

1. Copy [the browser adapter example](examples/garmin-release.browser.example.json)
   into `artifacts/garmin-release-mcp/private/browser.json` with mode 0600. Create
   the parent directories with mode 0700. This file contains selectors, not passwords.
2. With a separately authorized local inspection of your existing listing, verify the observed selectors and replace
   every remaining `REPLACE_...` selector/text with the current UI contract. Use the exact
   listing URL from the developer dashboard; it must be HTTPS on
   `apps.garmin.com` or `apps-developer.garmin.com` and contain the existing listing ID as a path segment.
   Do not use a create-app URL. The example listing route was inspected in the
   authenticated browser; the complete dedicated deployment flow remains unverified.
3. `ownerBeta` must identify the listing's owner-only beta state, not merely an app
   title or a generic badge. `currentVersion` must match one element whose text is the current beta version,
   optionally prefixed by `Version ` or `v`, or suffixed by `(Internal: N)`. Parsing is
   anchored and rejects multiple/ambiguous versions. `ownerBeta.prefix` permits the
   observed owner-warning sentence followed by explanatory text. `formIdentity`
   verifies the app update heading after navigation; it does not independently prove
   beta visibility. The listing owner-only warning is checked before upload and again
   after saving. No visibility setting is changed.
   `uploadAccepted` must identify completed saving, not file selection or progress.
   All selectors use Playwright's locator syntax and must match a single target.
4. The fixed flow is: listing inspection; optional `updateButton`; form identity check;
   file selection; version field; optional `nextButton`; form identity check; release
   notes; save beta; completion marker; listing reload; version and beta verification.
   Omit `updateButton` or `nextButton` if the current form has no such step. If this
   flow no longer matches Garmin's UI, update the adapter and its mocks before use.
   Never point controls at public publication, review submission, visibility,
   account creation, terms acceptance or app creation actions.
5. Add current login/MFA, CAPTCHA and terms-form selectors to `handoffSelectors`.
   Set `reviewedForExistingOwnerBeta` to `true` only after reviewing the complete
   flow. An unchecked example or unresolved placeholders fail validation.
6. In an interactive terminal, run `npm run garmin-release:session`. This opens
   a new dedicated headed profile on the configured existing listing. Complete
   login, MFA, CAPTCHA and any terms yourself. Return to that listing and press
   Enter in the terminal. The command verifies the beta marker/version, closes
   the browser and stores only a local verification marker plus the private profile.
   It does not select a file or upload. Re-run it when authentication expires.

Browser setup is a separately authorized interactive operation; it has not been
run as part of implementation. Never paste cookies, credentials or profile contents
into MCP tool arguments, chat, Git or shared reports.

## Preparing a new IQ

The known baseline is `0.1.0-beta.2`; new versions must be strictly newer, with the
form `major.minor.patch-beta.N` and at most 20 characters. An example next version
is `0.1.0-beta.3`. Keep the watch's displayed AppVersion consistent with the
caller-assigned Store version when preparing the next watch release. The signed
IQ manifest does not carry that release version, so this validator cannot prove
that the binary's displayed version matches the assigned Store metadata.

**Do not run `scripts/garmin-build.sh package` for this workflow.** Its output is
the original `artifacts/garmin-companion/opengym-garmin-beta.iq`, which must remain
untouched; it can also generate signing material if the default key is missing.
Use the official SDK export workflow with the existing signing identity and a new
versioned output filename, directly into this workflow's `inbox/`. Signing key
configuration may reference `CIQ_SIGNING_KEY` and SDK configuration may reference
`CIQ_SDK_HOME`; this release MCP neither reads those variables nor opens the key.
Do not copy the primary checkout's private SDK/key directory into another worktree.

Preparation expects the actual SDK's **7z IQ format**, identified by magic bytes
`377abcaf271c`. ZIP is not supported. The archive must contain exactly one regular
root `manifest.xml` and nonempty regular `.prg` files. The manifest must have schema
`version="3"` on `iq:manifest`, one application with the existing manifest ID and
`type="watch-app"`; namespace prefixes are ignored. The application has no required
release-version attribute. XML entities/DTDs, duplicate or unsafe archive paths,
encrypted entries and links posing as the manifest or programs are rejected.

Bounds are 64 MiB archive bytes, 256 MiB total declared expanded bytes, a 1 MiB
manifest, and 10,000 entries. Fixed `7zz` argument arrays use no shell or interactive
stdin; each process has a 15-second deadline, one worker, a 256 MiB decoder memory
limit, at most 8 MiB listing output and 64 KiB diagnostics. Only the exact root
manifest and listed `.prg` members are decoded to bounded stdout, with CRC errors
and mismatching byte counts rejected. Program bytes are counted and discarded.
No archive member, signature or public key is extracted to the filesystem. The
unchanged IQ is copied into a private temporary directory for the CLI and removed
after success or failure. Password requests, encrypted headers and decoder failures
fail closed; no password is provided or requested by this server.

The release version is caller-assigned Store metadata, independently guarded by the
existing request/version/replay rules. Validation metadata records
`versionSource: "caller-assigned-store-metadata"`, `archiveFormat: "7z"`, validated
manifest identity/schema, the actual SHA256 and `signatureVerification: "not-verified"`.
These fields flow into the preparation receipt. Relabeling an existing beta2 IQ as
beta3 in a local validation check does not create a new build or establish that it
is appropriate to upload. Never modify signed bytes to add a version attribute.

Compute the input hash locally (for example, `shasum -a 256 <versioned-iq>`).
`garmin_release_prepare` accepts:

```json
{
  "appId": "10ea70db-ee8f-4811-9b65-ec251468afae",
  "version": "0.1.0-beta.3",
  "sha256": "<64 lowercase hexadecimal characters>"
}
```

It only reads `inbox/opengym-garmin-<version>.iq`, validates the actual hashed bytes,
and creates an exclusive versioned snapshot plus a SHA256 receipt. Both files are
synced in a unique private staging directory before the complete version directory
is published by rename under the operation lock. Failed preparation cleans its
staging directory; abandoned staging from an interrupted process does not reserve
the final version. The process lock still requires manual inspection after a crash.
Paths and shell
commands are not tool arguments. Existing snapshots cannot be overwritten by a
different artifact. Repeating an identical preparation returns the existing receipt.
Hash, manifest and archive CRC validation do not verify the cryptographic signature, signing identity, device behavior
or SDK compatibility; Garmin still validates the package server-side.

## MCP registration and explicit deployment

Adapt [the MCP config example](examples/garmin-release.mcp.example.json) for your
client using an absolute entrypoint path. The initial deployment flag is `0`.
Register only this release server to avoid granting workout tools. The tools are:

| Tool | Observable behavior |
| --- | --- |
| `garmin_release_status` | Offline config/session-marker/lock status; optional version shows the prepared hash and journal state. A session marker is historical evidence, not a live login check. |
| `garmin_release_prepare` | Validates and snapshots an IQ locally. No Garmin browser/network operation. |
| `garmin_release_deploy` | Opens the configured dedicated session, verifies target/beta/current version, uploads the actual validated IQ buffer and notes, saves the update, then verifies the listing. |

When ready for an authorized real update, set `GARMIN_RELEASE_ENABLE_DEPLOY=1` in
the dedicated process config and restart that process. Deployment additionally
requires this explicit request:

```json
{
  "appId": "10ea70db-ee8f-4811-9b65-ec251468afae",
  "version": "0.1.0-beta.3",
  "sha256": "<the exact prepared hash>",
  "expectedCurrentVersion": "0.1.0-beta.2",
  "confirmOwnerOnlyBeta": true,
  "confirmSubmissionTerms": true,
  "releaseNotes": "Describe this beta update."
}
```

The existing listing must still show `expectedCurrentVersion`; the new version must
be greater than that version and the baseline. Before file selection, the service
rehashes/revalidates the prepared bytes and durably records an upload intent. A
toast alone never establishes success: the reloaded existing listing must show the
new version and the unchanged owner-beta marker. A successful result reports
`state: "deployed"` with the version/hash and verification timestamp. It does not
claim the app has reached a physical watch; normal Connect IQ distribution handles
installation afterward.

## Failures and recovery

- `DEPLOY_DISABLED`, invalid inputs, hash/manifest/version mismatches, missing
  setup, login redirects and beta-marker mismatches stop the operation. Preflight
  failures that occurred before file selection do not consume a deployment intent.
- File selection itself may start a remote upload. Any failure after the persisted
  intent becomes `uncertain`; a crash can leave `uploading`. Both block subsequent
  deployment requests for this version, even after a restart or changed notes/hash.
  An app-wide durable guard also blocks later versions while any upload is unresolved.
- An identical already verified deployment returns its stored result without
  uploading again. Different parameters for that version are rejected.
- One exclusive local lock covers prepare, deploy and interactive setup across
  processes. A crash can leave `private/operation.lock`. There is no timed expiry
  or automatic reset that could race a slow upload.
- Reconcile uncertain attempts manually on the **existing** Garmin beta listing.
  Check its version and the private journal; do not resend an upload just because
  a timeout occurred. Keep the journal as evidence. There is deliberately no MCP
  tool to erase an intent or mark a failed attempt safe to retry. Any local repair
  requires separately authorized evidence that no process or remote upload remains
  in flight. Prefer a reviewed recovery change over deleting state blindly.
  Check `private/active-deployment.json` as well as the version journal: a crash
  between durable writes may conservatively leave one at `uploading` even if another
  records a verified result.
- CAPTCHA, login/MFA and terms are manual handoffs. Unknown form changes stop the
  adapter; there is no attempt to bypass challenges or automatically accept terms.
  Browser/provider diagnostics are sanitized rather than copied into tool output.

## Verification and evidence limits

```sh
cd mcp
npm run test:garmin-release
npm test
npm run check:node-loadable
```

The release tests generate real synthetic 7z IQ archives using the local CLI and use mocked browser objects. The stdio
test starts the real Node server through the existing SDK client, lists exactly
three release tools, calls offline status with an unusable workout-data path,
and checks that deployment is disabled. No system MCP configuration is installed.
Tests cover upload intent ordering, persistent uncertain/active retry blocking,
concurrent services, immutable version conflicts, changed artifact bytes, wrong
app/version/beta, login/CAPTCHA handoff, private config, symlinks and browser errors.
Artifact tests also cover absent application-version metadata, encrypted payloads
and headers, corrupt program data, non-regular/empty programs, a non-root manifest,
entry/size/output limits and executable-path shell-injection boundaries. The actual
signed beta2 IQ is used only for an authorized local compatibility receipt; no real
binary, signature or public key fixture is included in Git.

Relevant primary library references are [MCP's TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk/tree/v1.x),
[Playwright authentication](https://playwright.dev/docs/auth),
[persistent browser contexts](https://playwright.dev/docs/api/class-browsertype#browser-type-launch-persistent-context),
[file uploads](https://playwright.dev/docs/input#upload-files),
[7-Zip](https://www.7-zip.org/) (the installed CLI's `7zz -h` documents the switches) and
[fast-xml-parser](https://github.com/NaturalIntelligence/fast-xml-parser).
Local evidence and source fingerprints belong in ignored
`artifacts/garmin-release-mcp/`, never in shared browser/session dumps.

## Authenticated UI evidence and remaining setup

The existing listing was inspected on 2026-10-28. Its owner-only banner begins
`Only you will be able to download and test the app.`; a separate BETA badge is
present. The current version appears as both `Version 0.1.0-beta.2` and
`0.1.0-beta.2 (Internal: 2)`. Upload New Version navigates to an existing-app
update route containing the fixed listing UUID; the developer account ID is not
stored in source. The initial update heading, `input#fileInput` and
`input#app-version` are observed in the example. The update heading alone does
not establish owner-only visibility.

The next/details step, release-notes input, final submission sequence and completed
release marker remain unobserved. CUA file selection was blocked by the local
browser extension's file-access setting; no IQ was transmitted and the final
button was not pressed. The example remains fail-closed with placeholders for
these unverified controls. It must not be marked reviewed until that flow is
confirmed in the dedicated deployment session.

The Store form says final submission agrees to Garmin's Developer License
Agreement and Terms of Use. The client/operator must obtain the user's explicit
confirmation for the specific final upload before passing
`confirmSubmissionTerms: true`; this is never a persisted consent setting.
`confirmOwnerOnlyBeta` is a separate privacy precondition, not legal consent. Do not run unattended final submission
through a new agreement or security challenge. The adapter never clicks separate CAPTCHA, MFA or agreement controls. The final
upload button itself can accept the linked terms, so its per-upload confirmation
is required before invocation.
