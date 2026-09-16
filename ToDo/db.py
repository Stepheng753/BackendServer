import sqlite3
import os
from datetime import datetime, timedelta
import pytz
from .config import DB_PATH, APP_TIMEZONE


def get_connection():
    """Returns a SQLite connection with Row factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the tasks table if it does not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                text TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                completed_at TEXT,
                status TEXT DEFAULT 'active',
                display_order INTEGER DEFAULT 0,
                archived_at TEXT,
                created_at TEXT NOT NULL
            );
        """)
        # Indexes for query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_order ON tasks(category, display_order);")
        conn.commit()


def get_last_monday_2am(now_dt=None):
    """
    Computes the most recent Monday at 02:00:00 AM in the application timezone (America/Los_Angeles).
    Any task completed before this cutoff belongs to a previous week and should be archived.
    """
    if now_dt is None:
        now_dt = datetime.now(APP_TIMEZONE)
    elif now_dt.tzinfo is None:
        now_dt = APP_TIMEZONE.localize(now_dt)
    else:
        now_dt = now_dt.astimezone(APP_TIMEZONE)

    days_since_monday = now_dt.weekday()  # Monday is 0, Sunday is 6
    candidate = now_dt.replace(hour=2, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
    if now_dt < candidate:
        # It is Monday before 02:00:00 AM, cutoff was the previous Monday
        candidate -= timedelta(days=7)
    return candidate


def auto_archive_expired_tasks(now_dt=None):
    """
    Finds active tasks with completed=1 where completed_at is older than the latest Monday 2am cutoff,
    and updates their status to 'archived'.
    """
    cutoff = get_last_monday_2am(now_dt)
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    archived_count = 0

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, completed_at FROM tasks
            WHERE status = 'active' AND completed = 1 AND completed_at IS NOT NULL
        """)
        rows = cursor.fetchall()

        to_archive_ids = []
        for row in rows:
            try:
                task_completed_dt = datetime.fromisoformat(row["completed_at"])
                if task_completed_dt.tzinfo is None:
                    task_completed_dt = APP_TIMEZONE.localize(task_completed_dt)
                else:
                    task_completed_dt = task_completed_dt.astimezone(APP_TIMEZONE)

                if task_completed_dt < cutoff:
                    to_archive_ids.append(row["id"])
            except Exception as e:
                print(f"[ToDo] Error parsing completed_at for task {row['id']}: {e}")

        if to_archive_ids:
            cursor.executemany(
                "UPDATE tasks SET status = 'archived', archived_at = ? WHERE id = ?",
                [(now_iso, tid) for tid in to_archive_ids]
            )
            conn.commit()
            archived_count = len(to_archive_ids)

    return archived_count


def task_row_to_dict(row):
    """Converts a sqlite3.Row to a clean Python dictionary."""
    return {
        "id": row["id"],
        "category": row["category"],
        "text": row["text"],
        "completed": bool(row["completed"]),
        "completed_at": row["completed_at"],
        "status": row["status"],
        "display_order": row["display_order"],
        "archived_at": row["archived_at"],
        "created_at": row["created_at"]
    }


def get_tasks(status="active", category=None):
    """
    Retrieves tasks by status ('active' or 'archived'), optionally filtered by category.
    Always runs auto_archive_expired_tasks() first to ensure consistency.
    """
    auto_archive_expired_tasks()

    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM tasks WHERE status = ?"
        params = [status]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY display_order ASC, id ASC"
        cursor.execute(query, params)
        return [task_row_to_dict(row) for row in cursor.fetchall()]


def get_task_by_id(task_id):
    """Retrieves a single task by its ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return task_row_to_dict(row) if row else None


def add_task(text, category):
    """Adds a new active task to a category at the end of the order."""
    text = (text or "").strip()
    category = (category or "Misc").strip()
    if not text:
        raise ValueError("Task text cannot be empty.")

    now_iso = datetime.now(APP_TIMEZONE).isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(MAX(display_order), 0) as max_ord FROM tasks WHERE category = ? AND status = 'active'",
            (category,)
        )
        row = cursor.fetchone()
        next_order = (row["max_ord"] if row else 0) + 1

        cursor.execute("""
            INSERT INTO tasks (category, text, completed, status, display_order, created_at)
            VALUES (?, ?, 0, 'active', ?, ?)
        """, (category, text, next_order, now_iso))
        conn.commit()
        task_id = cursor.lastrowid

    return get_task_by_id(task_id)


