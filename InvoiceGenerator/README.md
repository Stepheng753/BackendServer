# Invoice Generator Module

The `InvoiceGenerator` package provides pure-Python vector PDF invoice generation, multi-company sender profiles, saved client directories, reusable service presets, and full lifecycle tracking with real-time financial metrics.

Accessible at `http://localhost:5000/invoices` (or prefixed at `/InvoiceGenerator/invoices`).

---

## 1. Features & Architecture

* **In-Memory Vector PDF Rendering**: Built with ReportLab Platypus. Generates professional 300 DPI vector PDFs streamed directly via `io.BytesIO`. Zero PDF files are stored on disk, preserving disk space and user privacy.
* **Smart PDF Title & Phone Normalization**: Automatically sets the internal PDF `/Title` metadata to `Invoice# - {Client Name}` (e.g. `INV-2026-001 - Acme Corp`) and normalizes all sender and client phone numbers to `+1 (XXX) XXX-XXXX`.
* **Selective Status Display**: The PDF header only displays the invoice status if it is marked **`paid`** (in bold emerald green). All other statuses (`draft`, `sent`, `overdue`, `void`) remain clean on customer-facing PDFs.
* **Persistent SQLite WAL Storage**: All entities (senders, clients, presets, invoices, line items) are stored in `config/invoices.db` running in SQLite Write-Ahead Logging (`WAL`) mode with foreign key integrity.
* **Client Presets**: Save commonly billed services, due date offsets, discount amounts, tax rates, payment instructions, and terms to any client, and load them into the invoice builder with a single click.
* **Live Dynamic History & Filtered Metrics**: Filter invoices by status, sender, client, date range, or search keyword. Summary cards (Total Invoiced, Outstanding Balance, Total Collected, Total Clients) update immediately to reflect the active filters.
* **Full-Page Print Preview**: Dedicated preview route (`/invoices/<id>/preview`) providing a print-ready HTML sheet, native browser print (`window.print()`), and direct vector PDF download.

---

## 2. Endpoints Reference

All endpoints require HTTP Basic Authentication.

### Web Dashboard & Previews
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/invoices` | `GET` | Main invoice application dashboard (Builder, History, Senders & Clients). |
| `/InvoiceGenerator/invoices` | `GET` | Prefixed alias for the main dashboard. |
| `/invoices/<id>/preview` | `GET` | Print-ready HTML preview page with print & PDF download toolbars. |

### REST API Endpoints
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/invoices/summary` | `GET` | Aggregated metrics (`total_invoiced`, `outstanding`, `paid`, `total_clients`) dynamically filtered by query params (`status`, `client_id`, `sender_id`, `search`, `start_date`, `end_date`). |
| `GET /api/invoices/next-number` | `GET` | Computes the next sequential invoice number for the current year (`INV-YYYY-001`). |
| `GET /api/invoices` | `GET` | Lists invoices matching active filters with pagination support. |
| `POST /api/invoices` | `POST` | Creates a new invoice with itemized line items, calculating subtotal, discount, tax, and total. |
| `GET /api/invoices/<id>` | `GET` | Returns full invoice details including snapshots and line items. |
| `PUT /api/invoices/<id>` | `PUT` | Updates an existing draft or active invoice. |
| `PATCH /api/invoices/<id>/status` | `PATCH` | Updates invoice status (`draft`, `sent`, `paid`, `overdue`, `void`). |
| `POST /api/invoices/<id>/duplicate`| `POST` | Clones an invoice with a newly generated invoice number in `draft` status. |
| `DELETE /api/invoices/<id>` | `DELETE`| Permanently deletes an invoice and cascades to line items. |
| `GET /api/invoices/<id>/pdf` | `GET` | Streams the vector PDF directly to the browser/download with `Content-Disposition: attachment`. |
| `GET /api/invoices/senders` | `GET` | Lists all sender profiles. |
| `POST /api/invoices/senders` | `POST` | Creates a sender profile. |
| `PUT /api/invoices/senders/<id>` | `PUT` | Updates a sender profile. |
| `POST /api/invoices/senders/<id>/default` | `POST` | Sets a sender profile as the default. |
| `DELETE /api/invoices/senders/<id>` | `DELETE`| Deletes a non-default sender profile. |
| `GET /api/invoices/clients` | `GET` | Lists all clients. |
| `POST /api/invoices/clients` | `POST` | Creates a new client profile. |
| `PUT /api/invoices/clients/<id>` | `PUT` | Updates an existing client profile. |
| `DELETE /api/invoices/clients/<id>` | `DELETE`| Deletes a client profile. |
| `GET /api/invoices/clients/<id>/presets` | `GET` | Retrieves saved service presets for a specific client. |
| `POST /api/invoices/presets` | `POST` | Creates a preset saving line items, invoice details, and remittance/terms. |
| `DELETE /api/invoices/presets/<id>` | `DELETE`| Deletes a saved preset. |

