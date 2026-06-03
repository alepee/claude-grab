# grab — click-to-copy 📋 links in Claude Code

Tired of fighting soft-wrap and the gutter to copy a command from Claude's output? `grab` makes Claude append a clickable 📋 link after every copyable block (commands, code snippets, draft messages). Clicking it puts the exact content in your clipboard.

Based on a hack by Guillaume Rams: OSC 8 hyperlinks + a custom `grab:` URI scheme handled at the OS level.

## Requirements

- macOS or Linux (Windows not supported).
- A terminal that makes `scheme:` URIs clickable — via OSC 8 hyperlinks or plain-text URI detection (cmd+click): iTerm2, Ghostty, Kitty, WezTerm, VS Code/Cursor integrated terminal. **Terminal.app and Warp are not supported**: Terminal.app lacks OSC 8, and Warp neither renders OSC 8 ([warpdotdev/Warp#4194](https://github.com/warpdotdev/Warp/issues/4194), fix underway in [#11885](https://github.com/warpdotdev/warp/pull/11885)) nor detects custom URI schemes in plain text. Note: Claude Code currently prints links as plain text rather than OSC 8 ([claude-code#13008](https://github.com/anthropics/claude-code/issues/13008)), so clickability relies on the terminal's plain-text URI detection — Warp will need both fixes before grab links work there.
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
