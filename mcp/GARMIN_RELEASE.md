# Garmin owner beta release MCP over HTTP

This dedicated Node stdio server updates the existing owner beta
`10ea70db-ee8f-4811-9b65-ec251468afae`, manifest
`6fcd6528636d4cc39c3ad1e317d7524a`. It uses HTTPS with a private cookie jar.
It does not launch/control a browser or import workout/database/health modules.
The previous Playwright adapter and selector configuration have been removed.

The Store website's private API is version-sensitive and is not a supported public
release SDK. Authenticated owner/version/manifest GETs have been verified. Neither
publication nor live expired-session renewal is proved by those checks or mocks.

## Setup

Use Node 22+ and a trusted 7-Zip executable. The macOS/Apple Silicon default is
`/opt/homebrew/bin/7zz`; Linux uses `GARMIN_RELEASE_7ZZ=/usr/bin/7zz` or another
absolute installed path. Run `npm ci` in `mcp`.

Configure `mcp/src/garmin-release/server.js` using
[the MCP example](examples/garmin-release.mcp.example.json). Deployment is disabled
unless that dedicated server process has `GARMIN_RELEASE_ENABLE_DEPLOY=1`.
Setup does not edit shared MCP configuration.

The local CLI imports a separately authorized cookie export, never passwords.
Supply a mode-0600 regular JSON file containing either an array of cookie records
or `{ "cookies": [...] }`. Browser records use `name`, `value`, `domain`, `path`,
`secure`, `httpOnly`, and `expires` (Unix seconds or -1). Only secure host-only
`apps.garmin.com` and `sso.garmin.com` records are accepted; unrelated and broad
cookie domains are ignored. Do not put credentials in chat, Git, an MCP argument,
a report or screenshot.

```sh
cd mcp
npm run garmin-release:session -- --import /absolute/private/cookies.json
```

Without `--import`, the command checks the existing HTTP session. It uploads
nothing. The private jar is
`artifacts/garmin-release-mcp/private/http-session.json` (0600, parent 0700).
The imported source remains the caller's responsibility. A legacy browser profile
may still exist locally; this transport neither reads nor launches it.

## Authentication renewal

`tough-cookie` handles expiry, host/path matching and `Set-Cookie` rotation.
Rotations are atomically persisted and synced before the next operation. When the
developer identity GET returns 401/403 or redirects, the transport follows the
observed Store `/login` entrypoint through at most eight HTTPS redirects on
`apps.garmin.com` and `sso.garmin.com`. Cookies remain scoped to their host. A valid
SSO session may complete this normally without interaction; the identity GET is
retried once afterward. No OAuth grant or refresh endpoint is invented from the
website's encrypted `refresh_token` cookie.

Normal redirect renewal is mock-tested. Successful renewal of an actually expired
live session remains unverified. The live unauthenticated SSO probe returned a
Cloudflare challenge. `AUTH_HANDOFF` requires login/MFA or a security check outside
this MCP, then an authorized local import. No browser control or challenge bypass
is performed. Renewal cannot be guaranteed when Garmin requires a human.

## Tools

| Tool | Behavior |
| --- | --- |
| `garmin_release_status` | Offline jar and journal readiness; no network. |
| `garmin_release_check` | Verify authenticated owner, fixed beta, signed manifest and current version via GET. May renew/persist the session. No upload. |
| `garmin_release_prepare` | Validate and snapshot the fixed versioned inbox IQ; no network. |
| `garmin_release_deploy` | Publish a prepared owner-beta update with confirmations and durable duplicate protection. |

The inbox path is
`artifacts/garmin-release-mcp/inbox/opengym-garmin-0.1.0-beta.3.iq` for beta.3.
Tool arguments accept the pinned `appId`, strict beta `version` and lowercase
64-digit `sha256`, never caller-selected paths, URLs, commands or credentials.
Deploy additionally requires `expectedCurrentVersion`, `confirmOwnerOnlyBeta:true`,
`confirmSubmissionTerms:true` and nonempty `releaseNotes` (max 2000 characters).
Final submission agrees to Garmin terms: obtain user confirmation for that specific
upload before setting `confirmSubmissionTerms`. Enabling deployment is not that
confirmation. Setup/checking never submits.

