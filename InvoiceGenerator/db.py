import json
import os
import sqlite3
from datetime import datetime
from .config import DB_PATH, APP_TIMEZONE, DEFAULT_SENDER, DEFAULT_DUE_DAYS


def get_connection():
    """Returns a SQLite connection with Row factory and WAL mode."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initializes SQLite schema for sender profiles, clients, presets, and invoices."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")

        # 1. Sender Profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sender_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                website TEXT,
                payment_instructions TEXT,
                default_notes TEXT,
                is_default INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # 2. Clients
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # 3. Client Presets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                preset_name TEXT NOT NULL,
                default_due_days INTEGER DEFAULT 14,
                items_json TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # 4. Invoices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                sender_id INTEGER REFERENCES sender_profiles(id) ON DELETE SET NULL,
                sender_name_snapshot TEXT NOT NULL,
                sender_info_snapshot TEXT,
                client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                client_name_snapshot TEXT NOT NULL,
                client_info_snapshot TEXT,
                issue_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                subtotal REAL NOT NULL DEFAULT 0.0,
                discount_amount REAL NOT NULL DEFAULT 0.0,
                tax_rate REAL NOT NULL DEFAULT 0.0,
                total_amount REAL NOT NULL DEFAULT 0.0,
                payment_instructions TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # 5. Invoice Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 1.0,
                unit_price REAL NOT NULL DEFAULT 0.0,
                amount REAL NOT NULL DEFAULT 0.0,
                sort_order INTEGER DEFAULT 0
            );
        """)

        # Indexes for fast querying & filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_client ON invoices(client_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_sender ON invoices(sender_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_issue ON invoices(issue_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(due_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_client_presets_client ON client_presets(client_id);")

        conn.commit()

        # Seed default sender if table is empty
        cursor.execute("SELECT COUNT(*) AS cnt FROM sender_profiles;")
        if cursor.fetchone()["cnt"] == 0:
            now_iso = datetime.now(APP_TIMEZONE).isoformat()
            cursor.execute("""
                INSERT INTO sender_profiles (
                    name, email, phone, address, website,
                    payment_instructions, default_notes, is_default,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                DEFAULT_SENDER.get("name", "Stephen Giang"),
                DEFAULT_SENDER.get("email", "stepheng753@gmail.com"),
                DEFAULT_SENDER.get("phone", ""),
                DEFAULT_SENDER.get("address", ""),
                DEFAULT_SENDER.get("website", ""),
                DEFAULT_SENDER.get("payment_instructions", ""),
                DEFAULT_SENDER.get("default_notes", ""),
                1,
                now_iso,
                now_iso
            ))
            conn.commit()


# ---------------------------------------------------------------------------
# SENDER PROFILES CRUD
# ---------------------------------------------------------------------------

def get_senders():
    """Returns all sender profiles ordered with default first, then by name."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sender_profiles
            ORDER BY is_default DESC, name ASC;
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_sender_by_id(sender_id):
    """Returns a single sender profile by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sender_profiles WHERE id = ?;", (sender_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_sender(name, email="", phone="", address="", website="",
               payment_instructions="", default_notes="", is_default=0):
    """Adds a new sender profile."""
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        if is_default:
            cursor.execute("UPDATE sender_profiles SET is_default = 0;")
        cursor.execute("""
            INSERT INTO sender_profiles (
                name, email, phone, address, website,
                payment_instructions, default_notes, is_default,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            name.strip(),
            email.strip(),
            phone.strip(),
            address.strip(),
            website.strip(),
            payment_instructions.strip(),
            default_notes.strip(),
            1 if is_default else 0,
            now_iso,
            now_iso
        ))
        conn.commit()
        return cursor.lastrowid


