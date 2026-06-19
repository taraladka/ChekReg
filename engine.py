#!/usr/bin/env python3
"""
chekreg — Digital Footprint Mapper
Scans your email via IMAP to discover and audit every account tied to your address.

Usage:
    python chekreg.py          # Interactive menu (choose CLI or Web GUI)
    python chekreg.py --cli    # Launch Terminal Interface directly
    python chekreg.py --web    # Launch Web Dashboard directly
"""

import os, re, sys, json, urllib.request, urllib.error, urllib.parse, logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import imaplib, email
from email.header import decode_header

# ── optional deps ──────────────────────────────────────────────────────────────
try:
    import tldextract
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    print("\n[!] Missing dependencies. Run:\n")
    print("    pip install tldextract colorama\n")
    sys.exit(1)

# ── terminal colours ───────────────────────────────────────────────────────────
R  = Fore.RED;    Y = Fore.YELLOW;  G = Fore.GREEN
C  = Fore.CYAN;   M = Fore.MAGENTA; B = Fore.BLUE
W  = Fore.WHITE;  D = Style.DIM;    BR = Style.BRIGHT
RS = Style.RESET_ALL

def clr(text, *styles):
    return "".join(styles) + str(text) + RS

def bar(filled, total=20, fill="█", empty="░"):
    n = int((filled / max(total, 1)) * 20)
    return G + fill * n + D + empty * (20 - n) + RS

VERSION = "3.3"

# ── hardcoded fallback — used when sites.json is missing ───────────────────────
DELETION_URLS_FALLBACK = {
    # ── Big Tech ──
    'google.com':       'https://myaccount.google.com/delete-services-or-account',
    'microsoft.com':    'https://account.microsoft.com/closeaccount',
    'apple.com':        'https://privacy.apple.com/',
    # ── Social ──
    'facebook.com':     'https://www.facebook.com/help/delete_account',
    'facebookmail.com': 'https://www.facebook.com/help/delete_account',
    'instagram.com':    'https://www.instagram.com/accounts/remove/request/permanent/',
    'twitter.com':      'https://twitter.com/settings/account',
    'x.com':            'https://twitter.com/settings/account',
    'reddit.com':       'https://www.reddit.com/settings/account',
    'linkedin.com':     'https://www.linkedin.com/psettings/account-management',
    'pinterest.com':    'https://www.pinterest.com/settings/account',
    'snapchat.com':     'https://accounts.snapchat.com/accounts/delete_account',
    'tiktok.com':       'https://www.tiktok.com/setting/account',
    'tumblr.com':       'https://www.tumblr.com/settings/account',
    'quora.com':        'https://www.quora.com/settings',
    'meetup.com':       'https://www.meetup.com/account/',
    # ── Messaging ──
    'discord.com':      'https://discord.com/channels/@me',
    'slack.com':        'https://slack.com/help/articles/203953052',
    'telegram.org':     'https://my.telegram.org/auth?to=delete',
    'signal.org':       'https://support.signal.org/hc/en-us/articles/360007059752',
    # ── Dev & Tech ──
    'github.com':       'https://github.com/settings/admin',
    'gitlab.com':       'https://gitlab.com/-/profile/account',
    'bitbucket.org':    'https://bitbucket.org/account/settings/',
    'stackoverflow.com':'https://stackoverflow.com/users/delete/current',
    'npmjs.com':        'https://www.npmjs.com/settings/~/profile',
    'docker.com':       'https://hub.docker.com/settings/general',
    'vercel.com':       'https://vercel.com/account',
    'netlify.com':      'https://app.netlify.com/user/settings',
    'heroku.com':       'https://devcenter.heroku.com/articles/account-deletion',
    'replit.com':       'https://replit.com/account',
    # ── Productivity ──
    'notion.so':        'https://www.notion.so/profile/identity',
    'evernote.com':     'https://www.evernote.com/secure/SecuritySettings.action',
    'trello.com':       'https://trello.com/your/account',
    'canva.com':        'https://www.canva.com/settings/account',
    'medium.com':       'https://medium.com/me/settings',
    'grammarly.com':    'https://account.grammarly.com/deleteAccount',
    # ── Cloud Storage ──
    'dropbox.com':      'https://www.dropbox.com/account/delete',
    'box.com':          'https://account.box.com/api/oauth2/logout',
    'mega.nz':          'https://mega.nz/fm/account',
    # ── Streaming & Entertainment ──
    'spotify.com':      'https://support.spotify.com/us/article/closing-your-account/',
    'netflix.com':      'https://www.netflix.com/cancelplan',
    'twitch.tv':        'https://www.twitch.tv/user/delete-account',
    'hulu.com':         'https://secure.hulu.com/account',
    'soundcloud.com':   'https://soundcloud.com/settings/account',
    'vimeo.com':        'https://vimeo.com/settings/account/general',
    # ── Shopping ──
    'amazon.com':       'https://www.amazon.com/privacy/data-deletion',
    'ebay.com':         'https://www.ebay.com/help/account/your-account/closing-account?id=4660',
    'etsy.com':         'https://www.etsy.com/your/account',
    # ── Finance ──
    'paypal.com':       'https://www.paypal.com/myaccount/settings/',
    # ── Travel ──
    'airbnb.com':       'https://www.airbnb.com/account-settings',
    'booking.com':      'https://account.booking.com/mysettings',
    # ── Gaming ──
    'steampowered.com': 'https://help.steampowered.com/en/wizard/HelpDeleteAccount',
    'epicgames.com':    'https://www.epicgames.com/account/personal',
    'roblox.com':       'https://www.roblox.com/my/account#!/info',
    # ── Health & Fitness ──
    'myfitnesspal.com': 'https://www.myfitnesspal.com/account/delete_account',
    'strava.com':       'https://www.strava.com/account',
    # ── Dating ──
    'tinder.com':       'https://account.gotinder.com/deleteaccount',
    'bumble.com':       'https://bumble.com/en/help/how-do-i-delete-my-bumble-account',
}

