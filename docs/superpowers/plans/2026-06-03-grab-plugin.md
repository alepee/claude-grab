# grab Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Claude Code plugin `grab` that makes Claude append clickable `[📋](grab:...)` links after copyable output, backed by an OS-level `grab:` URI handler that pipes the payload to the clipboard.

**Architecture:** One shared Python handler (`grab_handler.py`) does all decode/read/copy logic on both OSes; thin OS-specific install scripts register it as the `grab:` scheme handler (AppleScript applet on macOS, `.desktop` on Linux). A SessionStart hook detects the handler and injects the link-emitting instruction. Two slash commands (`/grab:setup`, `/grab:uninstall`) drive the install scripts.

**Tech Stack:** Bash, Python 3 (stdlib only), AppleScript (`osacompile`), XDG desktop entries, Claude Code plugin format (plugin.json, hooks.json, commands).

**Spec:** `docs/superpowers/specs/2026-06-03-grab-plugin-design.md`

## File structure

```
claude-copy-plugin/
├── .claude-plugin/plugin.json     # plugin manifest (name: grab)
├── commands/
│   ├── setup.md                   # /grab:setup
│   └── uninstall.md               # /grab:uninstall
├── hooks/hooks.json               # SessionStart hook declaration
├── instruction.md                 # the injected copy-link instruction (single source of truth)
├── scripts/
│   ├── grab_handler.py            # shared URI → clipboard logic (testable core)
│   ├── session-start.sh           # detection + instruction injection
│   ├── install-macos.sh
│   ├── uninstall-macos.sh
│   ├── install-linux.sh
│   └── uninstall-linux.sh
├── tests/test_grab_handler.py     # unittest suite for the handler
└── README.md
```

---

### Task 1: Plugin scaffold

**Files:**
- Create: `.claude-plugin/plugin.json`

- [ ] **Step 1: Write the manifest**

```json
{
  "name": "grab",
  "version": "0.1.0",
  "description": "Click-to-copy 📋 links in Claude Code output via a custom grab: URI scheme",
  "author": {
    "name": "Antoine Lépée"
  }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python3 -m json.tool .claude-plugin/plugin.json`
Expected: pretty-printed JSON, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: plugin manifest"
```

---

### Task 2: URI handler core (`grab_handler.py`) — TDD

**Files:**
- Create: `scripts/grab_handler.py`
- Test: `tests/test_grab_handler.py`

The handler receives a `grab:` URI as argv[1]. Inline mode: percent-decoded payload → clipboard. File mode (`file=` prefix): read the referenced file, restricted to `/tmp/grab/` and `$TMPDIR/grab/`. It never executes payload content.

- [ ] **Step 1: Write the failing tests**

`tests/test_grab_handler.py`:

```python
"""Tests for the grab: URI handler payload resolution."""
import os
import sys
import tempfile
import unittest
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from grab_handler import resolve_payload


class ResolveInlineTest(unittest.TestCase):
    def test_simple_content(self):
        self.assertEqual(resolve_payload("grab:hello%20world"), b"hello world")

    def test_multiline_and_quotes(self):
        content = 'echo "a"\necho \'b\''
        encoded = urllib.parse.quote(content, safe="")
        self.assertEqual(resolve_payload("grab:" + encoded), content.encode())

    def test_utf8(self):
        self.assertEqual(resolve_payload("grab:caf%C3%A9"), "café".encode())

    def test_normalized_double_slash(self):
        # Some launchers normalize scheme:payload to scheme://payload.
        self.assertEqual(resolve_payload("grab://hello"), b"hello")

    def test_rejects_other_scheme(self):
        with self.assertRaises(ValueError):
            resolve_payload("copy:hello")


class ResolveFileTest(unittest.TestCase):
    def setUp(self):
        os.makedirs("/tmp/grab", exist_ok=True)

    def test_reads_file_in_allowed_dir(self):
        fd, path = tempfile.mkstemp(dir="/tmp/grab", suffix=".txt")
        with os.fdopen(fd, "wb") as fh:
            fh.write(b"big payload")
        self.addCleanup(os.remove, path)
        uri = "grab:file=" + urllib.parse.quote(path, safe="")
        self.assertEqual(resolve_payload(uri), b"big payload")

    def test_rejects_path_outside_allowed_dir(self):
        uri = "grab:file=" + urllib.parse.quote("/etc/hosts", safe="")
        with self.assertRaises(ValueError):
            resolve_payload(uri)

    def test_rejects_symlink_escaping_allowed_dir(self):
        link = "/tmp/grab/escape-link"
        if os.path.lexists(link):
            os.remove(link)
        os.symlink("/etc/hosts", link)
        self.addCleanup(os.remove, link)
        uri = "grab:file=" + urllib.parse.quote(link, safe="")
        with self.assertRaises(ValueError):
            resolve_payload(uri)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'grab_handler'`.

- [ ] **Step 3: Implement the handler**

`scripts/grab_handler.py`:

```python
#!/usr/bin/env python3
"""grab: URI handler.

Receives a grab: URI as its single argument, resolves the payload
(inline percent-encoded content, or a file= reference restricted to
the grab temp directories) and pipes it to the system clipboard.

It decodes/reads and copies — it never executes anything.
"""
import os
import shutil
import subprocess
import sys
import urllib.parse

