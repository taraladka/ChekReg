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


class TestOrgProfile(unittest.TestCase):
    def test_is_inactive(self):
        from datetime import datetime, timezone, timedelta
        org = engine.OrgProfile("TestOrg")
        
        # Not seen -> not inactive
        org.last_seen = None
        self.assertFalse(org.is_inactive)
        
        # Seen 200 days ago -> inactive
        past_date = datetime.now(timezone.utc) - timedelta(days=200)
        org.last_seen = past_date.strftime("%a, %d %b %Y %H:%M:%S %z")
        self.assertTrue(org.is_inactive)
        
        # Seen 10 days ago -> active
        recent_date = datetime.now(timezone.utc) - timedelta(days=10)
        org.last_seen = recent_date.strftime("%a, %d %b %Y %H:%M:%S %z")
        self.assertFalse(org.is_inactive)

    def test_is_high_volume(self):
        org = engine.OrgProfile("TestOrg", total_emails=21)
        self.assertTrue(org.is_high_volume)
        org.total_emails = 20
        self.assertFalse(org.is_high_volume)


class TestReportScore(unittest.TestCase):
    def test_empty_score(self):
        report = engine.Report({}, "test@example.com", hibp_checked=False)
        self.assertEqual(report.score(), 100)
        
    def test_mixed_score(self):
        # 1 perfect, 1 breached, 1 inactive, 1 noisy
        o1 = engine.OrgProfile("O1", total_emails=1, has_account=True)
        o2 = engine.OrgProfile("O2", total_emails=1, breached=True)
        
        from datetime import datetime, timezone, timedelta
        past_date = datetime.now(timezone.utc) - timedelta(days=200)
        o3 = engine.OrgProfile("O3", total_emails=1, has_account=True, last_seen=past_date.strftime("%a, %d %b %Y %H:%M:%S %z"))
        
        o4 = engine.OrgProfile("O4", total_emails=50)
        
        orgs = {"o1": o1, "o2": o2, "o3": o3, "o4": o4}
        report = engine.Report(orgs, "test@example.com", hibp_checked=False)
        
        # Total = 4. Breached = 1 (25%). Inactive = 1 (25%). Noisy = 1 (25%).
        # Score = 100 - (0.25 * 50) - (0.25 * 30) - (0.25 * 20) = 100 - 12.5 - 7.5 - 5 = 75
        self.assertEqual(report.score(), 75)


if __name__ == "__main__":
    unittest.main()