---

## 3. Database Schema

The SQLite database (`config/invoices.db`) comprises 5 relational tables:

```
  ┌───────────────────────┐           ┌───────────────────────┐
  │    sender_profiles    │           │        clients        │
  ├───────────────────────┤           ├───────────────────────┤
  │ id (PK)               │           │ id (PK)               │
  │ name, address, email  │           │ name, address, email  │
  │ phone, website        │           │ phone                 │
  │ is_default (INTEGER)  │           └───────────┬───────────┘
  └───────────────────────┘                       │ 1:N
                                                  ▼
                                      ┌───────────────────────┐
                                      │    client_presets     │
                                      ├───────────────────────┤
                                      │ id (PK)               │
                                      │ client_id (FK)        │
                                      │ preset_name           │
                                      │ default_due_days      │
                                      │ discount_amount       │
                                      │ tax_rate              │
                                      │ payment_instructions  │
                                      │ notes                 │
                                      │ items_json            │
                                      └───────────────────────┘

  ┌───────────────────────────────────────────────────────────┐
  │                         invoices                          │
  ├───────────────────────────────────────────────────────────┤
  │ id (PK)                                                   │
  │ invoice_number (UNIQUE: INV-YYYY-XXX)                     │
  │ sender_id (FK), client_id (FK)                            │
  │ sender_name_snapshot, sender_info_snapshot (JSON)         │
  │ client_name_snapshot, client_info_snapshot (JSON)         │
  │ issue_date, due_date                                      │
  │ status ('draft' | 'sent' | 'paid' | 'overdue' | 'void')   │
  │ subtotal, discount_amount, tax_rate, tax_amount           │
  │ total_amount, payment_instructions, notes                 │
  └─────────────────────────────┬─────────────────────────────┘
                                │ 1:N (CASCADE)
                                ▼
  ┌───────────────────────────────────────────────────────────┐
  │                       invoice_items                       │
  ├───────────────────────────────────────────────────────────┤
  │ id (PK)                                                   │
  │ invoice_id (FK -> invoices.id ON DELETE CASCADE)          │
  │ description, quantity, unit_price, amount, sort_order     │
  └───────────────────────────────────────────────────────────┘
```

---

## 4. Package Structure

```
InvoiceGenerator/
├── __init__.py                # Blueprint export (invoice_bp)
├── db.py                      # SQLite WAL database operations & migrations
├── pdf.py                     # ReportLab Platypus vector PDF generator
├── routes.py                  # Web & REST API endpoints
├── templates/
│   ├── invoices.html          # Main responsive 3-tab HTML dashboard
│   └── invoice_print.html     # Print-ready HTML preview page
├── tests/
│   ├── __init__.py            # Test package marker
│   ├── test_invoices.py       # Unit tests for CRUD, DB, and vector PDF bytes
│   └── test_integration.py    # Flask route integration & OpenAPI validation
└── README.md                  # Module technical reference
```

---

## 5. Automated Testing

Run all unit and integration tests for the Invoice Generator:

```bash
# From repository root
.venv/bin/python -m unittest discover -s InvoiceGenerator/tests -p "test_*.py"
```