def update_sender(sender_id, name, email="", phone="", address="", website="",
                  payment_instructions="", default_notes="", is_default=0):
    """Updates an existing sender profile."""
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        if is_default:
            cursor.execute("UPDATE sender_profiles SET is_default = 0 WHERE id != ?;", (sender_id,))
        cursor.execute("""
            UPDATE sender_profiles SET
                name = ?,
                email = ?,
                phone = ?,
                address = ?,
                website = ?,
                payment_instructions = ?,
                default_notes = ?,
                is_default = ?,
                updated_at = ?
            WHERE id = ?;
        """, (
            name.strip(),
            email.strip(),
            phone.strip(),
            address.strip(),
            website.strip(),
            payment_instructions.strip(),
            default_notes.strip(),
            1 if is_default else 0,
            now_iso,
            sender_id
        ))
        conn.commit()
        return cursor.rowcount > 0


def set_default_sender(sender_id):
    """Sets the designated sender profile as default."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE sender_profiles SET is_default = 0;")
        cursor.execute("UPDATE sender_profiles SET is_default = 1 WHERE id = ?;", (sender_id,))
        conn.commit()
        return cursor.rowcount > 0


def delete_sender(sender_id):
    """Deletes a sender profile."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sender_profiles WHERE id = ?;", (sender_id,))
        conn.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# CLIENTS CRUD
# ---------------------------------------------------------------------------

def get_clients():
    """Returns all clients ordered by name."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients ORDER BY name COLLATE NOCASE ASC;")
        return [dict(row) for row in cursor.fetchall()]


def get_client_by_id(client_id):
    """Returns a client by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?;", (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_client(name, email="", phone="", address="", notes=""):
    """Adds a new client."""
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clients (name, email, phone, address, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            name.strip(),
            email.strip(),
            phone.strip(),
            address.strip(),
            notes.strip(),
            now_iso,
            now_iso
        ))
        conn.commit()
        return cursor.lastrowid


def update_client(client_id, name, email="", phone="", address="", notes=""):
    """Updates a client's details."""
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clients SET
                name = ?,
                email = ?,
                phone = ?,
                address = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?;
        """, (
            name.strip(),
            email.strip(),
            phone.strip(),
            address.strip(),
            notes.strip(),
            now_iso,
            client_id
        ))
        conn.commit()
        return cursor.rowcount > 0


def delete_client(client_id):
    """Deletes a client and cascades to their presets."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clients WHERE id = ?;", (client_id,))
        conn.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# CLIENT PRESETS CRUD
# ---------------------------------------------------------------------------

def get_presets_by_client(client_id):
    """Returns presets for a given client."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM client_presets
            WHERE client_id = ?
            ORDER BY preset_name COLLATE NOCASE ASC;
        """, (client_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["items"] = json.loads(d.get("items_json") or "[]")
            except Exception:
                d["items"] = []
            result.append(d)
        return result


def add_preset(client_id, preset_name, default_due_days=14, items=None, notes=""):
    """Saves a recurring line-item preset for a client."""
    if items is None:
        items = []
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    items_json = json.dumps(items)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO client_presets (
                client_id, preset_name, default_due_days, items_json, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?);
        """, (
            client_id,
            preset_name.strip(),
            int(default_due_days),
            items_json,
            notes.strip(),
            now_iso
        ))
        conn.commit()
        return cursor.lastrowid


def delete_preset(preset_id):
    """Deletes a preset."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM client_presets WHERE id = ?;", (preset_id,))
        conn.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# INVOICE NUMBER GENERATION
# ---------------------------------------------------------------------------

