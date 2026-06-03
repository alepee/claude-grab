"""Tests for the grab: URI handler payload resolution."""
import os
import sys
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

    def test_legacy_file_payload_is_treated_as_plain_text(self):
        # The file= mode was removed: such a payload is just inline content now.
        self.assertEqual(resolve_payload("grab:file%3D%2Fetc%2Fhosts"), b"file=/etc/hosts")


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
