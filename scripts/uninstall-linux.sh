#!/usr/bin/env bash
# Remove the grab: URI handler from Linux.
set -euo pipefail

APPS_DIR="$HOME/.local/share/applications"
MIMEAPPS="$HOME/.config/mimeapps.list"

rm -f "$APPS_DIR/grab-handler.desktop"
rm -rf "$HOME/.local/share/grab"

if [ -f "$MIMEAPPS" ]; then
  sed -i '/^x-scheme-handler\/grab=/d' "$MIMEAPPS"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" || true
fi

rm -rf /tmp/grab
echo "grab handler uninstalled."