def generate_next_invoice_number():
    """Generates the next sequential invoice number for current year: INV-YYYY-001."""
    now = datetime.now(APP_TIMEZONE)
    year = now.year
    prefix = f"INV-{year}-"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT invoice_number FROM invoices
            WHERE invoice_number LIKE ?
            ORDER BY id DESC;
        """, (f"{prefix}%",))
        rows = cursor.fetchall()

        max_seq = 0
        for r in rows:
            num_str = r["invoice_number"]
            try:
                parts = num_str.split("-")
                seq = int(parts[-1])
                if seq > max_seq:
                    max_seq = seq
            except (ValueError, IndexError):
                continue

        return f"{prefix}{max_seq + 1:03d}"


# ---------------------------------------------------------------------------
# INVOICES & ITEMS CRUD
# ---------------------------------------------------------------------------

def get_invoices(status=None, client_id=None, sender_id=None, search=None,
                 start_date=None, end_date=None, sort_by="issue_date", sort_order="desc"):
    """
    Returns invoices matching filters.
    Updates overdue status on the fly for sent/draft invoices whose due_date < today.
    """
    today_str = datetime.now(APP_TIMEZONE).strftime("%Y-%m-%d")

    # Auto-flag overdue invoices (sent or draft invoices past due date)
    with get_connection() as conn:
        conn.execute("""
            UPDATE invoices
            SET status = 'overdue', updated_at = ?
            WHERE status IN ('draft', 'sent') AND due_date < ?;
        """, (datetime.now(APP_TIMEZONE).isoformat(), today_str))
        conn.commit()

    query = "SELECT * FROM invoices WHERE 1=1"
    params = []

    if status and status.lower() != "all":
        query += " AND status = ?"
        params.append(status.lower())

    if client_id:
        query += " AND client_id = ?"
        params.append(int(client_id))

    if sender_id:
        query += " AND sender_id = ?"
        params.append(int(sender_id))

    if start_date:
        query += " AND issue_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND issue_date <= ?"
        params.append(end_date)

    if search:
        search_term = f"%{search.strip()}%"
        query += """ AND (
            invoice_number LIKE ? OR
            client_name_snapshot LIKE ? OR
            sender_name_snapshot LIKE ? OR
            notes LIKE ?
        )"""
        params.extend([search_term, search_term, search_term, search_term])

    # Sorting
    allowed_sort_fields = {
        "issue_date": "issue_date",
        "due_date": "due_date",
        "total_amount": "total_amount",
        "invoice_number": "invoice_number",
        "status": "status",
        "created_at": "created_at"
    }
    col = allowed_sort_fields.get(sort_by, "issue_date")
    direction = "ASC" if str(sort_order).lower() == "asc" else "DESC"
    query += f" ORDER BY {col} {direction}, id {direction};"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            result.append(item)
        return result


def get_invoice_by_id(invoice_id):
    """
    Returns full invoice details including snapshots and list of line items.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id = ?;", (invoice_id,))
        row = cursor.fetchone()
        if not row:
            return None

        invoice = dict(row)

        # Parse JSON snapshots if present
        try:
            invoice["sender_info"] = json.loads(invoice.get("sender_info_snapshot") or "{}")
        except Exception:
            invoice["sender_info"] = {}

        try:
            invoice["client_info"] = json.loads(invoice.get("client_info_snapshot") or "{}")
        except Exception:
            invoice["client_info"] = {}

        # Fetch items
        cursor.execute("""
            SELECT * FROM invoice_items
            WHERE invoice_id = ?
            ORDER BY sort_order ASC, id ASC;
        """, (invoice_id,))
        invoice["items"] = [dict(r) for r in cursor.fetchall()]

        return invoice


