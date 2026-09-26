# Swagger & OpenAPI Module

The `swagger` package provides interactive OpenAPI 3.0 API documentation, specification generation, and the Swagger UI console for Stephen Giang's Flash Server.

Accessible at `http://localhost:5000/` or `http://localhost:5000/docs`.

---

## 1. Features & Architecture

* **Interactive Swagger UI**: Custom-branded Swagger UI interface rendered at root `/` and `/docs`, matching `/css/shared.css` with dark mode support.
* **Unified OpenAPI 3.0 Schema**: Dynamically exposes `/openapi.json` containing complete endpoints, request bodies, query parameters, responses, and schemas across all server modules:
  * **Monitoring**: Hardware telemetry, processes, storage, services, and diagnostic tests.
  * **Tutoring Calculator**: Billing calculation, Google Sheets, calendar hours, and Twilio SMS dispatches.
  * **To-Do Board**: Task management, Eisenhower categories, reordering, and archival.
  * **Invoice Generator**: Vector PDF generation, client presets, multi-sender profiles, and history tracking.
* **Security Integration**: Documents the HTTP Basic Authentication security requirement across all endpoints with one-click authorization testing directly from the Swagger UI console.
* **Top Navigation Bar**: Seamless navigation between all web applications (`System Monitor`, `Tutoring Calculator`, `To Do`, and `Invoices`).

---

## 2. Endpoints Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Main landing page rendering Swagger UI. |
| `/docs` | `GET` | Direct alias for the Swagger UI documentation console. |
| `/openapi.json` | `GET` | Machine-readable OpenAPI 3.0 specification JSON schema. |

---

## 3. Package Structure

```
swagger/
├── swagger.py                 # OpenAPI 3.0 specification and Swagger UI HTML renderer
└── README.md                  # Module technical reference
```
