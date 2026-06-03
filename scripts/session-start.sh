#!/usr/bin/env bash
# SessionStart hook: inject the grab link instruction when the grab:
# URI handler is installed; otherwise hint at /grab:setup.
set -uo pipefail
: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT must be set}"

installed=false
case "$(uname -s)" in
  Darwin)
    [ -d "$HOME/Applications/GrabHandler.app" ] && installed=true
    ;;
  Linux)
    [ -n "$(xdg-mime query default x-scheme-handler/grab 2>/dev/null)" ] && installed=true
    ;;
esac

if [ "$installed" = true ]; then
  context="$(cat "${CLAUDE_PLUGIN_ROOT}/instruction.md")" || exit 1
else
  context="grab plugin: the grab: URI handler is not installed on this machine, so click-to-copy links are disabled. If the user wants them, suggest running /grab:setup once."
fi

python3 - "$context" <<'EOF'
import json, sys
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": sys.argv[1],
    }
}))
EOF
