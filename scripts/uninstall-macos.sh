#!/usr/bin/env bash
# Remove the grab: URI handler from macOS.
set -euo pipefail

APP="$HOME/Applications/GrabHandler.app"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

if [ -d "$APP" ]; then
  "$LSREGISTER" -u "$APP" || true
  rm -rf "$APP"
  echo "Removed $APP."
else
  echo "GrabHandler.app not found — nothing to remove."
fi

rm -rf /tmp/grab "${TMPDIR:-/tmp}/grab"
echo "grab handler uninstalled."
