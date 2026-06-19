"""
fetch_missing_links.py — Multi-source link resolver for ChekReg.

Resolution pipeline (in order):
  1. JustDeleteMe open-source database (instant, authoritative)
  2. AccountKiller open-source database (instant, authoritative)
  3. Well-known URL path probing (fast, direct HTTP checks)
  4. DuckDuckGo web search (fallback, slower)

Each domain gets a clear status printed to the terminal.
"""

import os
import sys
import json
import time
import socket
import urllib.request
import urllib.error
from urllib.parse import urlparse

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

# ── Well-known account deletion / settings paths ─────────────────────────────
# These are the most common URL patterns across thousands of websites.
WELL_KNOWN_PATHS = [
    "/account/delete",
    "/settings/account",
    "/settings/delete",
    "/account/deactivate",
    "/delete-account",
    "/close-account",
    "/privacy/delete",
    "/help/delete-account",
    "/support/delete-account",
    "/account/remove",
    "/settings/privacy",
    "/settings",
    "/account",
    "/profile/settings",
    "/preferences",
    "/unsubscribe",
]

# ── Junk domains to skip in search results ────────────────────────────────────
JUNK_DOMAINS = frozenset([
    'justdelete.me', 'accountkiller.com', 'pinterest.com',
    'reddit.com', 'quora.com', 'youtube.com', 'twitter.com',
    'x.com', 'facebook.com', 'tiktok.com', 'wikipedia.org',
    'wikihow.com', 'medium.com',
])


# ═══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1 & 2: Open-Source Databases
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_json(url, label):
    """Download and parse a JSON file from a URL."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ChekReg/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  [!] Could not load {label}: {e}")
        return None


def load_open_source_databases():
    """Load JustDeleteMe + AccountKiller into a single domain->url map."""
    db_map = {}

    # ── JustDeleteMe ──
    print("  [*] Loading JustDeleteMe database...")
    jdm = _fetch_json(
        "https://raw.githubusercontent.com/jdm-contrib/jdm/master/_data/sites.json",
        "JustDeleteMe"
    )
    if jdm:
        for site in jdm:
            link = site.get('url', '')
            for dom in site.get('domains', []):
                if dom and link:
                    db_map[dom.lower()] = link
        print(f"  [+] JustDeleteMe: {len(jdm)} services indexed")

    # ── AccountKiller ──
    print("  [*] Loading AccountKiller database...")
    ak = _fetch_json(
        "https://raw.githubusercontent.com/dessant/accountkiller-data/master/data/sites.json",
        "AccountKiller"
    )
    if ak:
        count = 0
        # AccountKiller has a different format — list of objects with 'domain' and 'url'
        if isinstance(ak, list):
            for site in ak:
                dom = site.get('domain', '').lower()
                link = site.get('url', '')
                if dom and link and dom not in db_map:
                    db_map[dom] = link
                    count += 1
        elif isinstance(ak, dict):
            for dom, info in ak.items():
                link = info if isinstance(info, str) else info.get('url', '')
                if dom and link and dom.lower() not in db_map:
                    db_map[dom.lower()] = link
                    count += 1
        print(f"  [+] AccountKiller: {count} new services added")

    total = len(db_map)
    print(f"  [+] Combined database: {total} domains ready\n")
    return db_map


# ═══════════════════════════════════════════════════════════════════════════════
#  SOURCE 3: Well-Known Path Probing
# ═══════════════════════════════════════════════════════════════════════════════

def probe_well_known_paths(domain):
    """Try common account-deletion URL paths directly via HTTP HEAD/GET."""
    for scheme in ['https', 'www.']:
        base = f"https://{scheme}{domain}" if scheme == 'www.' else f"https://{domain}"
        for path in WELL_KNOWN_PATHS:
            url = base + path
            try:
                req = urllib.request.Request(url, method='HEAD', headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120'
                })
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status in (200, 301, 302, 303, 307, 308):
                        return resp.url if hasattr(resp, 'url') else url
            except Exception:
                continue
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  SOURCE 4: DuckDuckGo Search Fallback
# ═══════════════════════════════════════════════════════════════════════════════

def _is_relevant_url(url, target_domain):
    """Check if a search result URL is relevant (not junk)."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    target_base = target_domain.replace('www.', '')
    # Prefer first-party links
    if target_base in host:
        return True
    # Reject known junk
    for j in JUNK_DOMAINS:
        if j in host:
            return False
    return True