SCHEME = "grab:"


def allowed_dirs():
    """Directories from which file= payloads may be read."""
    dirs = ["/tmp/grab"]
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        dirs.append(os.path.join(tmpdir, "grab"))
    return [os.path.realpath(d) for d in dirs]


def resolve_payload(uri):
    """Return the bytes to copy for a grab: URI.

    Raises ValueError for a non-grab URI or a file= path outside
    the allowed directories.
    """
    if not uri.startswith(SCHEME):
        raise ValueError(f"not a {SCHEME} URI: {uri!r}")
    payload = uri[len(SCHEME):]
    # Some launchers normalize scheme:payload to scheme://payload.
    # Inline payloads never start with '/' (aggressive encoding turns
    # '/' into %2F), so leading slashes can only come from that.
    payload = payload.lstrip("/")
    if payload.startswith("file="):
        path = os.path.realpath(urllib.parse.unquote(payload[len("file="):]))
        if not any(path.startswith(d + os.sep) for d in allowed_dirs()):
            raise ValueError(f"file payload outside allowed dirs: {path!r}")
        with open(path, "rb") as fh:
            return fh.read()
    return urllib.parse.unquote(payload).encode()


def clipboard_cmd():
    """Pick the clipboard command for the current platform."""
    if sys.platform == "darwin":
        return ["pbcopy"]
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
        return ["wl-copy"]
    if shutil.which("xclip"):
        return ["xclip", "-selection", "clipboard"]
    raise RuntimeError("no clipboard tool found (need wl-copy or xclip)")


def main(argv):
    if len(argv) != 2:
        print("usage: grab_handler.py <grab-uri>", file=sys.stderr)
        return 2
    try:
        data = resolve_payload(argv[1])
        subprocess.run(clipboard_cmd(), input=data, check=True)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"grab: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: 8 tests, OK.

Note (macOS): `/tmp` is a symlink to `/private/tmp`; both sides go through `os.path.realpath`, so the allowed-dir check still matches. If `test_reads_file_in_allowed_dir` fails on a path mismatch, that invariant broke — fix the code, not the test.

- [ ] **Step 5: Smoke-test the clipboard end of the chain (macOS)**

Run: `python3 scripts/grab_handler.py "grab:test%20ok" && pbpaste`
Expected: prints `test ok`.

- [ ] **Step 6: Commit**

```bash
git add scripts/grab_handler.py tests/test_grab_handler.py
git commit -m "feat: grab URI handler core with inline and file payloads"
```

---

### Task 3: Injected instruction (`instruction.md`)

**Files:**
- Create: `instruction.md`

Single source of truth for the instruction the hook injects. Kept in its own file so it can be tuned without touching shell.

- [ ] **Step 1: Write the instruction**

`instruction.md`:

````markdown
<grab-plugin>
When you output content the user will likely want to copy verbatim — a command to run, a code snippet, a draft message (Slack, email), text to paste elsewhere — append immediately after it a markdown link `[📋](grab:<payload>)`.

Rules:
- One link per copyable block. The payload is the exact displayed content, no added decoration.
- Percent-encode aggressively: every character outside `[A-Za-z0-9._~-]` becomes `%XX` (UTF-8 bytes). Spaces, newlines and quotes must all be encoded.
- If the content exceeds ~1500 characters, do not inline it. Create a temp file with a single Bash command (quoted heredoc: content is preserved verbatim):

```bash
mkdir -p /tmp/grab; f=$(mktemp /tmp/grab/XXXXXX.txt); cat > "$f" <<'GRAB_EOF'
<content>
GRAB_EOF
echo "$f"
```

  then emit `[📋](grab:file=<percent-encoded path>)` using the echoed path.
- Do not add links inside content that is itself going to be copied, and never for secrets.
</grab-plugin>
````

- [ ] **Step 2: Commit**

```bash
git add instruction.md
git commit -m "feat: copy-link instruction injected at session start"
```

---

### Task 4: SessionStart hook

**Files:**
- Create: `scripts/session-start.sh`
- Create: `hooks/hooks.json`

