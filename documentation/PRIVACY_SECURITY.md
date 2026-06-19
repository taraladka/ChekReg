# Privacy & Security Model

ChekReg was engineered explicitly to solve a massive privacy ironically created by the privacy industry itself: to find out what companies have your data, you usually have to hand your entire inbox over to a massive cloud corporation (like Unroll.me, SayMine, or DeleteMe) using OAuth.

ChekReg is fundamentally different. It is a **Zero-Trust, Local-First Architecture**.

## 1. Local Execution Guarantees

When you run ChekReg, you are executing a python script locally on your own machine's hardware. 
- **No Cloud Servers**: ChekReg does not route your emails through our servers. We do not have servers.
- **No Phoning Home**: The engine does not collect telemetry, crash reports, or analytics of any kind.
- **Direct Connection**: The IMAP connection is established directly from your local IP address to your email provider's IMAP server over an encrypted `SSL/TLS` tunnel.

## 2. Ephemeral Credential Handling

You are required to use an "App Password" to run ChekReg. 
- **Volatile Storage**: The password you type into the Terminal or the Web GUI is held strictly in volatile RAM. It is **never** written to a disk, config file, database, or cache.
- **Process Termination**: As soon as you hit `Ctrl+C` or close the local web server, the password is permanently eradicated from memory. Furthermore, clicking the 'New Scan' button in the Web GUI or the 'Back to Scanner' button on the docs page explicitly triggers a cache-flush, actively erasing the `sessionStorage` in your browser before returning you to the input page, ensuring no residual scan data is left behind.

## 3. Minimal Privilege Data Extraction

ChekReg respects the sanctity of your inbox.
- **Header-Only Extraction**: ChekReg explicitly queries for `RFC822.HEADER` data. It completely ignores the bodies and contents of your emails. It only cares about the `From:` and `List-Unsubscribe:` fields.
- **Read-Only Mode**: The engine operates in a strict, read-only mode (`imap.select('INBOX', readonly=True)`). It cannot accidentally delete, flag, or modify your emails.

## 4. Have I Been Pwned Integration

If you choose to enable the Breach Check feature, the engine will make outgoing HTTPS requests to the `haveibeenpwned.com` API.
- Only the specific domains found in your footprint are sent to the API to check for breaches.
- Your full email address is transmitted securely over HTTPS to the official HIBP `/breachedaccount` endpoint to retrieve matching breach domains. No other personal data is sent.
- This feature can be completely bypassed by not checking the HIBP toggle, allowing for a 100% offline database resolution using the local `sites.json`.
