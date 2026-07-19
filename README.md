# Hiking Club Stats App — Setup Guide

A Streamlit app that reads two Google Sheets live and lets members look up
their own stats via a shared link, no login required.

## 1. Edit the config in `app.py`

At the top of `app.py`, update:
- `SPREADSHEET_URL` — the URL of your Google Sheet (the one with the
  "Individual Stats", "Award Leaderboards", and "Leader Stats" tabs)

The tab names (`INDIVIDUAL_WS_NAME`, `LEADERBOARD_WS_NAME`, `LEADER_WS_NAME`)
and column layout already match your actual spreadsheet, based on the file
you shared:
- **Individual Stats**: Name, Attendance Count, Total Distance, Total Height
  Gain, Mean Distance, Mean Height Gain
- **Award Leaderboards**: five side-by-side ranked Name/Value column pairs
  (metadata in rows 1–3, headers in row 4, data from row 5)
- **Leader Stats**: Leader Name, then lead-type counts (Solo-lead, Co-lead,
  Assessor, Nav Course, Shadow Assess.) and route-grade counts (Green,
  Yellow, Red, D. Red, Technical Winter, Expedition, Fell Run) — two-row
  header, data from row 3

If you rename a tab or add/remove/reorder columns in the sheet later, update
the matching constant near the top of `app.py`.

## 2. Create a Google service account (so the app can read your sheets)

This is a one-time setup, takes about 5 minutes.

1. Go to https://console.cloud.google.com/ and create a new project (or use an existing one).
2. In the search bar, enable these two APIs:
   - "Google Sheets API"
   - "Google Drive API"
3. Go to **APIs & Services → Credentials → Create Credentials → Service Account**.
   - Give it any name, e.g. `hiking-stats-reader`.
   - Skip granting it project roles — not needed.
4. Once created, click into the service account → **Keys** tab → **Add Key → Create new key → JSON**.
   This downloads a `.json` file — keep it private, don't commit it to GitHub.
5. Open that JSON file and copy the value of `"client_email"` — it'll look like
   `hiking-stats-reader@your-project.iam.gserviceaccount.com`.
6. Open your Google Sheet, click **Share**, and share it with that email
   address as a **Viewer**.

## 3. Add your credentials as Streamlit secrets

Streamlit reads secrets from a file called `secrets.toml`.

**For local testing:**
Create a folder `.streamlit/` next to `app.py`, and inside it a file
`.streamlit/secrets.toml` with this content (copy values straight from your
downloaded JSON key file):

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_KEY_HERE\n-----END PRIVATE KEY-----\n"
client_email = "hiking-stats-reader@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"
```

Important: keep the `\n` characters inside `private_key` exactly as they
appear in the JSON file (as literal `\n`, not actual line breaks).

**Never commit `secrets.toml` to a public GitHub repo.** Add it to `.gitignore`.

## 4. Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`.

## 5. Deploy it for free so the club can access it

1. Push this folder to a GitHub repo (excluding `secrets.toml` — add a
   `.gitignore` with `.streamlit/secrets.toml` in it).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app**, pick your repo, branch, and `app.py` as the entry point.
4. Before deploying (or after, in **Settings → Secrets**), paste the same
   contents from your local `secrets.toml` into the app's Secrets box.
5. Deploy. You'll get a public URL like `https://your-app-name.streamlit.app`
   — share that link with the club.

The app will auto-refresh data from your Google Sheets every 5 minutes
(you can change `CACHE_TTL_SECONDS` in `app.py`).

## Notes / things you may want to tweak

- Right now it shows *every* column from Individual Stats and Leader Stats
  (except the name column). If some columns are internal/private, filter
  them out before display.
- Leader Stats hides any stat that's zero (e.g. a leader with no "Assessor"
  leads won't see that row) to keep the table readable — remove that filter
  in `app.py` if you'd rather show everything including zeros.
- Leaderboard rank is computed as the person's position within each
  category's sorted column, independent of the sheet's own "Rank" column
  (which has some blank cells for tied entries). This means rank numbers
  are always consistent even where the sheet's own rank column isn't.
- The name dropdown assumes names in "Individual Stats" are unique. If two
  people share a name, you may want to add a second identifier column
  (e.g. email) to disambiguate.
- If someone doesn't appear on any leaderboard (the list only goes down to
  a limited length), the app shows a friendly "keep hiking!" message instead
  of an error.
