"""
Unit tests for engine.py core extraction logic.
Run with: python -m unittest discover tests/
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine


class TestDomainExtraction(unittest.TestCase):
    def test_simple_domain(self):
        import tldextract
        ext = tldextract.extract("newsletter@updates.spotify.com")
        root = f"{ext.domain}.{ext.suffix}"
        self.assertEqual(root, "spotify.com")

    def test_subdomain_stripped(self):
        import tldextract
        ext = tldextract.extract("noreply@mail.github.com")
        root = f"{ext.domain}.{ext.suffix}"
        self.assertEqual(root, "github.com")

    def test_country_tld(self):
        import tldextract
        ext = tldextract.extract("no-reply@amazon.co.uk")
        root = f"{ext.domain}.{ext.suffix}"
        self.assertEqual(root, "amazon.co.uk")


class TestUnsubscribeParsing(unittest.TestCase):
    def test_angle_bracket_url(self):
        import re
        header = "<https://example.com/unsubscribe?uid=123>, <mailto:unsub@example.com>"
        match = re.search(r'<(https?://[^>]+)>', header)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "https://example.com/unsubscribe?uid=123")

    def test_no_http_link(self):
        import re
        header = "<mailto:unsub@example.com>"
        match = re.search(r'<(https?://[^>]+)>', header)
        self.assertIsNone(match)

    def test_empty_header(self):
        import re
        match = re.search(r'<(https?://[^>]+)>', "")
        self.assertIsNone(match)


class TestScannerLifecycle(unittest.TestCase):
    def test_close_before_auth_does_not_raise(self):
        """close() must be safe to call even if authentication never ran."""
        scanner = engine.Scanner("test@example.com", quiet=True)
        try:
            scanner.close()
        except Exception as e:
            self.fail(f"scanner.close() raised unexpectedly: {e}")

    def test_credential_zeroed_after_close(self):
        scanner = engine.Scanner("test@example.com", quiet=True)
        scanner._imap_pass = "secret"
        scanner.close()
        self.assertIsNone(scanner._imap_pass)


if __name__ == "__main__":
    unittest.main()
