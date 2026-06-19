# Platforms Used in Setup

chekreg relies on a small number of external platforms to do its job. This file explains what each one is, why it's needed, and what it actually does — so you're not just clicking through setup steps blindly.

---

## Google Cloud Console

**URL:** https://console.cloud.google.com/  
**Used for:** Creating the project that owns your OAuth credentials

Google Cloud Console is the management interface for **Google Cloud Platform (GCP)** — Google's full cloud computing infrastructure, the same platform that competes with Amazon Web Services (AWS) and Microsoft Azure. It offers virtual machines, databases, storage buckets, machine learning services, networking, and much more. Large companies run entire production systems on it.

chekreg uses a tiny, entirely free corner of it: the ability to register an application and enable APIs. You're not provisioning any servers or cloud resources — you're just creating a record that says "this app called chekreg is allowed to call the Gmail API." That's all a GCP project is in this context: an organisational container that Google requires before it will issue API credentials.

For chekreg, you create a **project** here — think of it as a named slot that tells Google "this application wants permission to read Gmail." The project itself doesn't run anything; it's just the wrapper that the API enablement and the OAuth credentials live under.

**You need a Google account to use it, but you don't need to pay anything or enter payment details.** The Gmail API and OAuth for personal/desktop use fall entirely within Google's free tier.

**What chekreg uses it for:** One-time setup only. After you've downloaded `credentials.json`, you never need to go back to Cloud Console unless you want to revoke access or regenerate credentials.

---

## Gmail API

**URL:** https://console.cloud.google.com/apis/library/gmail.googleapis.com  
**Used for:** Actually reading your emails

The Gmail API is a Google service that lets applications read (and optionally modify) Gmail inboxes programmatically. chekreg uses it to search your inbox and fetch email headers — the sender address, subject line, date, and unsubscribe header.

It does **not** read email bodies. It never sends, deletes, or modifies anything. The access scope requested is `gmail.readonly`, which is the most restricted scope Gmail offers.

**How it works at runtime:** Every time you run chekreg, it calls the Gmail API with search queries like `subject:"verify" OR subject:"confirm"`. The API returns matching message IDs, then chekreg fetches the headers for each one. That's the entirety of the Gmail interaction.

**Why you have to enable it manually:** Google requires developers to explicitly enable each API they use inside a Cloud project. This is a safety measure — it means an application can't quietly start accessing your Gmail without that permission being on record.

---

## Google OAuth 2.0

**Used for:** Proving to Gmail that you've authorised chekreg to read your inbox  
**Files involved:** `credentials.json` (identity of the app), `token.json` (your saved permission)

OAuth 2.0 is the standard protocol that lets you grant an application access to your account without giving it your password. You've used it every time you've clicked "Sign in with Google" on a third-party website.

Here's what happens the first time you run chekreg:

1. chekreg reads `credentials.json` to identify itself to Google
2. It opens a browser and sends you to a Google consent screen
3. You review the permissions (read-only Gmail access) and click **Allow**
4. Google sends back a token — a time-limited key that proves you said yes
5. chekreg saves that token to `token.json` so you don't have to log in again

On subsequent runs, chekreg just loads `token.json`. If the token has expired, it automatically refreshes it using a refresh token embedded in the same file, so you still don't need to log in again.

**`credentials.json`** identifies the application (like a username for the app itself).  
**`token.json`** records your personal authorisation (like a session cookie).

Both files should be kept private. Anyone with them can read your Gmail until you revoke access at https://myaccount.google.com/permissions.

---

## Have I Been Pwned (HIBP)

**URL:** https://haveibeenpwned.com  
**Used for:** Checking whether your email appeared in known data breaches  
**Required:** Free API key (get one at https://haveibeenpwned.com/API/Key)

Have I Been Pwned is a security service run by researcher Troy Hunt. It aggregates data from publicly disclosed data breaches — when a company is hacked and user records leak, HIBP collects and indexes those records so individuals can check if their email was exposed.

chekreg uses HIBP's `/breachedaccount` API endpoint. It sends your email address to HIBP and gets back a list of breaches that email appeared in, along with which domains were involved. chekreg then cross-references those domains against the accounts it found in your inbox, so the breach section of the report shows you exactly which of your active services were compromised.

**Privacy note:** Your email address is sent to HIBP's servers for this check. HIBP is a well-regarded, privacy-conscious service — it does not store or log the email addresses queried — but if you'd rather not send your email to any external service, run chekreg with `--no-hibp` to skip this step entirely.

**Why an API key is needed:** HIBP's `/breachedaccount` endpoint has required a free API key since 2024 to prevent abuse. The key is free for personal use. Set it as an environment variable before running chekreg:

```bash
export HIBP_API_KEY=your_key_here
```

Without the key, the breach check is silently skipped and chekreg will note this in the output.

---

## Summary

| Platform | What it is | Free? | Required? |
|---|---|---|---|
| Google Cloud Console | Google's cloud platform (AWS/Azure equivalent) — chekreg uses only the free API registration corner of it | Yes | Yes (one-time setup) |
| Gmail API | Google service that reads your inbox | Yes | Yes |
| Google OAuth 2.0 | Auth protocol — grants chekreg inbox access without your password | Yes | Yes |
| Have I Been Pwned | Breach database to check if your email was leaked | Free API key | No (skip with `--no-hibp`) |