def create_invoice(data):
    """
    Creates an invoice along with its line items and historical snapshots.
    `data` expects:
      - invoice_number (optional, generated if omitted)
      - sender_id (optional, takes default sender if omitted)
      - client_id (optional)
      - client_name (required if client_id not present or client snapshot)
      - client_email, client_phone, client_address
      - issue_date, due_date
      - status ('draft', 'sent', 'paid', 'overdue', 'void')
      - discount_amount, tax_rate
      - payment_instructions, notes
      - items: list of {description, quantity, unit_price}
    """
    now = datetime.now(APP_TIMEZONE)
    now_iso = now.isoformat()

    invoice_number = data.get("invoice_number")
    if not invoice_number or not invoice_number.strip():
        invoice_number = generate_next_invoice_number()
    else:
        invoice_number = invoice_number.strip()

    # Resolve sender
    sender_id = data.get("sender_id")
    sender_row = None
    if sender_id:
        sender_row = get_sender_by_id(sender_id)
    if not sender_row:
        # Fall back to default sender
        senders = get_senders()
        if senders:
            sender_row = senders[0]
            sender_id = sender_row["id"]
        else:
            sender_row = DEFAULT_SENDER
            sender_id = None

    sender_name_snapshot = sender_row.get("name", "Stephen Giang")
    sender_info_snapshot = json.dumps({
        "name": sender_row.get("name", ""),
        "email": sender_row.get("email", ""),
        "phone": sender_row.get("phone", ""),
        "address": sender_row.get("address", ""),
        "website": sender_row.get("website", ""),
        "payment_instructions": sender_row.get("payment_instructions", "")
    })

    # Resolve client
    client_id = data.get("client_id")
    client_row = None
    if client_id:
        client_row = get_client_by_id(client_id)

    client_name = data.get("client_name") or (client_row.get("name") if client_row else "") or "Valued Client"
    client_email = data.get("client_email") or (client_row.get("email") if client_row else "")
    client_phone = data.get("client_phone") or (client_row.get("phone") if client_row else "")
    client_address = data.get("client_address") or (client_row.get("address") if client_row else "")

    client_info_snapshot = json.dumps({
        "name": client_name,
        "email": client_email,
        "phone": client_phone,
        "address": client_address
    })

    issue_date = data.get("issue_date") or now.strftime("%Y-%m-%d")
    due_date = data.get("due_date")
    if not due_date:
        from datetime import timedelta
        due_date = (now + timedelta(days=DEFAULT_DUE_DAYS)).strftime("%Y-%m-%d")

    status = (data.get("status") or "draft").lower()

    # Calculate item amounts and totals
    raw_items = data.get("items") or []
    subtotal = 0.0
    processed_items = []
    for idx, it in enumerate(raw_items):
        desc = (it.get("description") or "").strip()
        if not desc:
            continue
        try:
            qty = float(it.get("quantity", 1.0))
        except (ValueError, TypeError):
            qty = 1.0
        try:
            unit_price = float(it.get("unit_price", 0.0))
        except (ValueError, TypeError):
            unit_price = 0.0

        line_amount = round(qty * unit_price, 2)
        subtotal += line_amount
        processed_items.append({
            "description": desc,
            "quantity": qty,
            "unit_price": unit_price,
            "amount": line_amount,
            "sort_order": idx
        })

    subtotal = round(subtotal, 2)
    try:
        discount_amount = max(0.0, float(data.get("discount_amount", 0.0)))
    except (ValueError, TypeError):
        discount_amount = 0.0

    try:
        tax_rate = max(0.0, float(data.get("tax_rate", 0.0)))
    except (ValueError, TypeError):
        tax_rate = 0.0

    discounted_subtotal = max(0.0, subtotal - discount_amount)
    tax_amount = round(discounted_subtotal * (tax_rate / 100.0), 2)
    total_amount = round(discounted_subtotal + tax_amount, 2)

    payment_instructions = data.get("payment_instructions") or sender_row.get("payment_instructions", "")
    notes = data.get("notes") or sender_row.get("default_notes", "")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO invoices (
                invoice_number, sender_id, sender_name_snapshot, sender_info_snapshot,
                client_id, client_name_snapshot, client_info_snapshot,
                issue_date, due_date, status,
                subtotal, discount_amount, tax_rate, total_amount,
                payment_instructions, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            invoice_number,
            sender_id,
            sender_name_snapshot,
            sender_info_snapshot,
            client_id,
            client_name,
            client_info_snapshot,
            issue_date,
            due_date,
            status,
            subtotal,
            discount_amount,
            tax_rate,
            total_amount,
            payment_instructions,
            notes,
            now_iso,
            now_iso
        ))
        invoice_id = cursor.lastrowid

        for it in processed_items:
            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_id, description, quantity, unit_price, amount, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, (
                invoice_id,
                it["description"],
                it["quantity"],
                it["unit_price"],
                it["amount"],
                it["sort_order"]
            ))

        conn.commit()
        return invoice_id


