# Getting Started with ChekReg

Welcome! ChekReg is an OSINT (technically CSINT) tool that scans email headers locally to map out a user's digital footprint—identifying active subscriptions, inactive ghost accounts, and potential data breaches using Zero-Trust architecture.

> **Note on OSINT vs. CSINT**: While ChekReg heavily utilizes traditional Open-Source Intelligence (OSINT) workflows—such as data enrichment and cross-referencing public breach databases—its primary data source is an authenticated, private email inbox. Because this seed data is not publicly accessible, it falls under the strict technical definition of Closed-Source Intelligence (CSINT).

---

## 1. Prerequisites

- Python 3.8+
- Active IMAP access for the target email account

## 2. Download and Install

1. Clone the repository:
   ```bash
   git clone https://github.com/taraladka/ChekReg.git
   cd ChekReg-IMAP
   ```
2. Create and activate a virtual environment:
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate
   
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install tldextract colorama flask
   ```

## 3. Generate an App Password (CRITICAL)

Because ChekReg enforces local execution, standard email passwords will generally fail due to modern provider security policies blocking third-party basic auth. You must generate an App Password.

### For Gmail Users
1. Go to your [Google Account Security page](https://myaccount.google.com/security).
2. Ensure **2-Step Verification** is turned ON.
3. Use the search bar at the top to search for **"App passwords"**.
4. Create a new password. Name it "ChekReg".
5. Google will give you a 16-letter password (e.g., `abcd efgh ijkl mnop`). **Save this.**

### For Microsoft Outlook Users
1. Go to your [Microsoft Account Advanced Security Options](https://account.live.com/proofs/manage/additional).
2. Turn on **Two-step verification**.
3. Scroll down to the "App passwords" section and click **"Create a new app password"**.
4. Microsoft will give you a password. **Save this.**

### For Yahoo Mail & AOL Users
1. Log in to your Yahoo or AOL Account Security page.
2. Scroll down to **"How you sign in"** and ensure **2-Step Verification** is turned on.
3. Below that, click on **"Generate and manage app passwords"**.
4. Enter "ChekReg" as the app's name, and click "Generate password".
5. Copy the 16-character code (without the spaces) and paste it into ChekReg.

### For Apple iCloud Mail Users
1. Go to your [Apple ID account page](https://appleid.apple.com) and sign in.
2. Under the "Sign-In and Security" section, click on **"App-Specific Passwords"**.
3. Click "Generate an app-specific password" (or the plus `+` button).
4. Enter "ChekReg" as the profile name and click Create.
5. Enter your regular Apple ID password if prompted, then copy the generated 16-character string.

### For Custom / Private IMAP Providers
If you use a private IMAP server (like ProtonMail via Proton Bridge, or a corporate server), you may not need an app password depending on your IT policy. Use your standard password, or generate an App Password from your corporate Microsoft/Google workspace if required.

## 4. Run ChekReg!

Run the engine:
```bash
python chekreg.py
```

The CLI will prompt you to:
1. **Choose your Interface:** Select `2` to launch the local **Flask Web GUI** on port 5000, or `1` for the raw Terminal stdout.
2. **Authenticate:** Provide the target email address and the 16-character App Password.
3. **IMAP Server:** Select the provider endpoint.

The scan executes entirely locally; credentials are held in volatile memory and destroyed upon process exit.