def update_task(task_id, text=None, category=None, completed=None, display_order=None):
    """Updates a task's text, category, completion status, or display order."""
    task = get_task_by_id(task_id)
    if not task:
        return None

    updates = []
    params = []

    if text is not None:
        trimmed = text.strip()
        if not trimmed:
            raise ValueError("Task text cannot be empty.")
        updates.append("text = ?")
        params.append(trimmed)

    if category is not None:
        trimmed_cat = category.strip()
        if trimmed_cat:
            updates.append("category = ?")
            params.append(trimmed_cat)

    if completed is not None:
        is_comp = 1 if completed else 0
        updates.append("completed = ?")
        params.append(is_comp)
        if is_comp:
            updates.append("completed_at = ?")
            params.append(datetime.now(APP_TIMEZONE).isoformat())
        else:
            updates.append("completed_at = NULL")

    if display_order is not None:
        updates.append("display_order = ?")
        params.append(int(display_order))

    if not updates:
        return task

    params.append(task_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    return get_task_by_id(task_id)


def reorder_tasks(items):
    """
    Batch updates tasks display_order and optional category.
    items: list of dicts [{'id': int, 'display_order': int, 'category': str (optional)}]
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        for item in items:
            tid = item.get("id")
            order = item.get("display_order", 0)
            cat = item.get("category")
            if cat:
                cursor.execute(
                    "UPDATE tasks SET display_order = ?, category = ? WHERE id = ?",
                    (order, cat, tid)
                )
            else:
                cursor.execute(
                    "UPDATE tasks SET display_order = ? WHERE id = ?",
                    (order, tid)
                )
        conn.commit()
    return True


def archive_completed_now():
    """Immediately moves all completed active tasks to status = 'archived'."""
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks
            SET status = 'archived', archived_at = ?
            WHERE status = 'active' AND completed = 1
        """, (now_iso,))
        count = cursor.rowcount
        conn.commit()
    return count


def archive_all(category=None):
    """Archives all active tasks, optionally for a specific category."""
    now_iso = datetime.now(APP_TIMEZONE).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "UPDATE tasks SET status = 'archived', archived_at = ? WHERE status = 'active'"
        params = [now_iso]
        if category:
            query += " AND category = ?"
            params.append(category)
        cursor.execute(query, params)
        count = cursor.rowcount
        conn.commit()
    return count


def restore_task(task_id):
    """Restores an archived task back to active status (uncompleted)."""
    task = get_task_by_id(task_id)
    if not task:
        return None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(MAX(display_order), 0) as max_ord FROM tasks WHERE category = ? AND status = 'active'",
            (task["category"],)
        )
        row = cursor.fetchone()
        next_order = (row["max_ord"] if row else 0) + 1

        cursor.execute("""
            UPDATE tasks
            SET status = 'active', completed = 0, completed_at = NULL, archived_at = NULL, display_order = ?
            WHERE id = ?
        """, (next_order, task_id))
        conn.commit()

    return get_task_by_id(task_id)


def delete_task(task_id):
    """Permanently deletes a task by id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        count = cursor.rowcount
        conn.commit()
    return count > 0


def delete_all(status="active", category=None):
    """Permanently deletes tasks filtered by status and optional category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "DELETE FROM tasks WHERE status = ?"
        params = [status]
        if category:
            query += " AND category = ?"
            params.append(category)
        cursor.execute(query, params)
        count = cursor.rowcount
        conn.commit()
    return count
