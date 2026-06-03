# grab — click-to-copy links in Claude Code output

**Date:** 2026-06-03
**Status:** Approved design

## Problem

Copying content from Claude Code's terminal output (commands, code snippets, draft messages) is painful: soft-wrap and the gutter corrupt selections. Origin: a hack shared by Guillaume Rams on Slack using a custom `copy:` URI scheme + OSC 8 hyperlinks.

## Goal

A shareable Claude Code plugin named `grab` that:

1. Registers a custom `grab:` URI scheme at the OS level whose handler decodes a payload and puts it in the clipboard.
2. Instructs Claude (via a SessionStart hook) to append a clickable `[📋](grab:...)` link after any copyable output.
3. Installs in two steps: install the plugin, run `/grab:setup` once.

Target OS: **macOS + Linux**. Windows out of scope.
Target terminals: any with OSC 8 hyperlink support (iTerm2, Ghostty, Kitty, WezTerm, VS Code/Cursor integrated terminal). Terminal.app unsupported (no OSC 8) — documented limitation.

## Why `grab:`

Short, says what it does, near-zero collision risk with registered or common schemes.

## Plugin structure

```
claude-copy-plugin/
├── .claude-plugin/plugin.json     # name: "grab"
├── commands/
│   ├── setup.md                   # exposed as /grab:setup
│   └── uninstall.md               # exposed as /grab:uninstall
├── hooks/hooks.json               # SessionStart hook declaration
├── scripts/
│   ├── session-start.sh           # handler detection + instruction injection
│   ├── install-macos.sh
│   ├── install-linux.sh
│   ├── uninstall-macos.sh
│   └── uninstall-linux.sh
└── README.md                      # install, supported terminals, limitations
```

## Components

### 1. SessionStart hook (`scripts/session-start.sh`)

Detects whether the `grab:` handler is installed:

- macOS: `~/Applications/GrabHandler.app` exists.
- Linux: `xdg-mime query default x-scheme-handler/grab` returns non-empty.

If installed → injects the copy-link instruction as `additionalContext` (see below).
If absent → injects a single line: "grab: handler not installed, run /grab:setup to enable clipboard links." No dead links.

### 2. Injected instruction

> When you produce content the user will likely want to copy verbatim — a command to run, a code snippet, a draft message (Slack, email), text to paste elsewhere — append right after it a link `[📋](grab:<payload>)`. One link per copyable block. The payload must be the exact displayed content, no added decoration, percent-encoded aggressively: every character outside `[A-Za-z0-9._~-]` becomes `%XX`.
>
> If the content exceeds ~1500 characters: write it to a temp file instead and emit `[📋](grab:file=<percent-encoded path>)`. Create the file with a single Bash command using `mktemp` (atomic, collision-free naming) and a quoted heredoc (content is preserved verbatim, no shell interpolation), and echo the path:
>
> ```bash
> mkdir -p /tmp/grab; f=$(mktemp /tmp/grab/XXXXXX.txt); cat > "$f" <<'GRAB_EOF'
> <content>
> GRAB_EOF
> echo "$f"
> ```

`mktemp` guarantees unique names without the agent tracking any counter or the hook interpolating a session id. Works identically on macOS (BSD) and Linux (GNU).

Aggressive encoding is what makes spaces, newlines, and quotes survive the URI round-trip.

### 3. `/grab:setup` command (`commands/setup.md`)

Markdown command instructing Claude to run the install script matching the current OS (`$CLAUDE_PLUGIN_ROOT/scripts/install-macos.sh` or `install-linux.sh`). Scripts are deterministic.

**macOS (`install-macos.sh`):**
- `osacompile` generates `GrabHandler.app` in `~/Applications` from an AppleScript `on open location` handler.
- The handler strips the scheme, decodes via `python3 -c "urllib.parse.unquote(...)"`, pipes to `pbcopy`.
- `PlistBuddy` adds `CFBundleURLTypes` for scheme `grab` to the app's `Info.plist`.
- `lsregister -f` registers the app with LaunchServices.

**Linux (`install-linux.sh`):**
- Detects clipboard tool: `wl-copy` (Wayland) or `xclip` (X11); aborts with a clear message if neither.
- Writes `~/.local/share/applications/grab-handler.desktop` (python3 decode → clipboard tool).
- `xdg-mime default grab-handler.desktop x-scheme-handler/grab`.

**Both scripts end with a self-test:** trigger `open "grab:test%20ok"` / `xdg-open "grab:test%20ok"`, then ask the user to paste and confirm the clipboard contains `test ok`.

### 3b. `/grab:uninstall` command (`commands/uninstall.md`)

Mirror of setup: runs the uninstall script matching the current OS. Removes everything the install created, nothing else.

**macOS (`uninstall-macos.sh`):**
- `lsregister -u` to unregister, then remove `~/Applications/GrabHandler.app`.
- Remove `/tmp/grab/` if present.

**Linux (`uninstall-linux.sh`):**
- Remove `~/.local/share/applications/grab-handler.desktop`.
- Drop the `x-scheme-handler/grab` entries from `~/.config/mimeapps.list`.
- Remove `/tmp/grab/` if present.

After uninstall, the SessionStart hook naturally falls back to the "handler not installed" hint (or stops entirely once the plugin is removed).

### 4. Payloads and file fallback

**Inline (nominal, content ≤ ~1500 chars):** `grab:<percent-encoded content>` — handler decodes and copies.

**File fallback (large content):** Claude writes the content to `/tmp/grab/<mktemp-name>.txt`, then emits `[📋](grab:file=<percent-encoded path>)`. The handler recognizes the `file=` prefix, reads the file, pipes its content to the clipboard. Tiny URI, unbounded payload, click stays the trigger (no unsolicited clipboard overwrite).

- **No ambiguity:** aggressive encoding turns any inline `=` into `%3D`, so a raw `file=` prefix can only be a path reference.
- **Security:** the handler only accepts paths under `/tmp/grab/` (and `$TMPDIR/grab/` on macOS). Anything else is rejected. Prevents a malicious `grab:file=` link from siphoning arbitrary readable files into the clipboard.
- **Cleanup:** no deletion after copy (re-click works); `/tmp` is purged on reboot.

## Security model

The handler **decodes/reads and copies — never executes anything**. No eval, no shell interpretation of the payload. File mode is path-restricted to the dedicated tmp directory.

## Known limitations (documented in README)

- Terminal.app: no OSC 8, links not clickable.
- First click: iTerm2 / VS Code prompt once to confirm opening an unknown URI scheme.
- Very long inline URIs (multi-KB) may be silently truncated by some terminals — hence the 1500-char threshold and file fallback.

## Testing

Manual:
1. Install self-test (clipboard round-trip via `open` / `xdg-open`).
2. Real Claude Code session: verify the instruction produces clickable 📋 links in iTerm2/Ghostty, inline and file modes, multiline content survives.
