# ToDo Module

The `ToDo` package provides an interactive task management board organized across custom categories, drag-and-drop task reordering, an automated weekly archival scheduler, and SQLite persistence.

Accessible at `http://localhost:5000/todo`.

---

## 1. Features & Architecture

* **Responsive Category Grid**: Tasks are organized into customizable category cards. Categories can be dynamically added, edited, reordered, or archived.
* **Eisenhower & Priority Sorting**: Supports priority indicators, task due dates, completion toggles, and drag-and-drop manual reordering that saves directly to backend indices.
* **Weekly Auto-Archive Scheduler**: Runs a background daemon thread that automatically archives completed tasks every **Monday at 2:00 AM PST**, ensuring a fresh board for the upcoming week while keeping completed history searchable in the archive.
* **Manual & Bulk Operations**: Instant one-click actions: "Archive Completed", "Restore Task", "View Archive", and "Archived Categories" viewer with conflict resolution safeguards.
* **SQLite WAL Mode Engine**: All tasks and categories are stored in `config/todo.db` with Write-Ahead Logging (`WAL`), supporting high concurrency and atomic transactions.
* **REST API & Swagger Specs**: Fully documented OpenAPI 3.0 endpoints with HTTP Basic Authentication.

---

## 2. Endpoints Reference

All endpoints are protected by HTTP Basic Authentication.

### Web Dashboard
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/todo` | `GET` | Interactive To-Do board interface with category management and archive views. |

### Tasks API
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/tasks` | `GET` | Retrieves active or archived tasks (`?status=active|archived`). |
| `POST /api/tasks` | `POST` | Creates a new task in a specified category. Automatically positions new active tasks above completed tasks. |
| `PUT /api/tasks/<id>` | `PUT` | Updates task text, category, priority, due date, or completion status. |
| `DELETE /api/tasks/<id>` | `DELETE`| Permanently deletes an individual task. |
| `POST /api/tasks/reorder` | `POST` | Reorders tasks within a category by persisting an array of task IDs in sequence. |
| `POST /api/tasks/archive-completed` | `POST` | Manually archives all currently completed tasks immediately. |
| `POST /api/tasks/archive-all` | `POST` | Archives all active tasks regardless of completion. |
| `POST /api/tasks/<id>/restore` | `POST` | Restores an archived task back to active status. |
| `POST /api/tasks/delete-all` | `POST` | Permanently deletes all archived tasks. |

### Categories API
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/categories` | `GET` | Lists all active categories with their task counts and sort orders. |
| `POST /api/categories` | `POST` | Creates a new category. Detects soft-archived duplicate names and offers restoration. |
| `PUT /api/categories/<id>` | `PUT` | Updates category name, color theme, or sort order. |
| `DELETE /api/categories/<id>` | `DELETE`| Permanently deletes a category and cascades deletion to associated tasks. |
| `POST /api/categories/<id>/archive` | `POST` | Archives a category along with all of its contained tasks. |
| `POST /api/categories/<id>/restore` | `POST` | Restores an archived category and its tasks back to the active board. |
| `GET /api/categories/archived` | `GET` | Retrieves all archived categories and their associated tasks. |

---

## 3. Database Schema

Stored in `config/todo.db`:

```
  ┌───────────────────────────────────────────────────────────┐
  │                        categories                         │
  ├───────────────────────────────────────────────────────────┤
  │ id (INTEGER PRIMARY KEY AUTOINCREMENT)                    │
  │ name (TEXT NOT NULL)                                      │
  │ sort_order (INTEGER NOT NULL DEFAULT 0)                   │
  │ status (TEXT NOT NULL DEFAULT 'active')                   │
  │ created_at, updated_at (TIMESTAMP)                        │
  └─────────────────────────────┬─────────────────────────────┘
                                │ 1:N (CASCADE)
                                ▼
  ┌───────────────────────────────────────────────────────────┐
  │                           tasks                           │
  ├───────────────────────────────────────────────────────────┤
  │ id (INTEGER PRIMARY KEY AUTOINCREMENT)                    │
  │ text (TEXT NOT NULL)                                      │
  │ category_id (INTEGER FK -> categories.id)                 │
  │ completed (INTEGER NOT NULL DEFAULT 0)                    │
  │ priority (TEXT DEFAULT 'medium')                          │
  │ due_date (TEXT)                                           │
  │ sort_order (INTEGER NOT NULL DEFAULT 0)                   │
  │ status (TEXT NOT NULL DEFAULT 'active')                   │
  │ created_at, updated_at, completed_at, archived_at         │
  └───────────────────────────────────────────────────────────┘
```

---

## 4. Package Structure

```
ToDo/
├── __init__.py                # Blueprint export (todo_bp) & background scheduler startup
├── config.py                  # Default categories fallback & timezone settings
├── db.py                      # SQLite WAL database layer, migrations, and scheduler logic
├── routes.py                  # Web & REST API endpoints for tasks and categories
├── templates/
│   └── todo.html              # Responsive board UI with drag-and-drop and dark mode
├── tests/
│   ├── __init__.py            # Test package marker
│   └── test_todo.py           # Unit tests for CRUD, reordering, categories, and scheduler
└── README.md                  # Module technical reference
```

---

## 5. Automated Testing

Run all unit tests for the To-Do module:

```bash
# From repository root
.venv/bin/python -m unittest discover -s ToDo/tests -p "test_*.py"
```
