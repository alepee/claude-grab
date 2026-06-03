#!/usr/bin/env bash
# Install the grab: URI handler on macOS: an AppleScript applet that
# forwards the URI to grab_handler.py, registered for the grab scheme.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$HOME/Applications/GrabHandler.app"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

mkdir -p "$HOME/Applications"
rm -rf "$APP"

osacompile -o "$APP" <<'APPLESCRIPT'
on open location theURL
	set appPath to POSIX path of (path to me)
	do shell script "/usr/bin/python3 " & quoted form of (appPath & "Contents/Resources/grab_handler.py") & " " & quoted form of theURL
end open location
APPLESCRIPT

cp "$SCRIPT_DIR/grab_handler.py" "$APP/Contents/Resources/grab_handler.py"

PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string dev.alepee.grab-handler" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes array" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0 dict" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLName string GrabClipboard" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes array" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string grab" "$PLIST"

"$LSREGISTER" -f "$APP"

sleep 2

echo "Installed $APP and registered the grab: scheme."
echo "Self-test: opening grab:test%20ok — paste somewhere to verify the clipboard contains 'test ok'."
open "grab:test%20ok"
