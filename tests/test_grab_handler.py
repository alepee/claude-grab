"""Tests for the grab: URI handler payload resolution."""
import os
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from grab_handler import clipboard_cmd, main, resolve_payload


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
    # On macOS /tmp is a symlink to /private/tmp; the allowed-dir check works
    # because realpath is applied to both the candidate path and the allowed dirs.
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


class MainTest(unittest.TestCase):
    def test_wrong_argc_returns_2(self):
        self.assertEqual(main(["grab_handler.py"]), 2)


class ClipboardCmdTest(unittest.TestCase):
    def test_raises_when_no_clipboard_tool(self):
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch("grab_handler.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                clipboard_cmd()


if __name__ == "__main__":
    unittest.main()