def search_ddgs(domain):
    """Use DuckDuckGo to find deletion/unsubscribe links."""
    if not HAS_DDGS:
        return {}

    result = {}
    ddgs = DDGS()

    # ── Deletion link ──
    queries = [
        f'site:{domain} "delete account" OR "close account" OR "deactivate account"',
        f'{domain} delete account settings help',
        f'{domain} how to delete account',
    ]
    for q in queries:
        try:
            hits = ddgs.text(q, max_results=5)
            for h in (hits or []):
                url = h.get('href', '')
                if url and _is_relevant_url(url, domain):
                    result['delete_url'] = url
                    break
            if 'delete_url' in result:
                break
        except Exception:
            continue

    # ── Unsubscribe link ──
    try:
        unsub_hits = ddgs.text(
            f'site:{domain} unsubscribe OR "email preferences" OR "manage subscriptions"',
            max_results=5
        )
        for h in (unsub_hits or []):
            url = h.get('href', '')
            if url and _is_relevant_url(url, domain):
                low = url.lower()
                if any(kw in low for kw in ('unsubscribe', 'preference', 'opt-out', 'manage')):
                    result['unsub_url'] = url
                    break
    except Exception:
        pass

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  DNS Check
# ═══════════════════════════════════════════════════════════════════════════════

def is_domain_alive(domain):
    """Fast DNS resolution check."""
    for prefix in ['', 'www.']:
        try:
            socket.setdefaulttimeout(3)
            socket.gethostbyname(f"{prefix}{domain}")
            return True
        except socket.gaierror:
            continue
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    missing_path = os.path.join(root_dir, 'reports', 'missing_links.json')
    output_path = os.path.join(root_dir, 'reports', 'fetched_links.json')
    merge_script = os.path.join(root_dir, 'scripts', 'merge_db.py')

    if not os.path.exists(missing_path):
        print("\n  [!] No missing_links.json found in reports/.")
        print("      Run the scanner and extract missing links first.\n")
        return

    with open(missing_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    orgs = data.get('missing_orgs', [])
    if not orgs:
        print("\n  [+] No missing organizations to process.\n")
        return

    # ── Header ──
    print(f"\n  {'=' * 60}")
    print(f"  CHEKREG LINK RESOLVER")
    print(f"  {len(orgs)} organizations queued")
    print(f"  {'=' * 60}\n")

    # ── Step 1: Load open-source databases ──
    os_db = load_open_source_databases()

    # ── Step 2: Process each domain ──
    resolved = {}
    stats = {'db_hit': 0, 'probe_hit': 0, 'search_hit': 0, 'offline': 0, 'not_found': 0}

    for idx, org in enumerate(orgs, 1):
        domain = org.get('domain', '').lower().strip()
        name = org.get('name', domain)
        category = org.get('category', 'other')

        if not domain:
            continue

        print(f"  [{idx:>3}/{len(orgs)}] {domain}")

        # ── Source 1+2: Open-source DB lookup ──
        if domain in os_db:
            resolved[domain] = {
                "name": name, "category": category,
                "delete_url": os_db[domain]
            }
            stats['db_hit'] += 1
            print(f"           [DB HIT]    {os_db[domain]}")
            continue

        # ── DNS check ──
        if not is_domain_alive(domain):
            stats['offline'] += 1
            print(f"           [OFFLINE]   Domain does not resolve - service may have shut down")
            continue

        # ── Source 3: Well-known path probing ──
        probed = probe_well_known_paths(domain)
        if probed:
            resolved[domain] = {
                "name": name, "category": category,
                "delete_url": probed
            }
            stats['probe_hit'] += 1
            print(f"           [PROBED]    {probed}")
            continue

        # ── Source 4: DuckDuckGo search ──
        if HAS_DDGS:
            links = search_ddgs(domain)
            if links:
                entry = {"name": name, "category": category}
                if 'delete_url' in links:
                    entry['delete_url'] = links['delete_url']
                if 'unsub_url' in links:
                    entry['unsub_link'] = links['unsub_url']
                resolved[domain] = entry
                stats['search_hit'] += 1
                for k, v in links.items():
                    tag = 'DELETE' if 'delete' in k else 'UNSUB'
                    print(f"           [{tag:>6}]    {v}")
                continue
            time.sleep(1)  # Rate-limit politeness

        # ── Nothing found ──
        stats['not_found'] += 1
        print(f"           [MISS]      Domain is live but no link could be resolved")

    # ── Summary ──
    print(f"\n  {'=' * 60}")
    print(f"  RESULTS SUMMARY")
    print(f"  {'=' * 60}")
    print(f"  Total processed:    {len(orgs)}")
    print(f"  Resolved (DB):      {stats['db_hit']}")
    print(f"  Resolved (Probe):   {stats['probe_hit']}")
    print(f"  Resolved (Search):  {stats['search_hit']}")
    print(f"  Offline/Shutdown:   {stats['offline']}")
    print(f"  Not found:          {stats['not_found']}")
    total_resolved = stats['db_hit'] + stats['probe_hit'] + stats['search_hit']
    print(f"  {'=' * 60}")
    print(f"  Total resolved:     {total_resolved}/{len(orgs)}")
    print(f"  {'=' * 60}\n")

    if not resolved:
        print("  [!] No new links resolved this run.\n")
        return

    # ── Save & merge ──
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resolved, f, indent=4)
    print(f"  [+] Saved {total_resolved} entries to {output_path}")
    print(f"  [*] Running merge_db.py...\n")
    os.system(f'python "{merge_script}" "{output_path}"')


if __name__ == '__main__':
    main()
