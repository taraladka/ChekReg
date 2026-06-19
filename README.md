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
    Map your active digital footprint, flag compromised accounts, and automate deletion requests—all without sharing your inbox access with third-party cloud services.
  </p>
  
  <p>
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
    <img src="https://img.shields.io/badge/architecture-Zero%20Trust-success.svg" alt="Zero Trust">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
    <img src="https://img.shields.io/badge/status-Active-success.svg" alt="Status">
  </p>
</div>

---

## 🛡️ Why ChekReg?

Most digital footprint tools require you to grant OAuth access to your inbox. While convenient, this exposes your private email metadata to a third-party server. 

**ChekReg takes a different path.** It is a purely local script that connects directly to your email provider via IMAP, pulls only the necessary headers (`From`, `Date`, `List-Unsubscribe`), matches them against a local database, and destroys all credentials the moment the scan finishes.

**Zero Telemetry. Zero Cloud Processing. Zero Trust.**

## ✨ Features

- **Local & Offline Resolution**: Your footprint is built locally against the bundled `sites.json` database.
- **HaveIBeenPwned Integration**: (Optional) Flags your accounts that have been exposed in known public data breaches.
- **Ghost Account Detection**: Flags accounts you haven't received emails from in over 6 months.
- **Integrated Auto-Resolver**: A 4-stage engine that automatically crawls the web to find missing deletion URLs for obscure services.
- **Dual Interfaces**: Choose between a Hacker-style Terminal CLI or a beautiful Vanilla HTML/JS Web Dashboard.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+
- An [App Password](https://myaccount.google.com/apppasswords) for your email account (standard passwords are blocked by modern providers).

### 2. Installation
Clone the repository and install the lightweight dependencies:

```bash
git clone https://github.com/taraladka/ChekReg.git
cd ChekReg

python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows

pip install -r requirements.txt
```
*(If `requirements.txt` is missing, install: `tldextract colorama flask duckduckgo-search requests`)*

### 3. Run the Engine
```bash
python chekreg.py
```
This will launch the interactive selector. You can choose to start the **CLI mode** or the **Local Web GUI** (running on `localhost:5000`).

You can also bypass the menu:
- `python chekreg.py --web`
- `python chekreg.py --cli`

---

## 🤖 The Auto-Resolver Engine

ChekReg includes a Developer Tool to automatically find account deletion endpoints for services not yet in our database.

It runs a powerful 4-stage pipeline:
1. **JustDeleteMe Database** — Fast offline cross-referencing.
2. **DNS Validation** — Discards offline/dead domains to speed up execution.
3. **Path Probing** — Direct HTTP `HEAD` checks on common URL patterns (`/settings/account`, `/account/delete`).
4. **Search Engine Fallback** — Uses DuckDuckGo with strict heuristics to extract actionable settings pages.

> 💡 **Resolver Accuracy (~85%):** The Auto-Resolver is highly effective but search engines can occasionally pull stale URLs, and advanced anti-bot protections might block probes. **We highly encourage developers to manually verify the resolved links and submit a PR to improve the shared database!**

---

## 🤝 Contributing

We want to map the entire internet's account deletion URLs. Our community-driven database (`data/sites.json`) is the core of this project.

If ChekReg's Auto-Resolver successfully finds links for obscure regional or niche services you use, **please consider contributing them back!** Every new verified link helps hundreds of other users cleanly erase their footprint.

1. Verify the newly appended links in your `data/sites.json` file.
2. Fork the repository.
3. Submit a Pull Request against the `main` branch. No code changes required—just the raw JSON updates!

---

## 📝 Documentation
For a deeper dive into the architecture, the extraction logic, and advanced configuration, view the interactive Web Documentation by launching the GUI and clicking **"Docs"**, or read the raw files in the `documentation/` folder (if available).

## 📄 License
This project is licensed under the MIT License. See the `LICENSE` file for details.