# ── load external sites database ───────────────────────────────────────────────
def load_sites_db(path: str = None) -> tuple:
    """
    Load deletion URLs from the external sites.json file.
    Returns a flat dict of domain → URL.
    Falls back to DELETION_URLS_FALLBACK if the file is missing or invalid.
    """
    sites_path = path if path else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sites.json')
    if not os.path.exists(sites_path):
        return dict(DELETION_URLS_FALLBACK)

    try:
        with open(sites_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        sites = data.get('sites', {})
        result = {}
        for domain, info in sites.items():
            if isinstance(info, dict) and 'delete_url' in info:
                result[domain.lower()] = info['delete_url']
            elif isinstance(info, str):
                result[domain.lower()] = info

        # merge fallback entries for anything missing
        for domain, url in DELETION_URLS_FALLBACK.items():
            result.setdefault(domain, url)

        return result
    except (json.JSONDecodeError, IOError, KeyError):
        return dict(DELETION_URLS_FALLBACK)


def load_sites_metadata() -> dict:
    """
    Load the full sites metadata (name, category, etc.) from sites.json.
    Returns dict of domain → {name, delete_url, category}.
    """
    sites_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sites.json')
    if not os.path.exists(sites_path):
        return {}
    try:
        with open(sites_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('sites', {})
    except (json.JSONDecodeError, IOError):
        return {}


# Build the active deletion URLs (loaded once at startup)
DELETION_URLS = load_sites_db()
SITES_META    = load_sites_metadata()

PARENT_MAP = {
    'google.com': 'Google',     'youtube.com': 'Google',    'gmail.com': 'Google',
    'microsoft.com': 'Microsoft',
    'facebook.com': 'Facebook', 'facebookmail.com': 'Facebook / Instagram', 'instagram.com': 'Instagram',
    'spotify.com': 'Spotify',   'netflix.com': 'Netflix',    'amazon.com': 'Amazon',
    'twitter.com': 'X/Twitter', 'x.com': 'X/Twitter',
    'apple.com': 'Apple',       'icloud.com': 'Apple',
}

CATEGORIES = {
    'account':       ['verify', 'confirm', 'welcome', 'signup', 'sign up', 'activate', 'registration', 'thank you for joining'],
    'security':      ['password reset', 'reset your password', 'sign-in attempt', 'new login', 'security alert', '2fa', 'two-factor'],
    'transactional': ['receipt', 'invoice', 'order', 'shipment', 'payment', 'refund', 'subscription'],
    'newsletter':    ['unsubscribe', 'newsletter', 'digest', 'weekly', 'monthly', 'update'],
}

CAT_ICONS = {
    'account': '🔑', 'security': '🔒', 'transactional': '🧾', 'newsletter': '📰', 'unknown': '📧'
}

SITE_CAT_ICONS = {
    'social': '📱', 'entertainment': '🎬', 'dating': '💕', 'messaging': '💬',
    'forums': '🗣️', 'tech': '💻', 'gaming': '🎮', 'cloud': '☁️',
    'ai': '🤖', 'security': '🔐', 'finance': '💳', 'crypto': '🪙',
    'shopping': '🛒', 'business': '💼', 'jobs': '👔', 'food': '🍔',
    'travel': '✈️', 'health': '🏥', 'education': '📚', 'news': '📰',
    'productivity': '⚡', 'design': '🎨', 'telecom': '📡', 'automotive': '🚗',
    'real_estate': '🏠', 'government': '🏛️', 'music': '🎵', 'sports': '⚽',
    'kids': '👶', 'photo': '📸', 'video': '🎥', 'tools': '🔧', 'misc': '📦',
    'legal': '⚖️', 'weather': '🌤️',
    'startups & accounts': '🔑', 'newsletters': '📰', 'shopping & receipts': '🧾',
    'security alerts': '🔒', 'other/unknown': '📧'
}

# ── data model ─────────────────────────────────────────────────────────────────
@dataclass
class OrgProfile:
    name: str
    domains: Set[str]          = field(default_factory=set)
    total_emails: int          = 0
    categories: Counter        = field(default_factory=Counter)
    first_seen: Optional[str]  = None
    last_seen: Optional[str]   = None
    unsub_links: List[str]     = field(default_factory=list)
    has_account: bool          = False
    breached: bool             = False
    breach_names: List[str]    = field(default_factory=list)

    @property
    def is_high_volume(self): return self.total_emails > 20

    @property
    def is_inactive(self):
        if not self.last_seen:
            return False
        try:
            dt = parsedate_to_datetime(self.last_seen)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt) > timedelta(days=180)
        except Exception as e:
            logging.debug(f"is_inactive date parsing failed for '{self.last_seen}': {e}")
            return str(datetime.now().year) not in self.last_seen

    @property
    def primary_domain(self):
        return next(iter(self.domains), '')

    @property
    def dominant_category(self):
        if not self.categories: return 'unknown'
        return self.categories.most_common(1)[0][0]

    @property
    def final_category(self):
        # 1. Database Match
        for d in self.domains:
            if d in SITES_META and 'category' in SITES_META[d]:
                return SITES_META[d]['category']
        
        # 2. Behavior Match
        dom_cat = self.dominant_category
        if dom_cat == 'account':
            return 'startups & accounts'
        elif dom_cat == 'newsletter':
            return 'newsletters'
        elif dom_cat == 'transactional':
            return 'shopping & receipts'
        elif dom_cat == 'security':
            return 'security alerts'
        
        return 'other/unknown'

    @property
    def has_deletion_url(self):
        return any(d in DELETION_URLS for d in self.domains)

    def deletion_url(self):
        for d in self.domains:
            if d in DELETION_URLS:
                return DELETION_URLS[d]
        return None

# ── HIBP breach check ──────────────────────────────────────────────────────────
def check_hibp(email: str, api_key: str = None) -> dict:
    """
    Query HIBP for the given email.
    NOTE: As of 2024, this endpoint requires a paid API key (hibp-api-key header).
    Set the HIBP_API_KEY environment variable to enable breach checks.
    """
    if not api_key:
        api_key  = os.environ.get('HIBP_API_KEY', '')
    if not api_key:
        return {'_api_key_required': True}

    results  = {}
    try:
        encoded = urllib.parse.quote(email)
        url     = f"https://haveibeenpwned.com/api/v3/breachedaccount/{encoded}?truncateResponse=false"
        req     = urllib.request.Request(url, headers={
            'User-Agent':   f'chekreg-footprint-mapper/{VERSION}',
            'hibp-api-key': api_key,
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            for breach in data:
                domain = breach.get('Domain', '').lower()
                name   = breach.get('Name', '')
                if domain:
                    results.setdefault(domain, []).append(name)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            pass          # 404 = no breaches found — that's good
        elif e.code == 401:
            results['_api_key_required'] = True
        # 429 = rate limited, 503 = down — silently skip
    except Exception as e:
        logging.debug(f"HIBP network error: {e}")
    return results

# ── spinner ────────────────────────────────────────────────────────────────────
class Spinner:
    FRAMES = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
    def __init__(self, label, quiet=False):
        self.label = label
        self.i     = 0
        self.quiet = quiet

    def tick(self):
        if not self.quiet:
            print(f"\r  {C}{self.FRAMES[self.i % len(self.FRAMES)]}{RS} {self.label}  ", end="", flush=True)
            self.i += 1

    def done(self, msg=""):
        if not self.quiet:
            print(f"\r  {G}✓{RS} {self.label}{('  ' + msg) if msg else ''}      ")

    def fail(self, msg=""):
        if not self.quiet:
            print(f"\r  {R}✗{RS} {self.label}{('  ' + msg) if msg else ''}      ")

# ── scanner engine ─────────────────────────────────────────────────────────────
class Scanner:
    def __init__(self, email: str, quiet: bool = False):
        self.email   = email
        self.domain  = email.split('@')[-1] if '@' in email else ''
        self.quiet   = quiet
        self.orgs: Dict[str, OrgProfile] = {}
        self.scanned = 0

    def _log(self, msg):
        if not self.quiet:
            print(msg)

    def authenticate(self, host: str, port: int, password: str) -> bool:
        self.imap_host = host
        self.imap_port = port
        self._imap_pass = password
        try:
            self.imap = imaplib.IMAP4_SSL(host, port)
            self.imap.login(self.email, password)
            return True
        except Exception as e:
            print(f"\n  {R}✗ IMAP Auth error:{RS} {e}\n")
            return False

    def close(self):
        """Logout of IMAP and zero the in-memory credential."""
        self._imap_pass = None
        try:
            self.imap.logout()
        except Exception as e:
            logging.debug(f"IMAP logout error: {e}")

    # ── per-message header processing ──
    def _process_message(self, hdrs):
        try:
            sender  = hdrs.get('from', '')
            subject = hdrs.get('subject', '').lower()
            date    = hdrs.get('date', '')
            unsub   = hdrs.get('list-unsubscribe', '')

            m = re.search(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', sender)
            if not m: return

            ext  = tldextract.extract(m.group(1).lower())
            root = f"{ext.domain}.{ext.suffix}"
            name = PARENT_MAP.get(root, ext.domain.capitalize())

            if name not in self.orgs:
                self.orgs[name] = OrgProfile(name=name)

            org = self.orgs[name]
            org.domains.add(root)
            org.total_emails += 1
            org.last_seen = date
            if not org.first_seen:
                org.first_seen = date

            # categorise
            cat = 'unknown'
            for c, keywords in CATEGORIES.items():
                if any(k in subject for k in keywords):
                    cat = c
                    break
            org.categories[cat] += 1

            if cat == 'account':
                org.has_account = True

            if unsub:
                link = re.search(r'<(https?://[^>]+)>', unsub)
                if link and link.group(1) not in org.unsub_links:
                    org.unsub_links.append(link.group(1))

            self.scanned += 1
        except Exception as e:
            logging.debug(f"Message processing failed: {e}")

    # ── imap scan ──
    def scan_imap(self, progress_cb=None):
        try:
            self.imap.select('"[Gmail]/All Mail"', readonly=True)
            folder_name = 'ALL MAIL'
        except Exception as e:
            logging.debug(f"Could not select '[Gmail]/All Mail' ({e}), falling back to INBOX")
            self.imap.select('INBOX', readonly=True)
            folder_name = 'INBOX'
            
        if not self.quiet:
            print(f"\r  {C}⠋{RS} Targeting {folder_name}: Listing messages… ", end="", flush=True)
        if progress_cb:
            progress_cb(20, f"Targeting {folder_name}: Listing messages...")
            
        typ, data = self.imap.search(None, 'ALL')
        if typ != 'OK':
            if not self.quiet: print(f"\r  {R}✗{RS} Failed to list messages.      \n")
            return
            
        msg_ids = data[0].split()
        total = len(msg_ids)
        
        if total == 0:
            if not self.quiet:
                print(f"\r  {G}✓{RS} No messages to analyse.      \n")
            return
            
        if not self.quiet:
            print(f"\r  {G}✓{RS} Listed {folder_name} messages — {clr(total, BR, C)} emails found      ")
            print(f"  {C}⠋{RS} Analysing 0 / {total} emails (0%)  ", end="", flush=True)
        if progress_cb:
            progress_cb(30, f"Found {total:,} emails. Preparing to scan...")
            
        BATCH_SIZE = 100
        for start in range(0, total, BATCH_SIZE):
            chunk = msg_ids[start:start + BATCH_SIZE]
            id_list = b','.join(chunk)
            
            typ, fetch_data = self.imap.fetch(id_list, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE LIST-UNSUBSCRIBE)])')
            if typ == 'OK':
                for response_part in fetch_data:
                    if isinstance(response_part, tuple):
                        raw_email = response_part[1]
                        msg = email.message_from_bytes(raw_email)
                        
                        hdrs = {
                            'from': str(msg.get('from', '')),
                            'subject': str(msg.get('subject', '')),
                            'date': str(msg.get('date', '')),
                            'list-unsubscribe': str(msg.get('list-unsubscribe', ''))
                        }
                        
                        decoded_subject = ""
                        if hdrs['subject']:
                            for text, charset in decode_header(hdrs['subject']):
                                if isinstance(text, bytes):
                                    decoded_subject += text.decode(charset or 'utf-8', errors='ignore')
                                else:
                                    decoded_subject += text
                            hdrs['subject'] = decoded_subject
                        
                        self._process_message(hdrs)
            
            done = min(start + BATCH_SIZE, total)
            pct = int((done / total) * 100)
            if not self.quiet:
                print(f"\r  {C}⠋{RS} Analysing {clr(done, BR, C)} / {total} emails ({pct}%)  ", end="", flush=True)
            if progress_cb:
                # Map 0-100% of scan to 30-80% overall
                overall_pct = 30 + int(pct * 0.5)
                progress_cb(overall_pct, f"Scanning {done:,} / {total:,} emails ({pct}%)")
                
        if not self.quiet:
            print(f"\r  {G}✓{RS} Analysed {clr(total, BR, C)} emails — {clr(len(self.orgs), BR, C)} organisations detected      ")

    # ── hibp ──
    def run_hibp(self, api_key: str = None):
        spinner = Spinner("Checking Have I Been Pwned", quiet=self.quiet)
        spinner.tick()
        breach_map = check_hibp(self.email, api_key)

        if '_api_key_required' in breach_map:
            spinner.fail("HIBP requires API key — set HIBP_API_KEY env var to enable (see README)")
            return

        if not breach_map:
            spinner.done("No breaches found  🎉")
            return

        matched = 0
        for org in self.orgs.values():
            for domain in org.domains:
                if domain in breach_map:
                    org.breached      = True
                    org.breach_names += breach_map[domain]
                    matched += 1

        if matched:
            spinner.done(f"{clr(matched, BR, R)} breached services matched")
        else:
            spinner.done("Breach data fetched — no overlap with found accounts")

# ── report ─────────────────────────────────────────────────────────────────────
class Report:
    def __init__(self, orgs: Dict[str, OrgProfile], email: str, hibp_checked: bool = True):
        self.all         = list(orgs.values())
        self.email       = email
        self.hibp_checked = hibp_checked
        self.accounts    = [o for o in self.all if o.has_account]
        self.breached    = [o for o in self.all if o.breached]
        self.inactive    = [o for o in self.accounts if o.is_inactive]
        self.noisy       = sorted([o for o in self.all if o.is_high_volume],
                                  key=lambda x: x.total_emails, reverse=True)
        self.newsletters = [o for o in self.all if o.unsub_links or o.categories['newsletter'] > 0 or o.final_category in ('newsletters', 'newsletter')]

    def score(self) -> int:
        """Normalized 0-100 hygiene score, scaled by inbox size to avoid penalizing large inboxes."""
        if not self.all:
            return 100
        total = len(self.all)
        breach_rate   = len(self.breached)  / total
        inactive_rate = len(self.inactive)  / total
        noisy_rate    = len(self.noisy)     / total
        s = 100 - (breach_rate * 50) - (inactive_rate * 30) - (noisy_rate * 20)
        return max(0, min(100, round(s)))

    def score_label(self, s):
        if s >= 80: return G + "Good"    + RS
        if s >= 50: return Y + "Fair"    + RS
        return             R + "At Risk" + RS

    # ── header banner ──
    def print_banner(self):
        w = 66
        print()
        print(f"  {D}{'─' * w}{RS}")
        print(f"  {BR}{C}  chekreg{RS}  {D}Digital Footprint Mapper  v{VERSION}{RS}")
        print(f"  {D}{'─' * w}{RS}")
        print()

    # ── score card ──
    def print_scorecard(self):
        score = self.score()
        label = self.score_label(score)
        b     = bar(score, 100)
        print(f"  {BR}Hygiene Score{RS}   {b}  {BR}{score}{RS}/100  {label}")
        print(f"  {D}{'─' * 66}{RS}")
        print()

        cols = [
            (len(self.all),         "Services",       C),
            (len(self.breached),    "Breached",       R if self.breached else G),
            (len(self.inactive),    "Ghost Acc",      M),
            (len(self.newsletters), "Newsletters",    Y),
        ]
        row = "  "
        for val, label_txt, colour in cols:
            val_s   = clr(str(val).rjust(4), BR, colour)
            label_s = clr(f" {label_txt:<18}", D)
            row    += val_s + label_s
            if len(row) > 70:
                print(row)
                row = "  "
        if row.strip():
            print(row)

        # sites database coverage
        deletable_count = sum(1 for o in self.all if o.has_deletion_url)
        unsub_count = sum(1 for o in self.all if o.unsub_links)
        actionable_count = sum(1 for o in self.all if o.has_deletion_url or o.unsub_links)
        db_size = len(DELETION_URLS)
        print(f"  {D}  Sites DB: {db_size:,} sites loaded  ·  {unsub_count} unsub links & {deletable_count} delete URLs found{RS}")
        print(f"  {D}  Note: {actionable_count} out of {len(self.all)} services have an actionable link. (Counts may overlap due to Hybrids){RS}")
        print()

    # ── section header ──
    def print_section(self, title, subtitle=""):
        print(f"  {BR}{title}{RS}")
        if subtitle:
            print(f"  {D}{subtitle}{RS}")
        print()

    # ── breaches ──
    def print_breaches(self):
        if not self.hibp_checked:
            print(f"  {Y}ℹ{RS}  HIBP breach check was skipped.")
            print(f"     To manually check your email for data breaches, visit:")
            print(f"     {C}https://haveibeenpwned.com/{RS}\n")
            return

        if not self.breached:
            print(f"  {G}✓{RS}  No known breaches detected for your email.\n")
            return
        self.print_section(
            f"{R}⚠  Breach Alert — {len(self.breached)} service(s){RS}",
            "Your email appeared in data breach dumps for these services."
        )
        for org in self.breached:
            names = ", ".join(org.breach_names[:3])
            print(f"  {R}●{RS}  {BR}{org.name:<22}{RS}  {D}breach: {names}{RS}")
            if org.has_deletion_url:
                print(f"       {D}delete → {org.deletion_url()}{RS}")
        print()

    # ── master action dashboard ──
    def print_dashboard(self):
        if not self.all:
            return
            
        print(f"  {BR}{C}[*] ========================= FOOTPRINT DASHBOARD ========================= [*]{RS}")
        print(f"  {D}  The Web GUI provides advanced heuristics, filtering, and footprint tracking.{RS}")
        print(f"  {D}  This CLI is designed strictly for simple raw listing and developer testing.{RS}\n")
        
        for org in sorted(self.all, key=lambda x: x.name):
            breach_indicator = f" {R}[BREACHED]{RS}" if org.breached else ""
            inactive_indicator = f" {M}[INACTIVE]{RS}" if org.is_inactive else ""
            
            print(f"  {G}[+]{RS} {BR}{org.name}{RS} {D}({org.primary_domain}){RS}{breach_indicator}{inactive_indicator}")
            print(f"      {D}Volume:{RS} {org.total_emails} emails")
            
            if org.has_deletion_url:
                url = org.deletion_url()
                print(f"      {C}Delete:{RS} {url}")
            if org.unsub_links:
                url = org.unsub_links[0]
                print(f"      {Y}Unsub :{RS} {url}")
                
            print()
            
        print(f"  {BR}{C}[*] ======================================================================= [*]{RS}")

    # ── summary footer ──
    def print_footer(self):
        print(f"  {D}{'─' * 66}{RS}")
        db_src = 'sites.json' if SITES_META else 'hardcoded fallback'
        print(f"  {D}Scanned:  {self.email}   ·   {datetime.now().strftime('%Y-%m-%d %H:%M')}{RS}")
        print(f"  {D}Sites DB: {len(DELETION_URLS):,} deletion URLs loaded ({db_src}){RS}")
        print()

    # ── main print ──
    def print_all(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.print_banner()
        self.print_scorecard()
        self.print_breaches()
        self.print_dashboard()
        self.print_footer()

    # ── JSON export ──
    def export_json(self, path: str):
        data = {
            'generated':   datetime.now().isoformat(),
            'email':       self.email,
            'score':       self.score(),
            'summary': {
                'total_orgs':     len(self.all),
                'accounts':       len(self.accounts),
                'breached':       len(self.breached),
                'ghost_accounts': len(self.inactive),
                'newsletters':    len(self.newsletters),
                'high_volume':    len(self.noisy),
            },
            'breached_services': [
                {'name': o.name, 'domains': list(o.domains), 'breaches': o.breach_names}
                for o in self.breached
            ],
            'ghost_accounts': [
                {'name': o.name, 'domains': list(o.domains), 'last_seen': o.last_seen,
                 'breached': o.breached, 'delete_url': o.deletion_url()}
                for o in self.inactive
            ],
            'high_volume': [
                {'name': o.name, 'email_count': o.total_emails,
                 'unsub_link': o.unsub_links[0] if o.unsub_links else None}
                for o in self.noisy
            ],
            'all_organisations': [
                {
                    'name':         o.name,
                    'domains':      list(o.domains),
                    'email_count':  o.total_emails,
                    'has_account':  o.has_account,
                    'is_inactive':  o.is_inactive,
                    'is_breached':  o.breached,
                    'category':     o.final_category,
                    'first_seen':   o.first_seen,
                    'last_seen':    o.last_seen,
                    'unsub_links':  o.unsub_links,
                    'is_newsletter': bool(o.unsub_links or o.categories['newsletter'] > 0 or o.final_category in ('newsletters', 'newsletter')),
                    'is_high_volume': o.is_high_volume,
                    'delete_url':   o.deletion_url(),
                }
                for o in sorted(self.all, key=lambda x: x.total_emails, reverse=True)
            ],
            'cleanup_guide': {
                'total_deletable': sum(1 for o in self.all if o.has_deletion_url),
                'urgent_breached': [
                    {'name': o.name, 'delete_url': o.deletion_url(),
                     'breaches': o.breach_names}
                    for o in self.all if o.has_deletion_url and o.breached
                ],
                'urgent_inactive': [
                    {'name': o.name, 'delete_url': o.deletion_url(),
                     'last_seen': o.last_seen}
                    for o in self.all if o.has_deletion_url and o.is_inactive and not o.breached
                ],
                'all_deletable': [
                    {'name': o.name, 'delete_url': o.deletion_url(),
                     'breached': o.breached, 'inactive': o.is_inactive}
                    for o in sorted(
                        [o for o in self.all if o.has_deletion_url],
                        key=lambda x: x.name
                    )
                ],
            },
            'sites_db_size': len(DELETION_URLS),
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── plain-text export ──
    def export_txt(self, path: str):
        lines = []
        a = lines.append
        a(f"chekreg — Digital Footprint Report")
        a(f"Email    : {self.email}")
        a(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        a(f"Score    : {self.score()}/100")
        a("=" * 60)
        a("")

        if self.breached:
            a(f"BREACHES ({len(self.breached)})")
            for o in self.breached:
                a(f"  • {o.name}  — {', '.join(o.breach_names)}")
                if o.deletion_url():
                    a(f"    Delete: {o.deletion_url()}")
            a("")

        a(f"MASTER ACTION DASHBOARD ({len(self.all)} organizations)")
        grouped = defaultdict(list)
        for org in self.all:
            grouped[org.final_category].append(org)
            
        for category, orgs in sorted(grouped.items()):
            cat_name = category.replace('_', ' ').upper()
            a(f"--- {cat_name} ---")
            for o in sorted(orgs, key=lambda x: x.name):
                tags = []
                if o.breached:       tags.append("BREACHED")
                if o.is_inactive:    tags.append("INACTIVE")
                if o.is_high_volume: tags.append("HIGH VOLUME")
                
                tag_str = f"  [{', '.join(tags)}]" if tags else ""
                a(f"  • {o.name}  ({o.primary_domain}){tag_str}")
                
                if o.has_deletion_url:
                    a(f"      Delete Account: {o.deletion_url()}")
                if o.unsub_links:
                    a(f"      Unsubscribe   : {o.unsub_links[0]}")
                if o.has_deletion_url or o.unsub_links:
                    a("")
            a("")

        with open(path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def export_missing_links(self, path: str):
        """Exports organizations that have neither a deletion URL nor an unsubscribe link."""
        missing = [o for o in self.all if not o.has_deletion_url and not o.unsub_links]
        if not missing:
            return 0
            
        data = {
            'metadata': {
                'description': 'Organizations missing from sites.json and without unsubscribe links',
                'count': len(missing)
            },
            'missing_orgs': [
                {'name': o.name, 'domain': o.primary_domain, 'category': o.final_category}
                for o in sorted(missing, key=lambda x: x.name)
            ]
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return len(missing)