## Publication and recovery

1. GET developer identity, the fixed app and owner metadata (`isShadowApp=false`).
   Require exact owner, beta/non-shadow flags, signed Device App manifest, expected
   current version and no pending previous scan.
2. Persist app-wide and per-version intent before the first POST.
3. POST multipart `appBinaryFile` to `/api/ciq-developerservices/iqFiles/validate`
   with `isNewAppVersion=true`, version and app ID. Require the expected signed
   manifest identity and temporary file ID. The live validation response does not
   contain `newAppVersion`; version assignment occurs in the next POST and is
   verified through the subsequent app/metadata GETs.
4. POST `{tempFileId,appVersion}` to the owner's app `/version` endpoint with
   `locale=en-US&juniorAppUpdate=false`.
5. GET fresh metadata. Immediately after the successful version POST, the signed
   binary metadata may show the requested version while the app summary still
   shows the exact previous version. Accept only that specific transition at this
   point; owner/beta/signature fences remain. PUT the writable fields as multipart
   `appMetadata`, changing only English `appWhatsNew`, temporary ID and version.
   Preserve other translations, descriptions, beta flags and settings. Omit
   read-only media/file metadata; no screenshot operations are performed.
6. GET owner/app/metadata again to verify the new beta and release notes. Requests
   ask for uncached responses. Only these final reads may repeat, with at most
   seven checks and 60 seconds of backoff for propagation. Ownership/auth failures
   stop immediately. No write repeats. Allow at least a 180-second tool timeout
   in the calling client; individual HTTP requests remain limited to 30 seconds.

The version POST precedes details, as in Garmin's uploader. Final success still
requires matching app-summary and signed-metadata versions plus saved notes.
A later failure may
mean the version exists but notes were not saved. The attempt is uncertain, not a
success or an automatic retry. GETs do not establish completed scanning or watch
installation. Writes are never retried, redirected or replayed after renewal.

An uncertain attempt blocks that version and later versions across restarts.
An identical verified success returns its receipt without another POST. One
process lock serializes import/check, preparation and deployment. Inspect a stale
crash lock before removing it. Never delete journals to retry an uncertain upload;
reconcile the actual Store state first.

Preparation is transactional. Trusted 7-Zip validates actual 7z IQs without
filesystem extraction: SHA256, XML/schema, pinned manifest, nonempty regular PRGs
and archive integrity. Limits: 64 MiB archive, 256 MiB expanded, 10,000 entries,
1 MiB manifest and bounded process output/time. Store version is caller-assigned.
Local validation does not verify cryptographic signatures or watch behavior.

GETs use Node fetch. POST/PUT use one `node:https.request` on a fresh connection:
fetch's implicit HTTP 421 replay must not apply to release writes. Native multipart
encoding and explicit content length preserve the form bodies. HTTP responses are
bounded to 2 MiB with a 30-second timeout per request. Errors
never return raw bodies, cookies, tickets, owner IDs or developer secrets. Private
cookies, journals and IQ artifacts are Git-ignored. No workout data is needed.

## Evidence and maintenance

Protocol recovered on 2026-10-28 from Garmin's deployed public client:

- [Update route](https://apps.garmin.com/_next/static/chunks/pages/developer/%5Buid%5D/apps/%5Baid%5D/update-16bf32c0bd90c977.js)
- [Uploader chunk](https://apps.garmin.com/_next/static/chunks/480-ea6d2244e7110a15.js), module 71480
- [Application chunk](https://apps.garmin.com/_next/static/chunks/pages/_app-792471dff957ad16.js), developer endpoints module 86132

These assets can change/disappear. Keep local source hashes and sanitized check
receipts under `artifacts/garmin-api/`, without credentials or raw identity bodies.

```sh
npm run test:garmin-release
npm test
npm run check:node-loadable
```

Coverage includes synthetic real IQs, real Node stdio discovery, multipart/JSON
contracts, owner/version/signature fences, preserved metadata, cookie rotation and
expiry, scoped redirects, challenge handoff, response bounds, durable uncertain
attempts and transactional preparation. Mocks do not prove live deployment or
successful expired-session renewal.
