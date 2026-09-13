# Tutoring Calculator Automation & Google OAuth 2.0 Setup

This document details the **automated cron job schedules** and the **Google OAuth 2.0 & Twilio credentials setup** powering the `TutoringCalculator` module.

---

## 1. Automated Cron Schedules

The tutoring billing pipeline runs on two scheduled cron scripts every Monday on the host machine (`flash-server`):

```
Monday 04:00 AM PST ───> run_calc.py        (Parses hours, creates sheet, sends email)
                               │
                [Human Review Window: 8 Hours]
                               │
Monday 12:00 PM PST ───> run_send_texts.py (Checks title approval, sends SMS notifications)
```

### 1.1. Script Reference

#### `run_calc.py` (Script 1)
* **Path**: `TutoringCalculator/scripts/run_calc.py`
* **Schedule**: Every Monday at `04:00 AM` PST
* **Responsibilities**:
  1. Computes preceding Monday–Sunday date range.
  2. Copies master template sheet into Google Drive target year folder (`PAY_PARENT_FOLDER_ID`).
  3. Titles the copy `MM.DD.YY - MM.DD.YY CALCULATED`.
  4. Scrapes Google Calendar for tutoring sessions and updates hours in Column D.
  5. Scrapes previous week's sheet for unpaid balances and updates Column G.
  6. Sends calculation summary email with direct spreadsheet link to `stepheng753@gmail.com`.

#### `run_send_texts.py` (Script 2)
* **Path**: `TutoringCalculator/scripts/run_send_texts.py`
* **Schedule**: Every Monday at `12:00 PM` (Noon) PST
* **Responsibilities**:
  1. Locates the current week's sheet in Google Drive.
  2. **Safeguard Check**: If title still contains `CALCULATED`, aborts immediately.
  3. If approved, iterates over students with balances and blank status.
  4. Sends SMS via Twilio API with invoice breakdown and payment details.
  5. Updates student status to `"Need to Pay"` in Column B.
  6. Appends audit log to `TutoringCalculator/logs/text_messages.log`.

---

### 1.2. Crontab Configuration on Production Server

Edit your server user's crontab:
```bash
crontab -e
```

Add the following entries (pointing to the Python executable inside your virtual environment):

```bash
# -----------------------------------------------------------------------------
# Crossroads Tutoring Weekly Automation Pipeline
# -----------------------------------------------------------------------------
# 1. Weekly Pay Calculation: Monday 4:00 AM PST (12:00 UTC)
0 12 * * 1 /home/stepheng753/Development/BackendServer/.venv/bin/python /home/stepheng753/Development/BackendServer/TutoringCalculator/scripts/run_calc.py >> /home/stepheng753/Development/BackendServer/TutoringCalculator/logs/cron.log 2>&1

# 2. Text Message Dispatch: Monday 12:00 PM PST (20:00 UTC)
0 20 * * 1 /home/stepheng753/Development/BackendServer/.venv/bin/python /home/stepheng753/Development/BackendServer/TutoringCalculator/scripts/run_send_texts.py >> /home/stepheng753/Development/BackendServer/TutoringCalculator/logs/cron.log 2>&1
```

> [!NOTE]
> Adjust UTC hours if your server timezone is set to `America/Los_Angeles` rather than `UTC`. If `date` returns PST/PDT:
> * `0 4 * * 1` (4:00 AM local time)
> * `0 12 * * 1` (12:00 PM local time)

---

## 2. Google OAuth 2.0 Token Lifecycle

`TutoringCalculator` accesses Google Drive, Sheets, Calendar, and Gmail using an OAuth 2.0 User Token (`token.pickle`).

### 2.1. Required Google API Scopes
The application requires the following scopes defined in `google_auth.py`:
* `https://www.googleapis.com/auth/calendar.readonly`: Reads tutoring event names and durations.
* `https://www.googleapis.com/auth/drive`: Creates year folders and copies template spreadsheets.
* `https://www.googleapis.com/auth/spreadsheets`: Reads and writes student hours, balances, and payment statuses.
* `https://www.googleapis.com/auth/gmail.send`: Sends notification emails to Stephen.

### 2.2. Initial OAuth Authorization Flow
1. Obtain the Google Client Secret JSON file from Google Cloud Console.
2. Save it to `config/StephenG753-OAuth.json` (configured in `config/config.json`).
3. Start the Backend Server:
   ```bash
   ./app.py
   ```
4. In a web browser, navigate to the authorization route:
   * Local WSL: `http://localhost:5000/TutoringCalculator/login_oauth`
   * Production: `https://dev.stepheng753.com/TutoringCalculator/login_oauth`
5. Sign in with the primary Google account (`stepheng753@gmail.com`) and click **Allow**.
6. The callback handler exchanges the authorization code for an **Access Token** and **Refresh Token**, and serializes them to:
   `TutoringCalculator/keys/token.pickle`

### 2.3. Automatic Token Refresh
Whenever an API request is made:
1. `get_credentials()` loads `token.pickle`.
2. If the access token has expired (typically after 60 minutes), the library uses `creds.refresh(Request())` with the persistent refresh token.
3. The newly issued access token is saved back to `token.pickle` automatically. No manual intervention is needed.

> [!WARNING]
> If your Google Cloud project is in **"Testing"** publishing status, Google limits refresh token validity to **7 days**. Ensure your Google Cloud OAuth Consent Screen is published to **"Production"** or add your user email as a permanent test user to prevent weekly re-authorization.

---

## 3. Configuration & Secrets (`config.json` & `secrets.json`)

Configuration parameters are stored in `config/config.json` and sensitive tokens in `config/secrets.json`:

### `config/config.json`
```json
{
  "GOOGLE_CALENDAR_ID": "primary",
  "PAY_PARENT_FOLDER_ID": "12hcaaHrab8TCFO8hi_cC67FRBHIU-Xsx",
  "TEMPLATE_SHEET_ID": "1S5f5pKJZAvEW49sOrv-mbA7bqZs9_93WbcUNCNMHJBA",
  "NOTIFICATION_EMAIL": "stepheng753@gmail.com",
  "APP_HOST": "localhost:5000",
  "OAUTH_FILE": "StephenG753-OAuth.json",
  "TWILIO_ACCOUNT_SID": "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "TWILIO_API_KEY_SID": "SKXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "TWILIO_FROM_NUMBER": "+16195550100"
}
```

### `config/secrets.json`
```json
{
  "TWILIO_API_SECRET": "your_twilio_api_secret_here"
}
```
*(Ensure `secrets.json` is listed in `.gitignore` so tokens are never committed to version control).*