- [ ] **Step 1: Write the hook script**

`scripts/session-start.sh`:

```bash
#!/usr/bin/env bash
# SessionStart hook: inject the grab link instruction when the grab:
# URI handler is installed; otherwise hint at /grab:setup.
set -uo pipefail

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
  context="$(cat "${CLAUDE_PLUGIN_ROOT}/instruction.md")"
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
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/session-start.sh`

- [ ] **Step 3: Write the hook declaration**

`hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/scripts/session-start.sh\""
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: Test the not-installed branch**

Run: `CLAUDE_PLUGIN_ROOT="$PWD" HOME=/nonexistent bash scripts/session-start.sh | python3 -m json.tool`
Expected: valid JSON whose `additionalContext` contains "not installed" (handler app won't exist under the fake HOME).

- [ ] **Step 5: Test the installed branch (simulated)**

Run: `mkdir -p /tmp/fakehome/Applications/GrabHandler.app && CLAUDE_PLUGIN_ROOT="$PWD" HOME=/tmp/fakehome bash scripts/session-start.sh | python3 -c "import json,sys; print(json.load(sys.stdin)['hookSpecificOutput']['additionalContext'][:40])" && rm -rf /tmp/fakehome`
Expected: prints the start of the instruction (`<grab-plugin>` …).

- [ ] **Step 6: Commit**

```bash
git add scripts/session-start.sh hooks/hooks.json
git commit -m "feat: SessionStart hook with handler detection"
```

---

### Task 5: macOS install/uninstall scripts

**Files:**
- Create: `scripts/install-macos.sh`
- Create: `scripts/uninstall-macos.sh`

- [ ] **Step 1: Write the install script**

`scripts/install-macos.sh`:

```bash
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
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier dev.alepee.grab-handler" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes array" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0 dict" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLName string GrabClipboard" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes array" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string grab" "$PLIST"

"$LSREGISTER" -f "$APP"

echo "Installed $APP and registered the grab: scheme."
echo "Self-test: opening grab:test%20ok — paste somewhere to verify the clipboard contains 'test ok'."
open "grab:test%20ok"
```

- [ ] **Step 2: Write the uninstall script**

`scripts/uninstall-macos.sh`:

```bash
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
```

- [ ] **Step 3: Make them executable and syntax-check**

Run: `chmod +x scripts/install-macos.sh scripts/uninstall-macos.sh && bash -n scripts/install-macos.sh && bash -n scripts/uninstall-macos.sh`
Expected: no output, exit 0. (Full run is Task 9 — end-to-end on this machine.)

- [ ] **Step 4: Commit**

```bash
git add scripts/install-macos.sh scripts/uninstall-macos.sh
git commit -m "feat: macOS install/uninstall scripts"
```

---

### Task 6: Linux install/uninstall scripts

**Files:**
- Create: `scripts/install-linux.sh`
- Create: `scripts/uninstall-linux.sh`

- [ ] **Step 1: Write the install script**

`scripts/install-linux.sh`:

```bash
#!/usr/bin/env bash
# Install the grab: URI handler on Linux: a .desktop entry that
# forwards the URI to grab_handler.py, registered for the grab scheme.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HANDLER_DIR="$HOME/.local/share/grab"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP="$APPS_DIR/grab-handler.desktop"

if ! command -v wl-copy >/dev/null 2>&1 && ! command -v xclip >/dev/null 2>&1; then
  echo "error: need wl-copy (Wayland) or xclip (X11) installed." >&2
  exit 1
fi

mkdir -p "$HANDLER_DIR" "$APPS_DIR"
cp "$SCRIPT_DIR/grab_handler.py" "$HANDLER_DIR/grab_handler.py"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Grab URI Handler
Exec=python3 $HANDLER_DIR/grab_handler.py %u
MimeType=x-scheme-handler/grab;
NoDisplay=true
EOF

xdg-mime default grab-handler.desktop x-scheme-handler/grab
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" || true
fi

