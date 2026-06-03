#!/usr/bin/env bash
# Install the grab: URI handler on Linux: a .desktop entry that
# forwards the URI to grab_handler.py, registered for the grab scheme.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HANDLER_DIR="$HOME/.local/share/grab"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP="$APPS_DIR/grab-handler.desktop"

if [ -n "${WAYLAND_DISPLAY:-}" ]; then
  command -v wl-copy >/dev/null 2>&1 || { echo "error: Wayland session detected, need wl-copy installed." >&2; exit 1; }
else
  command -v xclip >/dev/null 2>&1 || { echo "error: X11 session detected, need xclip installed." >&2; exit 1; }
fi

mkdir -p "$HANDLER_DIR" "$APPS_DIR"
cp "$SCRIPT_DIR/grab_handler.py" "$HANDLER_DIR/grab_handler.py"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Grab URI Handler
Exec=python3 "$HANDLER_DIR/grab_handler.py" %u
MimeType=x-scheme-handler/grab;
NoDisplay=true
EOF

xdg-mime default grab-handler.desktop x-scheme-handler/grab
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" || true
fi

echo "Installed $DESKTOP and registered the grab: scheme."
echo "Self-test: opening grab:test%20ok — paste somewhere to verify the clipboard contains 'test ok'."
xdg-open "grab:test%20ok" || echo "warning: self-test failed (no display?). Run: xdg-open 'grab:test%20ok' from a desktop session." >&2
