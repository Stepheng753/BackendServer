import json
import os
from flask import Blueprint, jsonify, render_template_string, send_from_directory

swagger_bp = Blueprint('swagger', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')


def load_app_host():
    for folder in [CONFIG_DIR, BASE_DIR]:
        config_path = os.path.join(folder, 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f).get('APP_HOST')
            except Exception:
                pass
    return None


app_host = load_app_host()
servers = [{"url": "/", "description": "Current Server Host"}]
if app_host:
    servers.append({"url": app_host, "description": "Dev Production Server"})
servers.append({"url": "http://localhost:5000", "description": "Local Development Server"})

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Flash Server API",
        "description": "Interactive API Documentation and Test Execution Console for Stephen Giang's Flash Server Backend.",
        "version": "1.0.0"
    },
    "servers": servers,
    "tags": [
        {
            "name": "Tutoring Calculator",
            "description": "Crossroads Tutoring weekly billing, calendar event parsing, sheet management, Twilio reminders, and OAuth."
        },
        {
            "name": "Monitoring",
            "description": "Flash Server hardware telemetry, disk storage monitoring, service health matrix, and diagnostic test suite."
        }
    ],
    "components": {
        "securitySchemes": {
            "basicAuth": {
                "type": "http",
                "scheme": "basic",
                "description": "HTTP Basic Authentication using USERNAME and PASSWORD"
            }
        }
    },
    "security": [
        {"basicAuth": []}
    ],
    "paths": {
        "/test": {
            "get": {
                "tags": ["Tutoring Calculator"],
                "summary": "Health Check / Ping",
                "description": "Simple test endpoint to verify server status.",
                "responses": {
                    "200": {
                        "description": "Server is up and running."
                    }
                }
            }
        },
        "/dates": {
            "get": {
                "tags": ["Tutoring Calculator"],
                "summary": "Get Billing Date Range",
                "description": "Calculates the previous Monday date (or previous Monday if today is Monday) and the following Sunday in MM.DD.YY format.",
                "responses": {
                    "200": {
                        "description": "Calculated start_date and end_date.",
                        "content": {
                            "application/json": {
                                "example": {
                                    "start_date": "08.31.26",
                                    "end_date": "09.06.26",
                                    "start_date_full": "2026-08-31",
                                    "end_date_full": "2026-09-06"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/copy-template": {
            "post": {
                "tags": ["Tutoring Calculator"],
                "summary": "Copy Student Pay Template Sheet",
                "description": "Copies the master template sheet into the year folder, renames it to 'MM.DD.YY - MM.DD.YY CALCULATED', updates C1 (start date) and D1 (end date), and returns the sheet ID and editable URL.",
                "parameters": [
                    {
                        "name": "start_date",
                        "in": "query",
                        "required": False,
                        "description": "Start date in MM.DD.YY or YYYY-MM-DD format. If omitted, automatically computed.",
                        "schema": {"type": "string"}
                    },
                    {
                        "name": "end_date",
                        "in": "query",
                        "required": False,
                        "description": "End date in MM.DD.YY or YYYY-MM-DD format. If omitted, automatically computed.",
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Template copied successfully.",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "sheet_id": "1S5f5pKJZAvEW49sOrv-mbA7bqZs9_93WbcUNCNMHJBA",
                                    "sheet_url": "https://docs.google.com/spreadsheets/d/1S5f5pKJZAvEW49sOrv-mbA7bqZs9_93WbcUNCNMHJBA/edit",
                                    "title": "08.31.26 - 09.06.26 CALCULATED"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/calc-hours": {
            "get": {
                "tags": ["Tutoring Calculator"],
                "summary": "Calculate Tutoring Hours from Google Calendar",
                "description": "Queries the 'Tutoring' calendar for events ending in 'Tutoring' with default/primary color, consolidating hours by student's first name.",
                "parameters": [
                    {
                        "name": "start_date",
                        "in": "query",
                        "required": True,
                        "description": "Start date in MM.DD.YY or YYYY-MM-DD format",
                        "schema": {"type": "string"}
                    },
                    {
                        "name": "end_date",
                        "in": "query",
                        "required": True,
                        "description": "End date in MM.DD.YY or YYYY-MM-DD format",
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Tutoring hours consolidated by student name.",
                        "content": {
                            "application/json": {
                                "example": {
                                    "Elijah": 3.0,
                                    "Ellie": 4.5,
                                    "Amelie": 4.0,
                                    "Michael": 5.75,
                                    "Jack": 3.0
                                }
                            }
                        }
                    }
                }
            }
        },
        "/previous-balances": {
            "get": {
                "tags": ["Tutoring Calculator"],
                "summary": "Fetch Prior Week's Unpaid Balances",
                "description": "Finds the sheet for the previous week (7 days prior to start_date) and returns all students whose status is 'Need to Pay' along with their Total Balance.",
                "parameters": [
                    {
                        "name": "start_date",
                        "in": "query",
                        "required": True,
                        "description": "Start date of current week (MM.DD.YY)",
                        "schema": {"type": "string"}
                    },
                    {
                        "name": "end_date",
                        "in": "query",
                        "required": False,
                        "description": "End date of current week (MM.DD.YY)",
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Previous balances by student first name.",
                        "content": {
                            "application/json": {
                                "example": {
                                    "Elijah": 180.0,
                                    "Ellie": 270.0
                                }
                            }
                        }
                    }
                }
            }
        },
        "/update-sheet": {
            "post": {
                "tags": ["Tutoring Calculator"],
                "summary": "Update Sheet Hours or Pay Statuses",
                "description": "Action 'update_hours': reads C1/D1 dates, fetches calc-hours and previous-balances, and updates Column D (# Hours) and Column G (Remaining Balance). Action 'update_pay_status': converts blank statuses for active students to 'Need to Pay'.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["sheet_id", "action"],
                                "properties": {
                                    "sheet_id": {"type": "string", "description": "Google Sheet ID to update"},
                                    "action": {
                                        "type": "string",
                                        "enum": ["update_hours", "update_pay_status"],
                                        "description": "Action to perform"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Sheet updated successfully.",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "sheet_id": "1S5f5pKJZAvEW49sOrv-mbA7bqZs9_93WbcUNCNMHJBA",
                                    "sheet_url": "https://docs.google.com/spreadsheets/d/1S5f5pKJZAvEW49sOrv-mbA7bqZs9_93WbcUNCNMHJBA/edit",
                                    "action": "update_hours"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/send-texts": {
            "post": {
                "tags": ["Tutoring Calculator"],
                "summary": "Send SMS Payment Reminders via Twilio",
                "description": "Checks sheet title for 'CALCULATED' (aborts if present). If approved, sends SMS reminders to parents for students with Total Balance > 0 and blank status, updates status to 'Need to Pay', logs to text_messages.log.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["sheet_id"],
                                "properties": {
                                    "sheet_id": {"type": "string", "description": "Google Sheet ID"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "SMS processing complete.",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "sent_count": 5,
                                    "messages": [
                                        {"student": "Elijah Dinh", "phone": "+19512190584", "status": "sent"}
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        "/text-logs": {
            "get": {
                "tags": ["Tutoring Calculator"],
                "summary": "Retrieve Text Message Audit Logs",
                "description": "Returns the contents of text_messages.log containing full history of sent SMS payment notices.",
                "responses": {
                    "200": {
                        "description": "Log file content.",
                        "content": {
                            "text/plain": {
                                "example": "[2026-09-07 10:00:01 PST] SENT to Ms. Sandy (+19512190584) for Elijah Dinh: Elijah: $180.00..."
                            }
                        }
                    }
                }
            }
        },
        "/login_oauth": {
            "get": {
                "tags": ["Tutoring Calculator"],
                "summary": "Google OAuth 2.0 Login / Callback",
                "description": "Initiates Google OAuth 2.0 authorization or handles the redirect callback to acquire offline credentials with auto-refresh.",
                "responses": {
                    "302": {
                        "description": "Redirects to Google consent screen or returns to docs after login."
                    }
                }
            }
        },
        "/monitoring": {
            "get": {
                "tags": ["Monitoring"],
                "summary": "System Health & Telemetry Web Dashboard",
                "description": "Renders the interactive dashboard UI displaying hardware telemetry, storage shares, top processes, and service status.",
                "responses": {
                    "200": {
                        "description": "HTML Dashboard rendered."
                    }
                }
            }
        },
        "/api/monitoring/system": {
            "get": {
                "tags": ["Monitoring"],
                "summary": "System & Hardware Telemetry",
                "description": "Returns CPU load %, core count, load averages, temperature, RAM/Swap metrics, and host/kernel specs.",
                "responses": {
                    "200": {
                        "description": "JSON hardware and host specifications."
                    }
                }
            }
        },
        "/api/monitoring/processes": {
            "get": {
                "tags": ["Monitoring"],
                "summary": "Top Processes by RAM or CPU",
                "description": "Returns list of top running processes sorted by RAM (RSS) or CPU utilization.",
                "parameters": [
                    {
                        "name": "sort",
                        "in": "query",
                        "required": False,
                        "description": "Sort metric: 'ram' (default) or 'cpu'.",
                        "schema": {"type": "string", "enum": ["ram", "cpu"], "default": "ram"}
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "description": "Number of processes to return (default 10).",
                        "schema": {"type": "integer", "default": 10}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "JSON list of top processes."
                    }
                }
            }
        },
        "/api/monitoring/storage": {
            "get": {
                "tags": ["Monitoring"],
                "summary": "Storage Devices & Mounts",
                "description": "Returns capacity, usage, and alert status for all mounted disks and flash-server network shares.",
                "responses": {
                    "200": {
                        "description": "JSON array of storage partitions."
                    }
                }
            }
        },
        "/api/monitoring/services": {
            "get": {
                "tags": ["Monitoring"],
                "summary": "Services & Docker Health Matrix",
                "description": "Probes all configured flash-server services (Immich, Jellyfin, qBittorrent, n8n, Postgres, AIU, etc.) and returns real-time status and latencies.",
                "responses": {
                    "200": {
                        "description": "JSON array of service statuses."
                    }
                }
            }
        },
        "/api/monitoring/diagnostics": {
            "get": {
                "tags": ["Monitoring"],
                "summary": "Diagnostic Test Suite Audit",
                "description": "Runs comprehensive health checks across disks, RAM, thermals, services, and cron jobs, returning an overall audit result.",
                "responses": {
                    "200": {
                        "description": "JSON diagnostic audit report."
                    }
                }
            }
        }
    }
}

SWAGGER_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Flash Server API</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
  <link rel="icon" type="image/png" href="/static/flash.png" />
  <link rel="shortcut icon" type="image/png" href="/static/flash.png" />
  <style>
    body {
      margin: 0;
      padding: 0;
      background: #fafafa;
    }
    .topbar {
      display: none !important;
    }
    .swagger-ui .info {
      position: relative !important;
      min-height: 185px !important;
      padding-right: 280px !important;
    }
    .swagger-ui .info .title {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      color: #1a73e8;
    }
    #flash-header-banner {
      position: absolute !important;
      top: 0 !important;
      right: 0 !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      border-radius: 12px !important;
      overflow: hidden !important;
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.14) !important;
      border: 2px solid #eaeaea !important;
      background: #ffffff !important;
      transition: transform 0.25s ease, box-shadow 0.25s ease !important;
    }
    #flash-header-banner:hover {
      transform: scale(1.03) !important;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.22) !important;
    }
    #flash-header-banner img {
      height: 170px !important;
      width: auto !important;
      display: block !important;
      border-radius: 10px !important;
      object-fit: contain !important;
    }
    @media (max-width: 900px) {
      .swagger-ui .info {
        padding-right: 0 !important;
        min-height: auto !important;
      }
      #flash-header-banner {
        position: static !important;
        margin: 20px auto 10px auto !important;
        width: fit-content !important;
      }
      #flash-header-banner img {
        height: 130px !important;
      }
    }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js"></script>
  <script>
    function injectFlashBanner() {
      const info = document.querySelector('.swagger-ui .info');
      if (info && !document.getElementById('flash-header-banner')) {
        const banner = document.createElement('div');
        banner.id = 'flash-header-banner';
        banner.title = 'Flash Server';
        banner.innerHTML = '<img src="/static/flash.gif" alt="Flash Animation" />';
        info.appendChild(banner);

        const linkContainer = document.createElement('div');
        linkContainer.id = 'swagger-monitor-link';
        linkContainer.style = 'margin-top: 14px;';
        linkContainer.innerHTML = '<a href="/monitoring" style="display:inline-flex; align-items:center; gap:6px; background:#1a73e8; color:#ffffff; font-weight:600; font-size:13px; padding:7px 14px; border-radius:8px; text-decoration:none; box-shadow:0 1px 3px rgba(0,0,0,0.12); transition:background 0.2s;">🖥️ Open System Telemetry & Monitor (/monitoring) ↗</a>';
        info.appendChild(linkContainer);
      }
    }

    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: '#swagger-ui',
        deepLinking: true,
        persistAuthorization: true,
        validatorUrl: null,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        layout: "StandaloneLayout",
        onComplete: function() {
          injectFlashBanner();
        }
      });

      // Observe DOM to ensure banner is added as soon as Swagger UI info component mounts
      const swaggerContainer = document.getElementById('swagger-ui');
      if (swaggerContainer) {
        const observer = new MutationObserver(() => {
          injectFlashBanner();
        });
        observer.observe(swaggerContainer, { childList: true, subtree: true });
      }

      // Fallback timer check for first few seconds
      const timer = setInterval(injectFlashBanner, 150);
      setTimeout(() => clearInterval(timer), 3500);
    };
  </script>
</body>
</html>
"""


@swagger_bp.route("/")
@swagger_bp.route("/docs")
def swagger_ui():
    return render_template_string(SWAGGER_HTML_TEMPLATE)


@swagger_bp.route("/openapi.json")
@swagger_bp.route("/swagger.json")
def openapi_spec():
    return jsonify(OPENAPI_SPEC)


@swagger_bp.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'flash.png', mimetype='image/png')
