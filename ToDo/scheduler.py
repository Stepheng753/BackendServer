import threading
import time
from datetime import datetime
from .config import APP_TIMEZONE
from .db import auto_archive_expired_tasks

_scheduler_started = False
_lock = threading.Lock()


def _scheduler_loop():
    """Background worker that periodically triggers auto_archive_expired_tasks."""
    while True:
        try:
            archived = auto_archive_expired_tasks()
            if archived > 0:
                print(f"[ToDo Scheduler] Automatically archived {archived} tasks past Monday 2 AM cutoff.")
        except Exception as e:
            print(f"[ToDo Scheduler] Error in auto-archive cycle: {e}")

        # Sleep for 10 minutes between checks
        time.sleep(600)


def start_todo_scheduler():
    """Starts the background auto-archive daemon thread if not already running."""
    global _scheduler_started
    with _lock:
        if not _scheduler_started:
            thread = threading.Thread(target=_scheduler_loop, daemon=True, name="ToDoAutoArchiveScheduler")
            thread.start()
            _scheduler_started = True
            print("[ToDo Scheduler] Background auto-archive scheduler started.")
