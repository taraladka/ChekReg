# Contributing to ChekReg

We welcome contributions from the open-source cybersecurity and privacy community! ChekReg thrives on having an up-to-date database of service endpoints.

## 1. Updating the Database (`sites.json`)

The most impactful way you can contribute to ChekReg without touching a single line of Python is by updating our service database.

The database is located at `data/sites.json`. It maps domains to human-readable names, categories, and most importantly, Direct Deletion URLs.

### Format

```json
{
    "canva.com": {
        "name": "Canva",
        "category": "design",
        "delete_url": "https://www.canva.com/settings/your-account"
    }
}
```

### How to add a service:
1. Identify the primary domain the service sends emails from (e.g., `marketing.uber.com` usually resolves to `uber.com` via our TLD extractor).
2. Find the exact URL where a user can permanently delete their account or submit a DSAR (Data Subject Access Request).
3. Add the JSON block in alphabetical order.
4. Submit a Pull Request!

### Using CLI Developer Tools to Extract Missing Sites

You can automate finding missing entries! 
1. Run ChekReg in your terminal: `python chekreg.py --email you@example.com`
2. In the interactive CLI menu, select **"Developer Tools"**, then **"Extract missing links and run maintenance scripts"**.
3. The engine will automatically isolate every organization found in your inbox that does NOT currently exist in `sites.json` and export them to `reports/missing_orgs.json`.
4. Append the missing sites to `data/sites.json`, find their deletion URLs, and submit a Pull Request!

## 2. Setting up the Developer Environment

Assuming you have already followed the **Getting Started** guide to clone the repository and set up your virtual environment, you are ready to start coding.

If you plan to submit Pull Requests, please ensure you **Fork** the repository on GitHub first, and push your changes to your fork.

## 3. Submitting Pull Requests
- Ensure your code follows the existing style (Vanilla HTML/CSS/JS for the frontend, strict zero-dependency Python for the backend where possible).
- Do not add heavy npm modules, build steps, or frameworks like React/Vue. ChekReg must remain lightweight and auditable.
- Write clear commit messages.
- If you are modifying `engine.py` IMAP parsing, please ensure you test against multiple different email providers (Gmail, Outlook, Yahoo) to account for differing IMAP RFC header implementations.
