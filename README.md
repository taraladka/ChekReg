<div align="center">
  <pre>
   ____ _          _    ____           
  / ___| |__   ___| | _|  _ \ ___  __ _
 | |   | '_ \ / _ \ |/ / |_) / _ \/ _` |
 | |___| | | |  __/   &lt;|  _ &lt;  __/ (_| |
  \____|_| |_|\___|_|\_\_| \_\___|\__, |
                                  |___/ 
  </pre>
  <h3>The Zero-Trust Digital Footprint Mapper</h3>
  <p>
    Map your active digital footprint, flag compromised accounts, and automate deletion requests—all without sharing your inbox with any third-party service.
  </p>

  <p>
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
    <img src="https://img.shields.io/badge/architecture-Zero%20Trust-success.svg" alt="Zero Trust">
    <img src="https://img.shields.io/badge/IMAP-read--only-informational.svg" alt="Read Only">
    <img src="https://img.shields.io/badge/tests-8%20passing-brightgreen.svg" alt="Tests">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  </p>
</div>

---

## 🛡️ Why ChekReg?

Most digital footprint tools require you to grant OAuth access to your inbox. This exposes your private email metadata to a third-party server.

**ChekReg is different.** It connects directly to your mail provider via IMAP in strict **read-only mode**, pulls only the minimal headers needed (`From`, `Date`, `List-Unsubscribe`), matches them against a massive local database, and explicitly **zeros credentials from memory and logs out of the IMAP session** the moment the scan completes.

**Zero Telemetry. Zero Cloud Processing. Zero Trust.**

---

## ✨ Features

- **Massive Built-In Database** — `data/sites.json` contains thousands of organizations with their direct account deletion and unsubscribe endpoints, maintained by the community.
- **Strict Read-Only IMAP** — The engine selects mailbox folders with `readonly=True`. It cannot write, move, or delete any email.
- **Explicit Credential Teardown** — `Scanner.close()` zeroes the password attribute and calls `imap.logout()` in a `finally` block—in both the CLI and the web backend.
- **Thread-Safe Web Backend** — All shared state in the Flask server is guarded by a `threading.Lock()`.
- **HaveIBeenPwned Integration** — Optionally flags accounts exposed in known public data breaches (requires a HIBP API key).
- **Ghost Account Detection** — Flags accounts you haven't received mail from in over 6 months.
- **4-Stage Auto-Resolver** — Automatically finds deletion URLs for services not yet in the database.
- **Dual Interfaces** — Terminal CLI or a local Vanilla HTML/JS Web Dashboard; one engine, two surfaces.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- An [App Password](https://myaccount.google.com/apppasswords) for your mail account. Standard account passwords are rejected by modern providers for IMAP access.

### Installation

```bash
git clone https://github.com/taraladka/ChekReg.git
cd ChekReg

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Run

```bash
python chekreg.py           # Interactive launcher
python chekreg.py --web     # Launch Web Dashboard directly (localhost:5000)
python chekreg.py --cli     # Launch Terminal Interface directly
```

---

## 🤖 The Auto-Resolver Engine

When your scan surfaces a service that isn't yet in `sites.json`, the Auto-Resolver attempts to find its deletion endpoint through a layered 4-stage pipeline:

1. **JustDeleteMe DB** — Cross-references the open-source JustDeleteMe dataset first. Fast, offline, no network cost.
2. **DNS Liveness Check** — Resolves the domain before probing to discard dead/parked domains early.
3. **Path Probing** — Issues `HEAD` requests against common URL patterns (`/account/delete`, `/settings/account`, etc.).
4. **Search Engine Fallback** — Queries DuckDuckGo with strict path-filtering heuristics to surface actionable settings pages rather than generic homepages or privacy policies.

> **Accuracy ~85%.** Anti-bot protections and stale search index results account for most misses. Resolved links should be manually verified before submitting a PR.

---

## 🧪 Running Tests

```bash
python -m unittest discover tests/
```

The test suite covers domain extraction, `List-Unsubscribe` header parsing, and the `Scanner` credential lifecycle (including teardown).

---

## 🤝 Contributing

The power of ChekReg scales directly with the size and accuracy of `data/sites.json`. The internet is large and always changing—new services appear, old links go stale.

**To contribute a new or corrected deletion link:**

1. Run the Auto-Resolver or manually verify the correct URL.
2. Add or update the entry in `data/sites.json`.
3. Fork the repository and open a Pull Request against `main`.

No application code changes are required for database-only contributions.

---

## 🔒 Security Model

| Property | Implementation |
|---|---|
| IMAP access mode | `readonly=True` on all `select()` calls |
| Credential lifetime | Zeroed via `Scanner.close()` in a `finally` block |
| IMAP session | Explicitly logged out via `imap.logout()` |
| Flask concurrency | Shared state protected by `threading.Lock()` |
| Network binding | Flask bound to `127.0.0.1` only—not accessible on the network |
| External requests | Only to HIBP (opt-in, keyed) and DuckDuckGo (Auto-Resolver only) |

---

## 📝 Documentation

Launch the Web GUI and click **Docs** for the full interactive reference, or browse the `documentation/` directory directly.

## 📄 License

MIT. See `LICENSE`.
