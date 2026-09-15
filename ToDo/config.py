import os
import json
import pytz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CATEGORIES_FILE = os.path.join(CONFIG_DIR, "categories.json")
DB_PATH = os.path.join(CONFIG_DIR, "tasks.db")

APP_TIMEZONE = pytz.timezone("America/Los_Angeles")

DEFAULT_CATEGORIES = [
    {"name": "Category 1", "color": "#005fa3"},
    {"name": "Category 2", "color": "#55b080"},
    {"name": "Category 3", "color": "#a479b1"},
    {"name": "Category 4", "color": "#e7ba51"},
    {"name": "Category 5", "color": "#bc2b2e"},
    {"name": "Category 6", "color": "#f294e9"},
    {"name": "Category 7", "color": "#e0963c"}
]


def load_categories():
    """
    Loads categories from config/categories.json, supporting various formats:
    - {"categories": [{"name": "Category 1", "color": "#005fa3"}, ...]}
    - {"categories": [{"Category 1": "#005fa3"}, ...]}
    - {"categories": {"Category 1": "#005fa3", ...}}
    - [{"name": "...", "color": "..."}, ...]
    Returns a normalized list of objects: [{'id': str, 'name': str, 'color': str}, ...]
    Auto-initializes config/categories.json if missing.
    """
    raw_data = None
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            print(f"[ToDo] Warning loading categories.json: {e}")
    else:
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
                json.dump({"categories": DEFAULT_CATEGORIES}, f, indent=2)
            raw_data = {"categories": DEFAULT_CATEGORIES}
        except Exception as e:
            print(f"[ToDo] Note: Could not auto-create categories.json: {e}")

    if not raw_data:
        raw_data = {"categories": DEFAULT_CATEGORIES}

    categories_list = []
    items = raw_data.get("categories", raw_data) if isinstance(raw_data, dict) else raw_data

    if isinstance(items, dict):
        for name, color in items.items():
            categories_list.append({
                "id": str(name).strip(),
                "name": str(name).strip(),
                "color": str(color).strip() if isinstance(color, str) else "#6ba3d6"
            })
    elif isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                if "name" in item:
                    cat_name = str(item.get("name", "")).strip()
                    cat_color = str(item.get("color", "#6ba3d6")).strip()
                    cat_id = str(item.get("id", cat_name)).strip()
                    if cat_name:
                        categories_list.append({
                            "id": cat_id,
                            "name": cat_name,
                            "color": cat_color
                        })
                else:
                    # e.g. {"Category 1": "#005fa3"}
                    for k, v in item.items():
                        if isinstance(v, dict):
                            cat_color = v.get("color", "#6ba3d6")
                        else:
                            cat_color = str(v)
                        categories_list.append({
                            "id": str(k).strip(),
                            "name": str(k).strip(),
                            "color": str(cat_color).strip()
                        })

    if not categories_list:
        categories_list = [
            {"id": c["name"], "name": c["name"], "color": c["color"]}
            for c in DEFAULT_CATEGORIES
        ]

    return categories_list
