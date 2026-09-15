from flask import Blueprint, jsonify, render_template, request
from .config import load_categories
from .db import (
    init_db,
    get_tasks,
    get_task_by_id,
    add_task,
    update_task,
    reorder_tasks,
    archive_completed_now,
    archive_all,
    restore_task,
    delete_task,
    delete_all
)

todo_bp = Blueprint('todo', __name__, template_folder='templates')

# Ensure DB is initialized when routes are loaded
init_db()


@todo_bp.route("/todo")
def todo_page():
    """Renders the interactive To-Do grid application."""
    categories = load_categories()
    return render_template("todo.html", categories=categories)


@todo_bp.route("/api/todo/categories", methods=["GET"])
def api_get_categories():
    """Returns the list of configured categories with color codes."""
    categories = load_categories()
    return jsonify({"categories": categories})


@todo_bp.route("/api/todo/items", methods=["GET"])
def api_get_items():
    """
    Returns tasks filtered by status ('active' or 'archived') and optional category.
    Includes categories list in response for convenient client rendering.
    """
    status = request.args.get("status", "active").lower()
    if status not in ["active", "archived"]:
        status = "active"
    category = request.args.get("category")

    tasks = get_tasks(status=status, category=category)
    categories = load_categories()
    return jsonify({
        "status": status,
        "categories": categories,
        "tasks": tasks
    })


@todo_bp.route("/api/todo/items", methods=["POST"])
def api_add_item():
    """Creates a new task in a category."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    category = data.get("category", "Misc").strip()

    if not text:
        return jsonify({"error": "Task text is required."}), 400

    try:
        task = add_task(text=text, category=category)
        return jsonify({"success": True, "task": task}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@todo_bp.route("/api/todo/items/<int:item_id>", methods=["PATCH", "PUT"])
def api_update_item(item_id):
    """Updates task properties: text, category, or completion state."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text")
    category = data.get("category")
    completed = data.get("completed")

    try:
        updated = update_task(item_id, text=text, category=category, completed=completed)
        if not updated:
            return jsonify({"error": "Task not found."}), 404
        return jsonify({"success": True, "task": updated})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@todo_bp.route("/api/todo/items/<int:item_id>", methods=["DELETE"])
def api_delete_item(item_id):
    """Permanently deletes a task."""
    deleted = delete_task(item_id)
    if not deleted:
        return jsonify({"error": "Task not found."}), 404
    return jsonify({"success": True, "id": item_id})


@todo_bp.route("/api/todo/items/<int:item_id>/restore", methods=["POST"])
def api_restore_item(item_id):
    """Restores an archived task back to the active list."""
    task = restore_task(item_id)
    if not task:
        return jsonify({"error": "Task not found."}), 404
    return jsonify({"success": True, "task": task})


@todo_bp.route("/api/todo/reorder", methods=["POST"])
def api_reorder():
    """Updates display order and category assignment for a list of items."""
    data = request.get_json(force=True, silent=True) or {}
    items = data.get("items", [])
    if not isinstance(items, list):
        return jsonify({"error": "Items list expected."}), 400

    reorder_tasks(items)
    return jsonify({"success": True})


@todo_bp.route("/api/todo/archive-completed", methods=["POST"])
def api_archive_completed():
    """Immediately archives all crossed-out (completed) active tasks."""
    count = archive_completed_now()
    return jsonify({"success": True, "archived_count": count})


@todo_bp.route("/api/todo/archive-all", methods=["POST"])
def api_archive_all():
    """Archives all active tasks (or for a specified category)."""
    data = request.get_json(force=True, silent=True) or {}
    category = data.get("category")
    count = archive_all(category=category)
    return jsonify({"success": True, "archived_count": count})


@todo_bp.route("/api/todo/delete-all", methods=["POST"])
def api_delete_all():
    """Permanently deletes all tasks in the current status / category."""
    data = request.get_json(force=True, silent=True) or {}
    status = data.get("status", "active").lower()
    category = data.get("category")
    if status not in ["active", "archived"]:
        status = "active"

    count = delete_all(status=status, category=category)
    return jsonify({"success": True, "deleted_count": count})