def update_invoice(invoice_id, data):
    """
    Updates an invoice and its line items.
    """
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    existing = get_invoice_by_id(invoice_id)
    if not existing:
        return False

    sender_id = data.get("sender_id", existing.get("sender_id"))
    sender_row = get_sender_by_id(sender_id) if sender_id else None
    sender_name_snapshot = sender_row["name"] if sender_row else existing["sender_name_snapshot"]
    sender_info_snapshot = json.dumps({
        "name": sender_row.get("name", ""),
        "email": sender_row.get("email", ""),
        "phone": sender_row.get("phone", ""),
        "address": sender_row.get("address", ""),
        "website": sender_row.get("website", ""),
        "payment_instructions": sender_row.get("payment_instructions", "")
    }) if sender_row else existing.get("sender_info_snapshot")

    client_id = data.get("client_id", existing.get("client_id"))
    client_row = get_client_by_id(client_id) if client_id else None
    client_name = data.get("client_name") or (client_row["name"] if client_row else existing["client_name_snapshot"])
    client_info_snapshot = json.dumps({
        "name": client_name,
        "email": data.get("client_email") or (client_row["email"] if client_row else ""),
        "phone": data.get("client_phone") or (client_row["phone"] if client_row else ""),
        "address": data.get("client_address") or (client_row["address"] if client_row else "")
    })

    issue_date = data.get("issue_date", existing["issue_date"])
    due_date = data.get("due_date", existing["due_date"])
    status = (data.get("status", existing["status"])).lower()

    # Recalculate line items
    raw_items = data.get("items")
    if raw_items is None:
        raw_items = existing.get("items", [])

    subtotal = 0.0
    processed_items = []
    for idx, it in enumerate(raw_items):
        desc = (it.get("description") or "").strip()
        if not desc:
            continue
        try:
            qty = float(it.get("quantity", 1.0))
        except (ValueError, TypeError):
            qty = 1.0
        try:
            unit_price = float(it.get("unit_price", 0.0))
        except (ValueError, TypeError):
            unit_price = 0.0
        line_amount = round(qty * unit_price, 2)
        subtotal += line_amount
        processed_items.append({
            "description": desc,
            "quantity": qty,
            "unit_price": unit_price,
            "amount": line_amount,
            "sort_order": idx
        })

    subtotal = round(subtotal, 2)
    try:
        discount_amount = max(0.0, float(data.get("discount_amount", existing["discount_amount"])))
    except (ValueError, TypeError):
        discount_amount = existing["discount_amount"]

    try:
        tax_rate = max(0.0, float(data.get("tax_rate", existing["tax_rate"])))
    except (ValueError, TypeError):
        tax_rate = existing["tax_rate"]

    discounted_subtotal = max(0.0, subtotal - discount_amount)
    tax_amount = round(discounted_subtotal * (tax_rate / 100.0), 2)
    total_amount = round(discounted_subtotal + tax_amount, 2)

    payment_instructions = data.get("payment_instructions", existing["payment_instructions"])
    notes = data.get("notes", existing["notes"])

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE invoices SET
                sender_id = ?,
                sender_name_snapshot = ?,
                sender_info_snapshot = ?,
                client_id = ?,
                client_name_snapshot = ?,
                client_info_snapshot = ?,
                issue_date = ?,
                due_date = ?,
                status = ?,
                subtotal = ?,
                discount_amount = ?,
                tax_rate = ?,
                total_amount = ?,
                payment_instructions = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?;
        """, (
            sender_id,
            sender_name_snapshot,
            sender_info_snapshot,
            client_id,
            client_name,
            client_info_snapshot,
            issue_date,
            due_date,
            status,
            subtotal,
            discount_amount,
            tax_rate,
            total_amount,
            payment_instructions,
            notes,
            now_iso,
            invoice_id
        ))

        # Replace items
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?;", (invoice_id,))
        for it in processed_items:
            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_id, description, quantity, unit_price, amount, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, (
                invoice_id,
                it["description"],
                it["quantity"],
                it["unit_price"],
                it["amount"],
                it["sort_order"]
            ))

        conn.commit()
        return True


def update_invoice_status(invoice_id, status):
    """Updates invoice status (e.g. 'draft', 'sent', 'paid', 'overdue', 'void')."""
    valid_statuses = {"draft", "sent", "paid", "overdue", "void"}
    status = status.lower().strip()
    if status not in valid_statuses:
        return False

    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE invoices SET status = ?, updated_at = ?
            WHERE id = ?;
        """, (status, now_iso, invoice_id))
        conn.commit()
        return cursor.rowcount > 0


