<div align="center">

# ⚡ BackendServer
**Centralized Infrastructure API, System Telemetry & Operational Automation Hub**

[![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)](/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Swagger](https://img.shields.io/badge/OpenAPI-3.0-85EA2D?style=for-the-badge&logo=swagger&logoColor=black)](http://localhost:5000/docs)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Tailscale](https://img.shields.io/badge/Tailscale-Mesh-4E5EE4?style=for-the-badge&logo=tailscale&logoColor=white)](https://tailscale.com/)

*BackendServer is the production API engine, system telemetry monitor, and automation hub for Stephen Giang's infrastructure (`flash-server` at `dev.stepheng753.com`).*

---

</div>

## 📑 Table of Contents

- [🌟 Core Identity & Architecture](#-core-identity--architecture)
- [🛠️ Technology Stack](#️-technology-stack)
- [🏗️ Repository Structure](#️-repository-structure)
- [🖥️ System Monitoring Module](#️-system-monitoring-module)
- [🎓 Tutoring Calculator Automation](#-tutoring-calculator-automation)
- [📚 Project Documentation](#-project-documentation)
- [🔗 Internal Module References](#-internal-module-references)
- [🔐 Configuration & Secrets](#-configuration--secrets)
- [🚀 Local Development & Execution](#-local-development--execution)
- [⚙️ CI/CD Deployment & Cron Schedules](#️-cicd-deployment--cron-schedules)

---

## 🌟 Core Identity & Architecture

`BackendServer` provides centralized operational intelligence and business automation across Stephen Giang's homelab server (`flash-server`). It bridges public web requests, containerized microservices, Google Cloud workspace tools, and communication APIs into a unified platform.

```
[Public Web / Clients] ───> https://dev.stepheng753.com
                                   │
                                   ▼
                       [Nginx Reverse Proxy]
                      Terminates Let's Encrypt SSL
                                   │
                     (unix:/tmp/dev_stepheng753_com_api.sock)
                                   │
                                   ▼
                       [Gunicorn WSGI / Flask]
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  [Monitoring BP]           [Tutoring Calc BP]         [Swagger / OpenAPI]
  - Host Telemetry          - Calendar Scraper         - Interactive UI
  - Process Matrix          - Google Sheets Invoicing  - Basic Auth Security
  - 11-Service Probes       - Twilio SMS Reminders     - API Documentation
```

### 💼 Operational Philosophy
- **Lightweight & High-Performance:** Pure Python 3.12 with minimal dependencies; non-blocking telemetry collectors prevent event loop stalls.
- **Fail-Safe Business Logic:** Financial invoicing utilizes human-in-the-loop validation (`CALCULATED` title safeguard) before dispatching client notifications.
- **Zero Polling & Thread Safety:** Concurrent threaded socket probes evaluate service uptime in parallel with 0.5s tight timeouts.
- **Secure Encrypted Transport:** Tailscale mesh network for automated CI/CD deployments and internal administration.

---

## 🛠️ Technology Stack

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12"/>
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/Gunicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white" alt="Gunicorn"/>
  <img src="https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white" alt="Nginx"/>
  <img src="https://img.shields.io/badge/Let's_Encrypt-003A70?style=for-the-badge&logo=letsencrypt&logoColor=white" alt="Certbot"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker CE"/>
  <img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Google Cloud APIs"/>
  <img src="https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white" alt="Twilio SMS"/>
  <img src="https://img.shields.io/badge/Tailscale-4E5EE4?style=for-the-badge&logo=tailscale&logoColor=white" alt="Tailscale"/>
  <img src="https://img.shields.io/badge/Ubuntu_24.04-E95420?style=for-the-badge&logo=ubuntu&logoColor=white" alt="Ubuntu Server"/>
</p>

### Key Capabilities
1. **Host & Container Telemetry:** Real-time metrics on 12-thread CPU loads, package thermals, DDR4 RAM utilization, NVMe & 32TB HDD array storage pools, and top processes.
2. **Automated Weekly Billing Pipeline:** Parses Google Calendar events for tutoring hours, computes rollover balances, generates structured Google Sheets invoices, and dispatches customized SMS payment texts via Twilio.
3. **Interactive Developer Experience:** Built-in Swagger UI conforming to OpenAPI 3.0 specifications with HTTP Basic Authentication.
4. **Hardened Web Infrastructure:** Nginx reverse-proxy deployment with automated Let's Encrypt certificate renewal and dynamic DNS tracking.

---

## 🏗️ Repository Structure

| Directory / File | Description | Environment / Port |
| :--- | :--- | :--- |
| **[`app.py`](./app.py)** | Main Flask application entry point with blueprint registrations. | `localhost:5000` / Unix Socket |
| **[`Monitoring/`](./Monitoring/)** | System telemetry collectors (`collectors/`), process monitors, service probes, and HTML dashboard. | `/monitoring` |
| **[`TutoringCalculator/`](./TutoringCalculator/)** | Weekly invoicing engine, web dashboard (`/tutoring`), Google APIs integration, and Twilio SMS client. | `/tutoring`, `/dates`, etc. |
| **[`swagger/`](./swagger/)** | Interactive OpenAPI 3.0 Swagger documentation console and JSON spec generator. | `/`, `/docs`, `/openapi.json` |
| **[`index/`](./index/)** | HTTP Basic Auth middleware, security checkers, and route protection decorators. | Application middleware |
| **[`config/`](./config/)** | Environment configuration files and secrets schemas (`config.json`, `secrets.json`). | Application configuration |
| **[`static/`](./static/)** | Static brand assets (`flash.png`, `flash.gif`, favicon). | Web assets |
| **[`docs/`](./docs/)** | Comprehensive setup runbooks, monitoring architecture, and billing guides. | Documentation repository |

---

## 🖥️ System Monitoring Module

Accessible at `http://localhost:5000/monitoring` (or `https://dev.stepheng753.com/monitoring`), the web dashboard provides live visibility into `flash-server` health:

* **Top 10 Processes Table**: Real-time process listing with interactive **Sort by RAM** and **Sort by CPU** toggles, user badges, and memory metrics.
* **Storage Devices & Mounts**: Live capacity and usage tracking across all 5 flash-server storage pools (`/`, `Dragon-Ball`, `Photos`, `CapCut-Videos`, `TV-Series`).
* **Services Matrix**: Multi-threaded socket probes verifying uptime for 11 critical homelab services (`Immich`, `Jellyfin`, `qBittorrent`, `Gluetun`, `n8n`, `PostgreSQL`, `AIU`, `BackendServer`, `Nginx`, `Samba`, `Tailscale`).
* **Diagnostic Audit Suite**: One-click modal audit testing disk space, RAM pressure, CPU thermals, and background cron log freshness.
* **Unified Dark Mode**: Defaults to system color scheme with manual toggle button.

### Monitoring Endpoints
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/monitoring` | `GET` | Interactive Swagger-styled HTML Web Dashboard. |
| `/api/monitoring/system` | `GET` | Live CPU load %, core count, thermals, RAM, swap, and host specifications. |
| `/api/monitoring/processes` | `GET` | Top processes sorted by RAM or CPU utilization (`?sort=ram|cpu&limit=10`). |
| `/api/monitoring/storage` | `GET` | Partition and network share storage capacities, free space, and warning thresholds. |
| `/api/monitoring/services` | `GET` | Real-time health statuses and latency metrics for all 11 monitored services. |
| `/api/monitoring/diagnostics` | `GET` | Itemized audit report across disks, memory, thermals, services, and cron logs. |

---

## 🎓 Tutoring Calculator Automation & Web Dashboard

Accessible at `http://localhost:5000/tutoring` (or `https://dev.stepheng753.com/tutoring`), the web console provides one-click triggers, Google Sheet links, earnings modal summaries, text message audit logs, and direct access to the Google Drive Pay folder.

Weekly billing cycle runs Monday–Sunday:

```
Monday 04:00 AM PST ───> curl -u "$USER:$PASS" -X POST /tutoring/run-calc
                               │
                [Human Review Window: 8 Hours]
                               │
Monday 12:00 PM PST ───> curl -u "$USER:$PASS" -X POST /tutoring/run-send-texts
```

### Tutoring Calculator Endpoints
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/tutoring` | `GET` | Interactive HTML Web Dashboard with one-click actions, modals, and dark mode. |
| `/tutoring/status` | `GET` | Live billing dates, Google auth state, current week sheet metadata, and Drive folder links. |
| `/tutoring/run-calc` | `POST` | One-click full pay calculation: clones template, scrapes hours, checks balances, updates sheet, and emails summary. |
| `/tutoring/run-send-texts` | `POST` | One-click SMS dispatch: evaluates `CALCULATED` title safeguard, sends Twilio texts, and updates statuses. |
| `/dates` | `GET` | Computes preceding Monday & following Sunday billing week dates (`MM.DD.YY`). |
| `/copy-template` | `POST` | Clones master template into target year folder named `MM.DD.YY - MM.DD.YY CALCULATED`. |
| `/calc-hours` | `GET` | Scrapes Google Calendar for sessions ending in "Tutoring" and consolidates hours. |
| `/previous-balances` | `GET` | Queries prior week's sheet for students marked `"Need to Pay"`. |
| `/update-sheet` | `POST` | Injects hours into Column D, unpaid balances into Column G, and sends notification email. |
| `/send-texts` | `POST` | Low-level text dispatch route guarded by `CALCULATED` approval check. |
| `/text-logs` | `GET` | Returns raw audit log of all dispatched text messages (`text_messages.log`). |
| `/login_oauth` | `GET` | Google OAuth 2.0 web consent flow for Calendar, Drive, Sheets, and Gmail scopes. |

---

## 📚 Project Documentation

Explore the following modular documentation files for end-to-end setup and architecture details:

### 🛠️ Infrastructure & Web Deployment (`docs/setup/`)
* **[Server Hardware & Environment Setup](docs/setup/server.md)** — Host machine provisioning (Ubuntu 24.04 LTS, UFW firewall, Docker CE, Node.js, Python, storage mounts, systemd timers).
* **[Website & Nginx Projects Deployment](docs/setup/website.md)** — Nginx reverse proxy configurations, PM2 process management, Docker web containers, and Python WSGI socket deployment.
* **[Hostinger DNS & Certbot SSL Guide](docs/setup/dns-and-ssl.md)** — Hostinger DNS CNAME configuration, TP-Link Deco DDNS routing, router port forwarding, and automated Let's Encrypt SSL.
* **[Nginx Template Configuration](docs/setup/nginx.conf.template)** — Production-tested Nginx reverse-proxy template blocks (Unix socket, static + API, and local port).
* **[Setup Reference Specification](docs/setup/setup.conf)** — Master network configuration and subdomain routing definitions.

### 🖥️ System Telemetry & Monitoring (`docs/monitoring/`)
* **[Monitoring Architecture & Endpoints](docs/monitoring/architecture.md)** — Non-blocking telemetry collectors, multi-threaded socket probes, memory/CPU metrics, and REST API specification.
* **[Services Matrix & Probes](docs/monitoring/services-matrix.md)** — Detailed specification for the 11 monitored services, port mappings, and alert threshold triggers.
* **[Dashboard Operations Guide](docs/monitoring/dashboard-guide.md)** — Visual design guide, process table sort controls, refresh intervals, and diagnostic audit suite usage.

### 🎓 Tutoring Invoicing Pipeline (`docs/tutoring-calc/`)
* **[Billing Workflow & Endpoints](docs/tutoring-calc/billing-workflow.md)** — Weekly billing cycle, calendar scraping mechanics, rate lookups, and spreadsheet updates.
* **[Approval Safeguards & SMS Text Dispatch](docs/tutoring-calc/approval-safeguard.md)** — Human-in-the-loop review, `CALCULATED` title safety gate, Twilio SMS text dispatch, and audit logging.
* **[Automation & Google OAuth 2.0 Setup](docs/tutoring-calc/automation-and-oauth.md)** — Crontab automation schedules, script workflows, and Google OAuth 2.0 token management.

---

## 🔗 Internal Module References

For module-specific developer documentation and code architecture, refer to:
* **[Monitoring Module Documentation](Monitoring/README.md)** — Deep dive into the telemetry package, collector functions, and UI template.
* **[Tutoring Calculator Documentation](TutoringCalculator/README.md)** — Internal script details, API helpers, and logging structure.

---

## 🔐 Configuration & Secrets

Configuration parameters and secret credentials are kept strictly isolated:

1. **`config/config.json`** *(Ignored by Git)*:
   * Stores deployment folder IDs, Google Calendar ID, Twilio Account SID, Twilio API Key SID, sender phone number, notification email, and host URL.
   * Blueprint tracked in **`config/config.template.json`** for initial setup.
2. **`config/secrets.json`** *(Ignored by Git)*:
   * Stores Swagger Basic Auth credentials (`USERNAME` / `PASSWORD`) and `TWILIO_API_SECRET`.
3. **`config/StephenG753-OAuth.json`** *(Ignored by Git)*:
   * Client secret credentials file downloaded from Google Cloud Console.
4. **`TutoringCalculator/keys/token.pickle`** *(Ignored by Git)*:
   * Serialized Google OAuth 2.0 offline access token and auto-refresh token.

---

## 🚀 Local Development & Execution

### 1. Environment Setup
```bash
# Clone and enter directory
cd /home/stepheng753/Development/BackendServer

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Running Locally
```bash
# Launch development server
python3 app.py
```
* The local server will be accessible at `http://localhost:5000`.
* Open `http://localhost:5000/docs` to view the interactive Swagger UI.
* Open `http://localhost:5000/monitoring` to view the real-time hardware telemetry dashboard.
* Open `http://localhost:5000/tutoring` to view the interactive Crossroads Tutoring Console.

---

## ⚙️ CI/CD Deployment & Cron Schedules

### Production Service Management (`flash-server`)
```bash
# Check service status
sudo systemctl status dev_stepheng753_com_api.service

# Restart application daemon
sudo systemctl restart dev_stepheng753_com_api.service

# Stream live production logs
sudo journalctl -u dev_stepheng753_com_api.service -f
```

### Automated Monday Crontab
On `flash-server`, schedule the automated billing workflow via `crontab -e`:
```bash
# 1. Weekly Pay Calculation: Monday 4:00 AM PST (12:00 UTC)
0 12 * * 1 curl -sS -u "$USERNAME:$PASSWORD" -X POST https://dev.stepheng753.com/tutoring/run-calc >> /home/flash-server/Development/BackendServer/TutoringCalculator/logs/cron.log 2>&1

# 2. Text Message Dispatch Guarded by Approval: Monday 12:00 PM PST (20:00 UTC)
0 20 * * 1 curl -sS -u "$USERNAME:$PASSWORD" -X POST https://dev.stepheng753.com/tutoring/run-send-texts >> /home/flash-server/Development/BackendServer/TutoringCalculator/logs/cron.log 2>&1
```
*(Or target the local socket directly: `curl -sS -u "$USERNAME:$PASSWORD" --unix-socket /tmp/dev_stepheng753_com_api.sock -X POST http://localhost/tutoring/run-calc ...`)*

---

<div align="center">
  <i>Developed and engineered for Stephen Giang's Production Infrastructure</i>
</div>
