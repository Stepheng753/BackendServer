from flask import Blueprint, jsonify, render_template, request
from .db import (
    init_db,
    get_accounts,
    get_account_by_id,
    update_account_metadata,
    upsert_account,
    get_historical_snapshots,
    get_summary,
    record_snapshot,
    get_setting,
    set_setting,
    get_budget_items,
    get_budget_item_by_id,
    upsert_budget_item,
    delete_budget_item,
    toggle_budget_item_active,
    get_budget_summary
)
from .config import (
    SIMPLEFIN_AUTH_KEY,
    SIMPLEFIN_CLAIM_KEY,
    SIMPLEFIN_LAST_SYNC_KEY,
    save_secret
)
from .simplefin_client import (
    claim_access_url,
    sync_simplefin_accounts,
    get_stored_access_url
)

finance_bp = Blueprint('finance', __name__, template_folder='templates')

# Initialize DB and seed baseline on import
init_db()


# ---------------------------------------------------------------------------
# PAGE VIEWS
# ---------------------------------------------------------------------------

@finance_bp.route("/finance", methods=["GET"])
def finance_page():
    """Renders the main Financial Dashboard UI."""
    return render_template("finance.html")


# ---------------------------------------------------------------------------
# API ENDPOINTS
# ---------------------------------------------------------------------------

@finance_bp.route("/api/finance/summary", methods=["GET"])
def api_summary():
    """Returns high-level KPI metrics and categorized accounts."""
    try:
        summary = get_summary()
        return jsonify({"status": "success", "data": summary})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route("/api/finance/accounts", methods=["GET"])
def api_accounts():
    """Returns all individual accounts."""
    try:
        accounts = get_accounts()
        return jsonify({"status": "success", "accounts": accounts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route("/api/finance/history", methods=["GET"])
def api_history():
    """Returns time-series snapshot data for the growth chart."""
    timeframe = request.args.get("timeframe", "all")
    try:
        history_data = get_historical_snapshots(timeframe=timeframe)
        return jsonify({"status": "success", "data": history_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route("/api/finance/sync", methods=["POST"])
def api_sync():
    """Triggers account synchronization from SimpleFIN Bridge (or updates timestamp)."""
    try:
        result = sync_simplefin_accounts()
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@finance_bp.route("/api/finance/claim", methods=["POST"])
def api_claim():
    """Claims a SimpleFIN access URL using a one-time claim token, or saves an existing Access URL."""
    payload = request.get_json(silent=True) or {}
    claim_token = payload.get("claim_token", "").strip()
    access_url = payload.get("access_url", "").strip()

    if access_url:
        save_secret("SIMPLEFIN_ACCESS_URL", access_url)
        set_setting(SIMPLEFIN_AUTH_KEY, access_url)
        return jsonify({
            "success": True,
            "message": "Saved SimpleFIN Access URL successfully!"
        })

    if not claim_token:
        return jsonify({"success": False, "error": "Please provide a claim token or access URL."}), 400

    result = claim_access_url(claim_token)
    if result.get("success"):
        # Auto-trigger first sync
        sync_simplefin_accounts()
    return jsonify(result), 200 if result.get("success") else 400


@finance_bp.route("/api/finance/settings", methods=["GET"])
def api_settings():
    """Returns SimpleFIN connection status and configuration."""
    access_url = get_stored_access_url()
    claim_token = get_setting(SIMPLEFIN_CLAIM_KEY, "")
    last_sync = get_setting(SIMPLEFIN_LAST_SYNC_KEY, "")
    has_token = bool(access_url)

    # Mask access url for security
    masked_url = ""
    if access_url:
        if "@" in access_url:
            parts = access_url.split("@")
            masked_url = f"https://***:***@{parts[-1]}"
        else:
            masked_url = access_url[:12] + "..."

    return jsonify({
        "connected": has_token,
        "masked_url": masked_url,
        "has_access_url": has_token,
        "claim_token_preview": claim_token,
        "last_sync": last_sync
    })


@finance_bp.route("/api/finance/disconnect", methods=["POST"])
def api_disconnect():
    """Disconnects SimpleFIN Bridge credentials."""
    save_secret("SIMPLEFIN_ACCESS_URL", "")
    set_setting(SIMPLEFIN_AUTH_KEY, "")
    set_setting(SIMPLEFIN_CLAIM_KEY, "")
    return jsonify({"success": True, "message": "SimpleFIN credentials removed."})


@finance_bp.route("/api/finance/account/<account_id>", methods=["POST"])
def api_update_account(account_id):
    """Updates account metadata, custom note, credit limit, or balance."""
    payload = request.get_json(silent=True) or {}
    acc = get_account_by_id(account_id)
    if not acc:
        return jsonify({"success": False, "error": "Account not found."}), 404

    # If updating balance directly for manual adjustments
    if "balance" in payload:
        try:
            acc["balance"] = float(payload["balance"])
            upsert_account(acc)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid balance value."}), 400

    update_account_metadata(
        account_id,
        apy_interest=payload.get("apy_interest"),
        rewards_status=payload.get("rewards_status"),
        holdings_summary=payload.get("holdings_summary"),
        credit_limit=payload.get("credit_limit")
    )

    # Re-calculate snapshot
    record_snapshot(note=f"Manual update on account {account_id}")

    return jsonify({"success": True, "message": "Account updated successfully."})


# ---------------------------------------------------------------------------
# BUDGET & RECURRING EXPENSES / INCOMES API
# ---------------------------------------------------------------------------

@finance_bp.route("/api/finance/budget", methods=["GET"])
def api_get_budget():
    """Returns budget summary, list of incomes, and list of expenses."""
    try:
        data = get_budget_summary()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route("/api/finance/budget/item/<int:item_id>", methods=["GET"])
def api_get_budget_item(item_id):
    """Retrieves an individual budget item with detailed JSON payload (e.g. paystub breakdown)."""
    try:
        item = get_budget_item_by_id(item_id)
        if not item:
            return jsonify({"status": "error", "message": "Budget item not found."}), 404
        return jsonify({"status": "success", "item": item})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route("/api/finance/budget/item", methods=["POST"])
def api_save_budget_item():
    """Creates or updates a budget item."""
    payload = request.get_json(silent=True) or {}
    name = payload.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "Name is required."}), 400

    try:
        item_id = upsert_budget_item(payload)
        return jsonify({
            "success": True,
            "message": "Budget item saved successfully.",
            "item_id": item_id
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@finance_bp.route("/api/finance/budget/item/<int:item_id>", methods=["DELETE"])
def api_delete_budget_item(item_id):
    """Deletes a budget item."""
    try:
        deleted = delete_budget_item(item_id)
        if not deleted:
            return jsonify({"success": False, "error": "Item not found."}), 404
        return jsonify({"success": True, "message": "Budget item removed."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@finance_bp.route("/api/finance/budget/toggle/<int:item_id>", methods=["POST"])
def api_toggle_budget_item(item_id):
    """Toggles active/inactive state of a budget item."""
    try:
        toggled = toggle_budget_item_active(item_id)
        if not toggled:
            return jsonify({"success": False, "error": "Item not found."}), 404
        return jsonify({"success": True, "message": "Budget item status updated."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