def duplicate_invoice(invoice_id):
    """
    Duplicates an invoice into a new draft with a new invoice number and today's date.
    """
    orig = get_invoice_by_id(invoice_id)
    if not orig:
        return None

    now = datetime.now(APP_TIMEZONE)
    from datetime import timedelta
    new_due = (now + timedelta(days=DEFAULT_DUE_DAYS)).strftime("%Y-%m-%d")

    data = {
        "invoice_number": generate_next_invoice_number(),
        "sender_id": orig.get("sender_id"),
        "client_id": orig.get("client_id"),
        "client_name": orig.get("client_name_snapshot"),
        "client_email": orig.get("client_info", {}).get("email", ""),
        "client_phone": orig.get("client_info", {}).get("phone", ""),
        "client_address": orig.get("client_info", {}).get("address", ""),
        "issue_date": now.strftime("%Y-%m-%d"),
        "due_date": new_due,
        "status": "draft",
        "discount_amount": orig.get("discount_amount", 0.0),
        "tax_rate": orig.get("tax_rate", 0.0),
        "payment_instructions": orig.get("payment_instructions", ""),
        "notes": orig.get("notes", ""),
        "items": [
            {
                "description": it["description"],
                "quantity": it["quantity"],
                "unit_price": it["unit_price"]
            }
            for it in orig.get("items", [])
        ]
    }

    return create_invoice(data)


def delete_invoice(invoice_id):
    """Hard-deletes an invoice and its items (via CASCADE)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE id = ?;", (invoice_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_invoices_summary():
    """
    Computes dashboard summary statistics:
    - Total Invoiced (non-void)
    - Outstanding (sent + overdue)
    - Paid (paid)
    - Total Clients (count of distinct client records)
    - Total Drafts
    - Total Void
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Invoiced amounts by status
        cursor.execute("""
            SELECT status, SUM(total_amount) AS sum_total, COUNT(*) AS count
            FROM invoices
            GROUP BY status;
        """)
        rows = cursor.fetchall()
        status_map = {r["status"]: {"total": r["sum_total"] or 0.0, "count": r["count"]} for r in rows}

        total_invoiced = sum(
            d["total"] for s, d in status_map.items() if s != "void"
        )
        outstanding = (
            status_map.get("sent", {}).get("total", 0.0) +
            status_map.get("overdue", {}).get("total", 0.0)
        )
        paid = status_map.get("paid", {}).get("total", 0.0)
        drafts_count = status_map.get("draft", {}).get("count", 0)
        void_count = status_map.get("void", {}).get("count", 0)

        # Count total clients
        cursor.execute("SELECT COUNT(*) AS cnt FROM clients;")
        total_clients = cursor.fetchone()["cnt"]

        # Count total invoices
        cursor.execute("SELECT COUNT(*) AS cnt FROM invoices;")
        total_invoices = cursor.fetchone()["cnt"]

        return {
            "total_invoiced": round(total_invoiced, 2),
            "outstanding": round(outstanding, 2),
            "paid": round(paid, 2),
            "total_clients": total_clients,
            "total_invoices": total_invoices,
            "drafts_count": drafts_count,
            "void_count": void_count
        }
