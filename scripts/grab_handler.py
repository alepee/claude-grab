#!/usr/bin/env python3
"""grab: URI handler.

Receives a grab: URI as its single argument, percent-decodes the inline
payload and pipes it to the system clipboard.

It decodes and copies — it never executes anything, never touches files.
"""
import os
import shutil
import subprocess
import sys
import urllib.parse

SCHEME = "grab:"


def resolve_payload(uri):
    """Return the bytes to copy for a grab: URI.

    Raises ValueError for a non-grab URI.
    """
    if not uri.startswith(SCHEME):
        raise ValueError(f"not a {SCHEME} URI: {uri!r}")
    payload = uri[len(SCHEME):]
    # Some launchers normalize scheme:payload to scheme://payload.
    # Inline payloads never start with '/' (aggressive encoding turns
    # '/' into %2F), so leading slashes can only come from that.
    payload = payload.lstrip("/")
    return urllib.parse.unquote_to_bytes(payload)


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
