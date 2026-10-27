#!/usr/bin/env bash
# Build locally signed Connect IQ sideload files; never publishes or uploads.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$ROOT/.local/garmin"
OUT="$ROOT/artifacts/garmin-companion"
MODE="${1:-build}"
TARGET="${2:-fenix847mm}"
SDK="${CIQ_SDK_HOME:-$LOCAL/sdk}"
KEY="${CIQ_SIGNING_KEY:-$LOCAL/developer-key.der}"

if [[ "$MODE" == setup ]]; then
  [[ "$(uname -s)" == Darwin ]] || { echo 'Use Garmin SDK Manager for your operating system.' >&2; exit 2; }
  mkdir -p "$LOCAL"
  SDK_ARCHIVE=connectiq-sdk-mac-9.3.0-2026-10-20-95888f262
  curl --fail --location "https://developer.garmin.com/downloads/connect-iq/sdks/$SDK_ARCHIVE.dmg" -o "$LOCAL/sdk.dmg"
  hdiutil attach -nobrowse "$LOCAL/sdk.dmg"
  trap 'hdiutil detach "/Volumes/Connect IQ SDK" >/dev/null 2>&1 || true' EXIT
  [[ ! -e "$LOCAL/sdk" ]] || { echo "SDK already exists: $LOCAL/sdk; remove it explicitly to replace it." >&2; exit 2; }
  cp -R "/Volumes/Connect IQ SDK/$SDK_ARCHIVE" "$LOCAL/sdk"
  curl --fail --location 'https://developer.garmin.com/downloads/connect-iq/sdk-manager/connectiq-sdk-manager.dmg' -o "$LOCAL/sdk-manager.dmg"
  hdiutil attach -nobrowse "$LOCAL/sdk-manager.dmg"
  cp -R '/Volumes/Connect IQ SDK Manager/SdkManager.app' "$LOCAL/"
  hdiutil detach '/Volumes/Connect IQ SDK Manager'
  echo "SDK installed at $LOCAL/sdk. Open $LOCAL/SdkManager.app and install fenix847mm and fenix8solar51mm device packages. Garmin sign-in may be required."
  exit 0
fi

[[ -x "$SDK/bin/monkeyc" ]] || { echo "Missing SDK: $SDK. Set CIQ_SDK_HOME or run $0 setup." >&2; exit 2; }
mkdir -p "$LOCAL" "$OUT"

if [[ "$MODE" == syntax ]]; then
  # This is the official SDK grammar parser, not a compiler or device test.
  # TestRig reports syntax diagnostics on stderr but does not set a failure code.
  RECEIPT="$OUT/syntax.log"
  : > "$RECEIPT"
  for source in "$ROOT"/garmin/source/*.mc "$ROOT"/garmin/tests/*.mc; do
    java -cp "$SDK/bin/monkeybrains.jar" org.antlr.v4.gui.TestRig \
      com.garmin.connectiq.common.antlr.monkeybrains.MonkeyC2020 program "$source" 2>> "$RECEIPT"
  done
  if [[ -s "$RECEIPT" ]]; then cat "$RECEIPT" >&2; exit 1; fi
  echo 'Official SDK grammar parse passed. Device compilation and simulator execution are separate checks.' | tee "$RECEIPT"
  exit 0
fi

case "$TARGET" in fenix847mm|fenix8solar51mm|all) ;; *) echo 'Target must be fenix847mm, fenix8solar51mm, or all.' >&2; exit 2;; esac
case "$MODE" in build|test|package) ;; *) echo 'Usage: scripts/garmin-build.sh [setup|syntax|build|test|package] [fenix847mm|fenix8solar51mm|all]' >&2; exit 2;; esac

if [[ ! -f "$KEY" ]]; then
  [[ "$KEY" == "$LOCAL/developer-key.der" ]] || { echo "Signing key does not exist: $KEY" >&2; exit 2; }
  umask 077
  openssl genrsa -out "$LOCAL/developer-key.pem" 4096 2>/dev/null
  openssl pkcs8 -topk8 -inform PEM -outform DER -in "$LOCAL/developer-key.pem" -out "$KEY" -nocrypt
fi

if [[ "$MODE" == package ]]; then
  "$SDK/bin/monkeyc" -f "$ROOT/garmin/monkey.jungle" -e -r -l 1 -w \
    -y "$KEY" -o "$OUT/opengym-garmin-beta.iq" 2>&1 | tee "$OUT/beta-package.log"
  exit 0
fi

TARGETS=("$TARGET")
[[ "$TARGET" != all ]] || TARGETS=(fenix847mm fenix8solar51mm)
for DEVICE in "${TARGETS[@]}"; do
  if [[ "$MODE" == build ]]; then
    "$SDK/bin/monkeyc" -f "$ROOT/garmin/monkey.jungle" -d "$DEVICE" -r -l 1 -w \
      -y "$KEY" -o "$OUT/opengym-$DEVICE.prg" 2>&1 | tee "$OUT/build-$DEVICE.log"
  else
    "$SDK/bin/monkeyc" -f "$ROOT/garmin/tests.jungle" -d "$DEVICE" -t -l 1 -w \
      -y "$KEY" -o "$OUT/tests-$DEVICE.prg" 2>&1 | tee "$OUT/test-build-$DEVICE.log"
    "$SDK/bin/connectiq"
    # Let the normal simulator listener become ready, bounded to ten seconds.
    for ((attempt=0;attempt<10;attempt++)); do
      if nc -z 127.0.0.1 1234 2>/dev/null; then break; fi
      sleep 1
    done
    if "$SDK/bin/monkeydo" "$OUT/tests-$DEVICE.prg" "$DEVICE" -t 2>&1 | tee "$OUT/test-$DEVICE.log"; then
      RUNTIME_STATUS=0
    else
      RUNTIME_STATUS=$?
    fi
    # SDK 9.3 monkeydo has returned 1 for a complete passing simulator run.
    # Judge the complete test receipt, including exception count, not exit alone.
    if ! grep -Eq '^PASSED[[:space:]]*\(passed=[1-9][0-9]*, failed=0, errors=0\)' "$OUT/test-$DEVICE.log"; then
      echo 'Simulator did not report a complete passing test run.' >&2; exit 1
    fi
    echo "Simulator receipt passed; monkeydo exit=$RUNTIME_STATUS."
  fi
done
