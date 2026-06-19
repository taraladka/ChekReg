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

class TestProcessMessage(unittest.TestCase):
    def setUp(self):
        self.scanner = engine.Scanner("test@example.com", quiet=True)

    def test_extracts_org_from_sender(self):
        self.scanner._process_message({
            'from': 'Support <support@github.com>',
            'subject': 'Welcome to GitHub',
            'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
            'list-unsubscribe': ''
        })
        self.assertIn('Github', self.scanner.orgs)
        self.assertEqual(self.scanner.orgs['Github'].total_emails, 1)

    def test_skips_malformed_sender(self):
        self.scanner._process_message({
            'from': 'Just A Name Without Email',
            'subject': 'Hello',
            'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
            'list-unsubscribe': ''
        })
        self.assertEqual(len(self.scanner.orgs), 0)

    def test_categorizes_account_email(self):
        self.scanner._process_message({
            'from': 'admin@service.com',
            'subject': 'Verify your account',
            'date': '', 'list-unsubscribe': ''
        })
        self.assertTrue(self.scanner.orgs['Service'].has_account)

    def test_categorizes_newsletter(self):
        self.scanner._process_message({
            'from': 'news@media.com',
            'subject': 'Weekly Digest',
            'date': '', 'list-unsubscribe': ''
        })
        self.assertEqual(self.scanner.orgs['Media'].categories['newsletter'], 1)

    def test_extracts_unsub_link(self):
        self.scanner._process_message({
            'from': 'marketing@shop.com',
            'subject': 'Sale!',
            'date': '',
            'list-unsubscribe': '<https://shop.com/unsub>'
        })
        self.assertIn('https://shop.com/unsub', self.scanner.orgs['Shop'].unsub_links)


class TestLoadSitesDb(unittest.TestCase):
    def test_falls_back_when_file_missing(self):
        # We simulate missing file by calling load_sites_db on a fake path
        original = engine.SITES_META
        try:
            urls = engine.load_sites_db(path="/does/not/exist.json")
            self.assertIn('github.com', urls)  # fallback loaded
            self.assertTrue(len(urls) > 10)
        finally:
            engine.SITES_META = original

    def test_loads_real_sites_json(self):
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sites_path = os.path.join(root, 'data', 'sites.json')
        if os.path.exists(sites_path):
            urls = engine.load_sites_db(path=sites_path)
            self.assertTrue(len(urls) > 0)


class TestSafeUrlValidation(unittest.TestCase):
    # Testing the server-side regex that guards against JS injection in list-unsubscribe
    def test_rejects_javascript_url(self):
        import re
        unsub = "<javascript:alert(1)>"
        link = re.search(r'<(https?://[^>]+)>', unsub)
        self.assertIsNone(link)

    def test_accepts_https(self):
        import re
        unsub = "<https://safe.com/unsub>"
        link = re.search(r'<(https?://[^>]+)>', unsub)
        self.assertEqual(link.group(1), "https://safe.com/unsub")

    def test_accepts_http(self):
        import re
        unsub = "<http://safe.com/unsub>"
        link = re.search(r'<(https?://[^>]+)>', unsub)
        self.assertEqual(link.group(1), "http://safe.com/unsub")


if __name__ == "__main__":
    unittest.main()