echo "Installed $DESKTOP and registered the grab: scheme."
echo "Self-test: opening grab:test%20ok — paste somewhere to verify the clipboard contains 'test ok'."
xdg-open "grab:test%20ok"
```

- [ ] **Step 2: Write the uninstall script**

`scripts/uninstall-linux.sh`:

```bash
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
```

- [ ] **Step 3: Make them executable and syntax-check**

Run: `chmod +x scripts/install-linux.sh scripts/uninstall-linux.sh && bash -n scripts/install-linux.sh && bash -n scripts/uninstall-linux.sh && { command -v shellcheck >/dev/null && shellcheck scripts/*.sh || echo "shellcheck not available, skipped"; }`
Expected: exit 0; shellcheck clean or skipped. (No Linux machine here — real-machine validation happens when Guillaume tries it; the shared Python core is already unit-tested.)

- [ ] **Step 4: Commit**

```bash
git add scripts/install-linux.sh scripts/uninstall-linux.sh
git commit -m "feat: Linux install/uninstall scripts"
```

---

### Task 7: Slash commands

**Files:**
- Create: `commands/setup.md`
- Create: `commands/uninstall.md`

- [ ] **Step 1: Write /grab:setup**

`commands/setup.md`:

```markdown
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
```

- [ ] **Step 2: Write /grab:uninstall**

`commands/uninstall.md`:

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add commands/setup.md commands/uninstall.md
git commit -m "feat: setup and uninstall slash commands"
```

---

### Task 8: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

```markdown
# grab — click-to-copy 📋 links in Claude Code

Tired of fighting soft-wrap and the gutter to copy a command from Claude's output? `grab` makes Claude append a clickable 📋 link after every copyable block (commands, code snippets, draft messages). Clicking it puts the exact content in your clipboard.

Based on a hack by Guillaume Rams: OSC 8 hyperlinks + a custom `grab:` URI scheme handled at the OS level.

## Requirements

- macOS or Linux (Windows not supported).
- A terminal with OSC 8 hyperlink support: iTerm2, Ghostty, Kitty, WezTerm, VS Code/Cursor integrated terminal. **Terminal.app does not support OSC 8** — links won't be clickable there.
- `python3` on PATH. Linux also needs `wl-copy` (Wayland) or `xclip` (X11).

## Install

1. Install the plugin (marketplace or `--plugin-dir`).
2. Run `/grab:setup` once. It registers the `grab:` URI scheme (an applet in `~/Applications` on macOS, a `.desktop` entry on Linux) and runs a clipboard self-test.
3. New sessions inject the link instruction automatically; without the handler installed you only get a one-line hint instead of dead links.

To remove everything: `/grab:uninstall`.

## How it works

- A SessionStart hook detects the handler and instructs Claude to append `[📋](grab:<percent-encoded content>)` after copyable blocks.
- Clicking the link hands the URI to `grab_handler.py`, which decodes the payload and pipes it to `pbcopy` / `wl-copy` / `xclip`.
- Content over ~1500 characters goes through a temp file: Claude writes `/tmp/grab/<mktemp>.txt` and links `grab:file=<path>`; the handler reads the file. Paths are restricted to `/tmp/grab/` (and `$TMPDIR/grab/`).

## Security

The handler decodes/reads and copies — it never executes anything. File mode rejects any path (after symlink resolution) outside the dedicated grab temp directories.

## Known limitations

- First click: iTerm2 / VS Code ask once to confirm opening an unknown URI scheme. Allow and remember.
- Very long inline URIs can be truncated by some terminals — hence the file fallback threshold.
- `/tmp/grab/` files persist until reboot (so links survive re-clicks).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README"
```

---

### Task 9: End-to-end verification on this machine (macOS)

**Files:** none (verification only; fix-up commits if needed)

- [ ] **Step 1: Run the installer**

Run: `bash scripts/install-macos.sh`
Expected: "Installed … registered the grab: scheme.", then macOS may prompt to allow opening GrabHandler — allow it.

- [ ] **Step 2: Verify the self-test**

Run: `pbpaste`
Expected: `test ok`. If the prompt ate the first open, re-run `open "grab:test%20ok"` then `pbpaste`.

- [ ] **Step 3: Verify file mode**

Run: `mkdir -p /tmp/grab && f=$(mktemp /tmp/grab/XXXXXX.txt) && printf 'multi\nline payload' > "$f" && open "grab:file=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$f")" && sleep 1 && pbpaste`
Expected: `multi` + newline + `line payload`.

- [ ] **Step 4: Verify the hook detects the installed handler**

Run: `CLAUDE_PLUGIN_ROOT="$PWD" bash scripts/session-start.sh | python3 -c "import json,sys; print(json.load(sys.stdin)['hookSpecificOutput']['additionalContext'][:40])"`
Expected: prints `<grab-plugin>` …

- [ ] **Step 5: Live session test**

Install the plugin locally (`claude --plugin-dir` pointing at this repo, or via the user's marketplace flow), start a new session in iTerm2 or Ghostty, ask Claude for a command and a long draft. Verify: 📋 links render, clicking copies the exact content, file fallback used beyond ~1500 chars.

- [ ] **Step 6: Commit any fixes discovered**

```bash
git add -A
git commit -m "fix: adjustments from end-to-end verification"
```

(Skip if nothing changed.)
