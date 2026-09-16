import os
import sys
import unittest
from datetime import datetime, timedelta
import pytz

# Add repo root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ToDo.config import load_categories, APP_TIMEZONE
from ToDo.db import (
    init_db,
    get_connection,
    get_tasks,
    add_task,
    update_task,
    reorder_tasks,
    archive_completed_now,
    archive_all,
    restore_task,
    delete_task,
    delete_all,
    get_last_monday_2am,
    auto_archive_expired_tasks
)
from app import app


class TestToDoApp(unittest.TestCase):

    def setUp(self):
        init_db()
        # Clean test state
        with get_connection() as conn:
            conn.cursor().execute("DELETE FROM tasks WHERE text LIKE '[TEST]%'")
            conn.commit()

    def tearDown(self):
        with get_connection() as conn:
            conn.cursor().execute("DELETE FROM tasks WHERE text LIKE '[TEST]%'")
            conn.commit()

    def test_load_categories(self):
        from ToDo.config import DEFAULT_CATEGORIES
        self.assertEqual(len(DEFAULT_CATEGORIES), 7)
        self.assertEqual(DEFAULT_CATEGORIES[0]["name"], "Category 1")
        self.assertEqual(DEFAULT_CATEGORIES[0]["color"], "#005fa3")

        cats = load_categories()
        self.assertGreaterEqual(len(cats), 1)
        for c in cats:
            self.assertIn("id", c)
            self.assertIn("name", c)
            self.assertIn("color", c)

    def test_task_crud_and_reorder(self):
        task1 = add_task("[TEST] Task One", "Category 1")
        self.assertIsNotNone(task1)
        self.assertEqual(task1["text"], "[TEST] Task One")
        self.assertEqual(task1["category"], "Category 1")
        self.assertFalse(task1["completed"])
        self.assertEqual(task1["status"], "active")

        task2 = add_task("[TEST] Task Two", "Category 1")
        self.assertGreater(task2["display_order"], task1["display_order"])

        # Mark complete
        updated = update_task(task1["id"], completed=True)
        self.assertTrue(updated["completed"])
        self.assertIsNotNone(updated["completed_at"])

        # Reorder
        reorder_tasks([
            {"id": task2["id"], "display_order": 1, "category": "Category 1"},
            {"id": task1["id"], "display_order": 2, "category": "Category 1"}
        ])
        tasks = [t for t in get_tasks(status="active", category="Category 1") if t["text"].startswith("[TEST]")]
        self.assertEqual(tasks[0]["id"], task2["id"])
        self.assertEqual(tasks[1]["id"], task1["id"])

        # Update display_order directly
        updated_ord = update_task(task1["id"], display_order=50)
        self.assertEqual(updated_ord["display_order"], 50)

        # Delete
        self.assertTrue(delete_task(task2["id"]))
        self.assertTrue(delete_task(task1["id"]))

    def test_manual_archive_and_restore(self):
        task = add_task("[TEST] To Archive", "Category 2")
        update_task(task["id"], completed=True)

        count = archive_completed_now()
        self.assertGreaterEqual(count, 1)

        archived_tasks = [t for t in get_tasks(status="archived", category="Category 2") if t["id"] == task["id"]]
        self.assertEqual(len(archived_tasks), 1)
        self.assertEqual(archived_tasks[0]["status"], "archived")

        # Restore
        restored = restore_task(task["id"])
        self.assertEqual(restored["status"], "active")
        self.assertFalse(restored["completed"])

    def test_monday_2am_auto_archive(self):
        now = datetime.now(APP_TIMEZONE)
        cutoff = get_last_monday_2am(now)
        self.assertEqual(cutoff.weekday(), 0)  # Monday
        self.assertEqual(cutoff.hour, 2)
        self.assertEqual(cutoff.minute, 0)

        # Create a task completed 2 weeks ago (prior to cutoff)
        task_old = add_task("[TEST] Old Completed Task", "Category 3")
        old_completed_dt = (cutoff - timedelta(days=2)).isoformat()
        with get_connection() as conn:
            conn.cursor().execute(
                "UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?",
                (old_completed_dt, task_old["id"])
            )
            conn.commit()

        # Create a task completed 10 minutes ago (assuming within current week)
        task_recent = add_task("[TEST] Recent Completed Task", "Category 3")
        recent_completed_dt = (now).isoformat()
        with get_connection() as conn:
            conn.cursor().execute(
                "UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?",
                (recent_completed_dt, task_recent["id"])
            )
            conn.commit()

        # Run auto archive
        auto_archive_expired_tasks()

        # Check statuses
        active_ids = [t["id"] for t in get_tasks(status="active", category="Category 3")]
        archived_ids = [t["id"] for t in get_tasks(status="archived", category="Category 3")]

        self.assertIn(task_old["id"], archived_ids)
        self.assertNotIn(task_old["id"], active_ids)
        self.assertIn(task_recent["id"], active_ids)

    def test_flask_routes(self):
        client = app.test_client()
        # Test categories endpoint
        res = client.get("/api/todo/categories")
        # May require auth or allow
        # If check_auth returns 401 without auth header, supply basic auth
        auth_headers = {}
        if res.status_code == 401:
            from index.index import get_auth_credentials
            import base64
            u, p = get_auth_credentials()
            if u and p:
                token = base64.b64encode(f"{u}:{p}".encode()).decode()
                auth_headers = {"Authorization": f"Basic {token}"}
                res = client.get("/api/todo/categories", headers=auth_headers)

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("categories", data)

        # Test items endpoint
        res_items = client.get("/api/todo/items?status=active", headers=auth_headers)
        self.assertEqual(res_items.status_code, 200)
        data_items = res_items.get_json()
        self.assertIn("tasks", data_items)

        # Test page render
        res_page = client.get("/todo", headers=auth_headers)
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b"To-Do Board", res_page.data)

    def test_openapi_spec(self):
        client = app.test_client()
        from index.index import get_auth_credentials
        import base64
        u, p = get_auth_credentials()
        auth_headers = {}
        if u and p:
            token = base64.b64encode(f"{u}:{p}".encode()).decode()
            auth_headers = {"Authorization": f"Basic {token}"}

        res = client.get("/openapi.json", headers=auth_headers)
        self.assertEqual(res.status_code, 200)
        spec = res.get_json()
        tag_names = [t["name"] for t in spec.get("tags", [])]
        self.assertIn("To Do", tag_names)
        self.assertIn("/api/todo/items", spec.get("paths", {}))
        self.assertIn("/api/todo/categories", spec.get("paths", {}))


if __name__ == "__main__":
    unittest.main()
