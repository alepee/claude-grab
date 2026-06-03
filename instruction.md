<grab-plugin>
When you output content the user will likely want to copy verbatim — a command to run, a short snippet, a one-liner to paste elsewhere — append immediately after it a markdown link `[Grab 🫳](grab:<payload>)`.

Rules:
- One link per copyable block. The payload is the exact displayed content, no added decoration.
- Percent-encode aggressively: every character outside `[A-Za-z0-9._~-]` becomes `%XX` (UTF-8 bytes). Spaces, newlines and quotes must all be encoded.
- Inline only: if the content exceeds ~1500 characters, do not emit a link at all. Never write temp files for this — for long content, offer to pipe it to the clipboard tool (pbcopy/wl-copy/xclip) directly instead.
- Do not add links inside content that is itself going to be copied, and never for secrets.
</grab-plugin>
