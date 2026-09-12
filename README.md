# Backend Server

This repository contains the backend server codebase, deployment automation, and service configurations for Stephen Giang's infrastructure (`flash-server` at `dev.stepheng753.com`).

---

## 1. System Architecture

* **Domain & Reverse Proxy**:
  * Public Endpoint: `https://dev.stepheng753.com` (proxied via Nginx)
  * Nginx Unix Socket: `unix:/tmp/dev_stepheng753_com_api.sock`
  * ISP Port Handling: External HTTP requests route on port 8463 (redirecting to HTTPS 443 with Let's Encrypt certificates).
* **Application Server (Gunicorn & Systemd)**:
  * Systemd Service: `dev_stepheng753_com_api.service`
  * Working Directory: `/home/flash-server/Development/BackendServer`
  * Virtual Environment: `/home/flash-server/Development/BackendServer/.venv`
  * Execution Command: `gunicorn app:app --workers 4 --bind unix:/tmp/dev_stepheng753_com_api.sock -m 007 --timeout 300`
  * Restart Policy: `always`

> [!IMPORTANT]
> **Production Server Migration Note (`flash-server`)**:
> With the repository flattened, update `/etc/systemd/system/dev_stepheng753_com_api.service` on `flash-server` to point to the new working directory:
> ```ini
> WorkingDirectory=/home/flash-server/Development/BackendServer
> Environment="PATH=/home/flash-server/Development/BackendServer/.venv/bin"
> ExecStart=/home/flash-server/Development/BackendServer/.venv/bin/gunicorn --workers 4 --bind unix:/tmp/dev_stepheng753_com_api.sock -m 007 --timeout 300 app:app
> ```
> Then run `sudo systemctl daemon-reload && sudo systemctl restart dev_stepheng753_com_api.service`.

---

## 2. Core Modules & Endpoints

The centralized backend application lives directly at the repository root:

* **[`app.py`](./app.py)**: Flask entry point registering blueprints and global Basic Auth.
* **[`swagger/`](./swagger/)**: OpenAPI 3.0 interactive Swagger UI served at `/` and `/docs`.
* **[`index/`](./index/)**: Authentication middleware and credential verification.
* **[`config/`](./config/)**: Application configuration and secret files.
* **[`static/`](./static/)**: Favicon and branding assets (`flash.png`, `flash.gif`).
* **[`TutoringCalculator/`](./TutoringCalculator/)**: Core tutoring billing, Google Calendar parsing, Google Sheets management, and Twilio SMS notification workflows.

### Tutoring Calculator Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/dates` | `GET` | Computes previous Monday & following Sunday (`MM.DD.YY`). |
| `/copy-template` | `POST` | Copies master template into year folder named `MM.DD.YY - MM.DD.YY CALCULATED`, setting C1 and D1. |
| `/calc-hours` | `GET` | Parses Google Calendar for "Tutoring" events, aggregating hours by student first name. |
| `/previous-balances` | `GET` | Retrieves unpaid balances from the prior week's sheet (`Student Status == "Need to Pay"`). |
| `/update-sheet` | `POST` | Populates Column D (hours) and Column G (remaining balance), stopping before the subtotal row, and triggers notification email. |
| `/send-texts` | `POST` | Aborts if sheet title still contains `CALCULATED`. When approved, sends Twilio SMS payment reminders and updates status to `Need to Pay`. |
| `/text-logs` | `GET` | Returns audit logs from `text_messages.log`. |
| `/login_oauth` | `GET` | Google OAuth 2.0 flow for Drive, Sheets, Calendar, and Gmail permissions. |

---

## 3. Configuration & Secrets Architecture

Configuration is strictly separated into local configuration parameters and credentials:

1. **`config/config.json`** *(Ignored by Git)*:
   * Stores local deployment IDs, folder paths, Twilio Account SID & API Key, sender phone number, notification email, and host URL.
   * A blueprint is tracked in **`config/config.template.json`** for initial environment setup.
2. **`config/secrets.json`** *(Ignored by Git)*:
   * Stores private passwords, Twilio API secrets, and API keys.
3. **`config/StephenG753-OAuth.json`** *(Ignored by Git)*:
   * Client secrets for Google OAuth 2.0.
4. **`TutoringCalculator/keys/token.pickle`** *(Ignored by Git)*:
   * Offline Google OAuth credentials with auto-refresh token.

---

## 4. Usage & Local Development

### 4.1. Environment Setup
Create and activate the Python virtual environment at the repository root, then install all dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.2. Running the Development Server
Start the Flask server locally:
```bash
python3 app.py
# Or make app.py executable: ./app.py
```
*(By default, the server runs on `http://localhost:5000`)*

To run with Gunicorn locally:
```bash
gunicorn app:app --workers 2 --bind 0.0.0.0:5000
```

### 4.3. Interactive Swagger UI & Authentication
* **Swagger Console**: Visit `http://localhost:5000/` or `http://localhost:5000/docs` in your browser.
* **Authentication**: When prompted, log in with HTTP Basic Auth credentials configured in `config/secrets.json` (`USERNAME` / `PASSWORD`).
* **OpenAPI 3.0 Specification**: Accessible at `http://localhost:5000/openapi.json`.

### 4.4. Running Automation Scripts Manually
The cron calculation and text dispatch scripts can be triggered directly from the terminal:
```bash
# 1. Calculate tutoring hours from Google Calendar, create sheet, and send email:
python3 TutoringCalculator/scripts/run_calc.py

# 2. Dispatch Twilio SMS payment notices (after approving the sheet):
python3 TutoringCalculator/scripts/run_send_texts.py

# Optional: Run SMS dispatch for a specific Google Sheet ID:
python3 TutoringCalculator/scripts/run_send_texts.py <SHEET_ID>
```

### 4.5. Production Service Management (`flash-server`)
Manage the backend systemd service on `flash-server`:
```bash
# Check service status
sudo systemctl status dev_stepheng753_com_api.service

# Restart the service
sudo systemctl restart dev_stepheng753_com_api.service

# View live streaming service logs
sudo journalctl -u dev_stepheng753_com_api.service -f
```

---

## 5. CI/CD Deployment Pipeline

Deployments are automated through **[GitHub Actions](./.github/workflows/github_actions.yml)** upon every push to the `main` branch:

```
[Git Push to main]
       │
       ▼
[GitHub Actions Runner (ubuntu-latest)]
       │
       ▼
[Connect to Tailscale Network via OAuth]
       │
       ▼
[SSH into flash-server (100.66.69.41)]
       │
       ├─► git pull origin main
       ├─► Locate .venv/bin/pip (root or Flask-App fallback)
       ├─► $PIP_CMD install -r requirements.txt
       ├─► /home/flash-server/Services/restart_daemon.sh
       ├─► /home/flash-server/Services/Gunicorn/restart_gunicorn_service.sh
       └─► Health check: systemctl is-active dev_stepheng753_com_api.service
```

### GitHub Secrets Required
* `TS_OAUTH_CLIENT_ID`: Tailscale OAuth Client ID
* `TS_OAUTH_SECRET`: Tailscale OAuth Client Secret
* `SERVER_IP`: Production server Tailscale IP (`100.66.69.41`)
* `SSH_PRIVATE_KEY`: Private SSH key authorized in `/home/flash-server/.ssh/authorized_keys`

---

## 6. Cron Automation

Cron tasks on the production server can be scheduled via `crontab -e`:

```bash
# 1. Weekly Pay Calculation & Email Notice (Mondays at 4:00 AM)
0 4 * * 1 cd /home/flash-server/Development/BackendServer && /home/flash-server/Development/BackendServer/.venv/bin/python3 TutoringCalculator/scripts/run_calc.py >> /home/flash-server/.logs/cron_calc.log 2>&1

# 2. Weekly Text Dispatch Guarded by Approval (Mondays at 10:00 AM)
0 10 * * 1 cd /home/flash-server/Development/BackendServer && /home/flash-server/Development/BackendServer/.venv/bin/python3 TutoringCalculator/scripts/run_send_texts.py >> /home/flash-server/.logs/cron_texts.log 2>&1
```

---

## 7. Setup & Operations Documentation

All infrastructure, network, and reverse proxy setup documentation is located in **[`docs/setup/`](./docs/setup/)**:

* **[ServerSetUp.md](./docs/setup/ServerSetUp.md)**: Network architecture, port forwarding, DNS, SSL certbot automation, and complete Nginx operational management and troubleshooting.
* **[BackendSetUp.md](./docs/setup/BackendSetUp.md)**: Flask and Gunicorn Unix domain socket deployment guide and systemd configuration.
* **[nginx.conf.template](./docs/setup/nginx.conf.template)**: Nginx reverse-proxy template blocks (Unix socket, static + API, and local port).
* **[TutoringCalculator/README.md](./TutoringCalculator/README.md)**: Detailed Tutoring Calculator workflow, data schema, and endpoint references.
