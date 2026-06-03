---
description: Remove the grab URI handler from this machine
allowed-tools: Bash
---

Remove the `grab:` URI scheme handler installed by /grab:setup.

1. Detect the OS with `uname -s`.
2. Run the matching uninstall script:
   - `Darwin` → `bash "${CLAUDE_PLUGIN_ROOT}/scripts/uninstall-macos.sh"`
   - `Linux` → `bash "${CLAUDE_PLUGIN_ROOT}/scripts/uninstall-linux.sh"`
   - anything else → tell the user only macOS and Linux are supported, stop.
3. Confirm to the user that the handler and `/tmp/grab/` are gone, and that future sessions will fall back to the "handler not installed" hint until they run /grab:setup again (or disable the plugin).
