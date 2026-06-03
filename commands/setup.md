---
description: Install the grab URI handler for click-to-copy 📋 links
allowed-tools: Bash
---

Install the `grab:` URI scheme handler so `[📋](grab:...)` links put content in the clipboard.

1. Detect the OS with `uname -s`.
2. Run the matching install script:
   - `Darwin` → `bash "${CLAUDE_PLUGIN_ROOT}/scripts/install-macos.sh"`
   - `Linux` → `bash "${CLAUDE_PLUGIN_ROOT}/scripts/install-linux.sh"`
   - anything else → tell the user only macOS and Linux are supported, stop.
3. The script ends with a self-test that opens `grab:test%20ok`. The terminal may ask to confirm opening an unknown URI scheme the first time — tell the user to allow it (and remember the choice if offered).
4. Ask the user to paste somewhere: the clipboard must contain `test ok`. Report success or failure based on their answer.
5. On success, tell the user the 📋 links will appear starting from the next session (the SessionStart hook detects the handler).
