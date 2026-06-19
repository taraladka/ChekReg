import os
import time
import json
import threading
import urllib.request
from flask import Flask, request, jsonify, Response
from engine import Scanner, Report, VERSION

app = Flask(__name__, static_folder='static', static_url_path='')

# Global state to track scan progress
scan_state = {
    "status": "idle", # idle, auth_failed, scanning, done, error
    "progress": 0,
    "message": "",
    "report_data": None
}

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/scan', methods=['POST'])
def start_scan():
    global scan_state
    data = request.json
    email = data.get('email')
    host = data.get('host', 'imap.gmail.com')
    port = int(data.get('port', 993))
    password = data.get('password')
    hibp_key = data.get('hibp_key')

    if not all([email, host, port, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    scan_state['status'] = 'running'
    scan_state['progress'] = 0
    scan_state['message'] = 'Connecting to server...'
    scan_state["report_data"] = None

    def run_scan_thread():
        global scan_state
        
        def progress_cb(pct, msg):
            scan_state["progress"] = pct
            scan_state["message"] = msg
            
        try:
            scanner = Scanner(email, quiet=True)
            
            # Auth
            if not scanner.authenticate(host, port, password):
                scan_state["status"] = "auth_failed"
                scan_state["message"] = "Authentication failed. Check your App Password."
                return
                
            scan_state["status"] = "scanning"
            scan_state["progress"] = 30
            scan_state["message"] = "Scanning emails..."
            
            # Scan
            scanner.scan_imap(progress_cb=progress_cb)
            
            scan_state["progress"] = 80
            scan_state["message"] = "Checking for data breaches..."
            
            # HIBP
            scanner.run_hibp(api_key=hibp_key)
            
            scan_state["progress"] = 90
            scan_state["message"] = "Generating report..."
            
            report = Report(scanner.orgs, email, hibp_checked=bool(hibp_key))
            
            # Prepare JSON data for frontend
            scan_state["report_data"] = {
                'email': email,
                'score': report._score(),
                'summary': {
                    'total_orgs': len(report.all),
                    'accounts': len(report.accounts),
                    'breached': len(report.breached),
                    'ghost_accounts': len(report.inactive),
                    'newsletters': len(report.newsletters),
                    'high_volume': len(report.noisy),
                },
                'breached_services': [
                    {'name': o.name, 'domains': list(o.domains), 'breaches': o.breach_names}
                    for o in report.breached
                ],
                'ghost_accounts': [
                    {'name': o.name, 'domains': list(o.domains), 'last_seen': o.last_seen,
                     'breached': o.breached, 'delete_url': o.deletion_url()}
                    for o in report.inactive
                ],
                'high_volume': [
                    {'name': o.name, 'email_count': o.total_emails,
                     'unsub_link': o.unsub_links[0] if o.unsub_links else None}
                    for o in report.noisy
                ],
                'all_organisations': [
                    {
                        'name': o.name,
                        'domains': list(o.domains),
                        'email_count': o.total_emails,
                        'is_inactive': o.is_inactive,
                        'is_breached': o.breached,
                        'is_newsletter': bool(o.unsub_links or o.categories['newsletter'] > 0 or o.final_category in ('newsletters', 'newsletter')),
                        'is_high_volume': o.is_high_volume,
                        'last_seen': o.last_seen,
                        'category': o.final_category,
                        'unsub_link': o.unsub_links[0] if o.unsub_links else None,
                        'delete_url': o.deletion_url(),
                    }
                    for o in sorted(report.all, key=lambda x: x.name)
                ]
            }
            scan_state["status"] = "done"
            scan_state["progress"] = 100
            scan_state["message"] = "Scan Complete!"
            
        except Exception as e:
            scan_state["status"] = "error"
            scan_state["message"] = f"Error: {str(e)}"
            
    threading.Thread(target=run_scan_thread, daemon=True).start()
    return jsonify({"success": True, "message": "Scan started"})

@app.route('/api/status', methods=['GET'])
def get_status():
    global scan_state
    return jsonify({
        "status": scan_state["status"],
        "progress": scan_state["progress"],
        "message": scan_state["message"]
    })

@app.route('/api/results', methods=['GET'])
def get_results():
    global scan_state
    if scan_state["status"] == "done" and scan_state["report_data"]:
        return jsonify(scan_state["report_data"])
    return jsonify({"error": "Results not ready"}), 400

@app.route('/api/refresh', methods=['GET'])
def refresh_results():
    """Refresh the current scan results with the latest sites.json data without rescanning."""
    global scan_state
    if scan_state["status"] != "done" or not scan_state["report_data"]:
        return jsonify({"error": "No scan results to refresh"}), 400
        
    try:
        root = os.path.dirname(os.path.abspath(__file__))
        sites_path = os.path.join(root, 'data', 'sites.json')
        
        # Ensure sites.json exists before loading
        if not os.path.exists(sites_path):
             return jsonify(scan_state["report_data"])

        with open(sites_path, 'r', encoding='utf-8') as f:
            db = json.load(f)
        sites = db.get('sites', db)
        
        # update the report_data in memory
        for org in scan_state["report_data"]["all_organisations"]:
            if not org.get("delete_url"):
                for dom in org.get("domains", []):
                    dom_lower = dom.lower()
                    if dom_lower in sites:
                        org["delete_url"] = sites[dom_lower].get("delete_url") or sites[dom_lower].get("url")
                        break
                        
        return jsonify(scan_state["report_data"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/missing', methods=['POST'])
def export_missing():
    """Extract orgs with no delete_url from the current scan results."""
    global scan_state
    if scan_state["status"] != "done" or not scan_state["report_data"]:
        return jsonify({"error": "No scan results available"}), 400

    all_orgs = scan_state["report_data"].get("all_organisations", [])
    missing = []
    for o in all_orgs:
        if not o.get("delete_url"):
            missing.append({
                "domain": o["domains"][0] if o.get("domains") else "",
                "name": o.get("name", ""),
                "category": o.get("category", "other")
            })
    
    # Save to reports/missing_links.json for the resolver
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    path = os.path.join(reports_dir, 'missing_links.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({"missing_orgs": missing}, f, indent=2)

    return jsonify({"count": len(missing), "path": path})


# ── Auto-Resolve state ──
resolve_state = {
    "status": "idle",  # idle, running, done, error
    "log": [],
    "stats": {}
}

@app.route('/api/resolve', methods=['POST'])
def start_resolve():
    global resolve_state
    if resolve_state["status"] == "running":
        return jsonify({"error": "Resolver is already running"}), 400

    resolve_state = {"status": "running", "log": [], "stats": {}}

    def run_resolver():
        global resolve_state
        import socket as sock
        try:
            root = os.path.dirname(os.path.abspath(__file__))
            missing_path = os.path.join(root, 'reports', 'missing_links.json')

            if not os.path.exists(missing_path):
                resolve_state["log"].append("[!] No missing_links.json found. Extract missing links first.")
                resolve_state["status"] = "error"
                return

            with open(missing_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            orgs = data.get('missing_orgs', [])
            if not orgs:
                resolve_state["log"].append("[+] No missing organizations to process.")
                resolve_state["status"] = "done"
                resolve_state["stats"] = {"total": 0, "resolved": 0}
                return

            resolve_state["log"].append(f"[*] Processing {len(orgs)} organizations...")

            # Load JDM database
            resolve_state["log"].append("[*] Loading JustDeleteMe database...")
            jdm_map = {}
            try:
                req = urllib.request.Request(
                    "https://raw.githubusercontent.com/jdm-contrib/jdm/master/_data/sites.json",
                    headers={'User-Agent': 'ChekReg/1.0'}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    jdm_data = json.loads(resp.read().decode('utf-8'))
                    for site in jdm_data:
                        link = site.get('url', '')
                        for dom in site.get('domains', []):
                            if dom and link:
                                jdm_map[dom.lower()] = link
                resolve_state["log"].append(f"[+] JustDeleteMe: {len(jdm_map)} domains loaded")
            except Exception as e:
                resolve_state["log"].append(f"[!] JustDeleteMe failed: {e}")

            # Well-known paths
            well_known = [
                "/account/delete", "/settings/account", "/settings/delete",
                "/account/deactivate", "/delete-account", "/close-account",
                "/help/delete-account", "/settings", "/account", "/unsubscribe"
            ]

            resolved = {}
            stats = {'db_hit': 0, 'probe_hit': 0, 'search_hit': 0, 'offline': 0, 'not_found': 0}

            for idx, org in enumerate(orgs, 1):
                domain = org.get('domain', '').lower().strip()
                name = org.get('name', domain)
                category = org.get('category', 'other')
                if not domain:
                    continue

                # DB lookup
                if domain in jdm_map:
                    resolved[domain] = {"name": name, "category": category, "delete_url": jdm_map[domain]}
                    stats['db_hit'] += 1
                    resolve_state["log"].append(f"[{idx}/{len(orgs)}] {domain} -> [DB HIT] {jdm_map[domain]}")
                    continue

                # DNS check
                alive = False
                for prefix in ['', 'www.']:
                    try:
                        sock.setdefaulttimeout(3)
                        sock.gethostbyname(f"{prefix}{domain}")
                        alive = True
                        break
                    except sock.gaierror:
                        continue
                if not alive:
                    stats['offline'] += 1
                    resolve_state["log"].append(f"[{idx}/{len(orgs)}] {domain} -> [OFFLINE] Domain does not resolve")
                    continue

                # Path probing
                probed = None
                for path in well_known:
                    url = f"https://{domain}{path}"
                    try:
                        req = urllib.request.Request(url, method='HEAD', headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120'
                        })
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            if resp.status in (200, 301, 302, 303, 307, 308):
                                probed = resp.url if hasattr(resp, 'url') else url
                                break
                    except Exception:
                        continue

                if probed:
                    resolved[domain] = {"name": name, "category": category, "delete_url": probed}
                    stats['probe_hit'] += 1
                    resolve_state["log"].append(f"[{idx}/{len(orgs)}] {domain} -> [PROBED] {probed}")
                    continue

                # Fallback: DuckDuckGo
                try:
                    from duckduckgo_search import DDGS
                    from urllib.parse import urlparse
                    ddgs = DDGS()
                    found = False
                    for q in [f'{domain} delete account settings', f'{domain} how to delete account']:
                        hits = ddgs.text(q, max_results=5)
                        for h in (hits or []):
                            href = h.get('href', '')
                            href_lower = href.lower()
                            domain_stripped = domain.replace('www.', '')
                            if href and domain_stripped in href_lower:
                                parsed = urlparse(href)
                                path_query = (parsed.path + parsed.query).lower()
                                target_kws = ['delete', 'remove', 'deactivate', 'close', 'cancel', 'unsub', 'setting', 'account', 'profile']
                                if any(kw in path_query for kw in target_kws):
                                    resolved[domain] = {"name": name, "category": category, "delete_url": href}
                                    stats['search_hit'] += 1
                                    resolve_state["log"].append(f"[{idx}/{len(orgs)}] {domain} -> [SEARCH] {href}")
                                    found = True
                                    break
                        if found:
                            break
                    if not found:
                        stats['not_found'] += 1
                        resolve_state["log"].append(f"[{idx}/{len(orgs)}] {domain} -> [MISS] No link found")
                    time.sleep(1)
                except ImportError:
                    stats['not_found'] += 1
                    resolve_state["log"].append(f"[{idx}/{len(orgs)}] {domain} -> [MISS] duckduckgo-search not installed")

            # Merge into sites.json
            if resolved:
                sites_path = os.path.join(root, 'data', 'sites.json')
                try:
                    with open(sites_path, 'r', encoding='utf-8') as f:
                        db = json.load(f)
                    sites = db.get('sites', db)
                    added = 0
                    for dom, info in resolved.items():
                        if dom not in sites:
                            sites[dom] = info
                            added += 1
                    with open(sites_path, 'w', encoding='utf-8') as f:
                        json.dump(db, f, indent=2, ensure_ascii=False)
                    resolve_state["log"].append(f"[+] Merged {added} new entries into sites.json")
                except Exception as e:
                    resolve_state["log"].append(f"[!] Merge failed: {e}")

            total_resolved = stats['db_hit'] + stats['probe_hit'] + stats['search_hit']
            resolve_state["stats"] = {
                "total": len(orgs), "resolved": total_resolved,
                "db_hit": stats['db_hit'], "probe_hit": stats['probe_hit'],
                "search_hit": stats['search_hit'], "offline": stats['offline'],
                "not_found": stats['not_found']
            }
            resolve_state["log"].append(f"[+] Done! Resolved {total_resolved}/{len(orgs)} organizations.")
            resolve_state["status"] = "done"

        except Exception as e:
            resolve_state["log"].append(f"[!] Fatal error: {e}")
            resolve_state["status"] = "error"

    threading.Thread(target=run_resolver, daemon=True).start()
    return jsonify({"success": True})


@app.route('/api/resolve/status', methods=['GET'])
def resolve_status():
    global resolve_state
    return jsonify(resolve_state)


def run_server():
    print(f"\n  Starting Web Interface at http://127.0.0.1:5000\n")
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(host='127.0.0.1', port=5000, debug=False)

if __name__ == '__main__':
    run_server()
