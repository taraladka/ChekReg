# System Architecture

ChekReg is built as a highly robust, zero-trust footprint analysis engine. It leverages raw IMAP telemetry to reverse-engineer a user's digital footprint entirely on their local machine.

## High-Level Data Flow

1. **IMAP Telemetry Extraction**: Connects directly to the user's IMAP server using Python's native `imaplib`.
2. **Payload Parsing**: Evaluates standard headers (`From`, `Date`, `List-Unsubscribe`).
3. **Database Resolution**: Cross-references parsed domains against the `data/sites.json` database.
4. **Scoring Engine**: Evaluates metadata (last active date, breach status) to generate a Safety Score.
5. **UI Streaming**: Emits parsed, filtered JSON blobs for the frontend to consume via client polling.

---

## 1. The Core Engine (`engine.py`)

The `engine.py` script houses the `FootprintEngine`. This is the brain of the project.

### Phase 1: Authentication
Uses `IMAP4_SSL` to bind to standard ports (default: 993). Standard password authentication is blocked by most modern mail providers, necessitating the use of App Passwords.

### Phase 2: Metadata Extraction
Instead of downloading gigabytes of email bodies, the engine strictly fetches headers (`RFC822.HEADER`). This makes it exceptionally fast. It specifically hunts for:
*   `From`: To identify the service domain.
*   `List-Unsubscribe`: Crucial for tracking marketing noise and providing 1-click opt-outs.
*   `Date`: Essential for generating "Ghost Account" heuristics.

### Phase 3: Resolution (`sites.json`)
Every unique extracted domain is mapped against our `sites.json` database. The database provides the "friendly name", expected categories, and direct `delete_url` endpoints.

---

## 2. The Web Server (`server.py`)

The application avoids heavy, bloated cloud frameworks by running an ephemeral, lightweight `Flask` server strictly on `localhost:5000`. 

**Client Polling**: The server utilizes lightweight endpoints (`/api/status`) to provide live progress telemetry. During the engine scan, the frontend periodically polls to get:
1.  `status` frames: `{"status": "scanning", "progress": 30}`
2.  `complete` payload: Drops the final processed footprint payload for the UI to consume and render via `/api/results`.

---

## 3. The Frontend Client (`static/`)

The client is built exclusively using Vanilla HTML, CSS, and Javascript. 
- **Zero-Dependency**: No React, No Vue, No Tailwind. This ensures the footprint of the app remains incredibly small and easy to audit for security.
- **Dynamic Filtering**: The `script.js` evaluates boolean flags (`o.is_newsletter`, `o.is_inactive`, `o.is_breached`) sent by the backend payload to dynamically filter the UI rendering.

## 4. Privacy & Zero-Trust Constraints

The architecture was deliberately designed around the principles of Zero-Trust:
1.  **No Telemetry**: No tracking pixels, no analytics, no crash reporting.
2.  **No Cloud Proxies**: The IMAP connection goes from `localhost` -> `imap.provider.com`.
3.  **No Persistent Credential Storage**: App Passwords are held strictly in active memory and destroyed when the terminal process exits. 
