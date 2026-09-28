import base64
import re
from urllib.parse import urlparse
import requests
from datetime import datetime
from .config import (
    APP_TIMEZONE,
    SIMPLEFIN_AUTH_KEY,
    SIMPLEFIN_CLAIM_KEY,
    SIMPLEFIN_LAST_SYNC_KEY,
    get_secret,
    save_secret
)
from .db import (
    get_setting,
    set_setting,
    get_accounts,
    upsert_account,
    record_snapshot
)


def decode_claim_token(raw_token: str) -> str:
    """
    Decodes the user's claim token.
    SimpleFIN claim tokens are base64-encoded claim URLs, or directly a claim URL.
    """
    token = raw_token.strip()
    if token.startswith("http://") or token.startswith("https://"):
        return token

    # Attempt base64 decoding
    try:
        decoded = base64.b64decode(token).decode("utf-8").strip()
        if decoded.startswith("http://") or decoded.startswith("https://"):
            return decoded
    except Exception:
        pass

    # If it's just the token suffix, build the full URL
    return f"https://beta-bridge.simplefin.org/simplefin/claim/{token}"


def claim_access_url(claim_token_input: str) -> dict:
    """
    Exchanges a one-time SimpleFIN claim token for a permanent access URL.
    """
    claim_url = decode_claim_token(claim_token_input)
    try:
        res = requests.post(claim_url, timeout=15)
        if res.status_code == 200:
            access_url = res.text.strip()
            if not access_url.startswith("http"):
                return {"success": False, "error": f"Unexpected response from SimpleFIN: {access_url}"}

            save_secret("SIMPLEFIN_ACCESS_URL", access_url)
            set_setting(SIMPLEFIN_AUTH_KEY, access_url)
            set_setting(SIMPLEFIN_CLAIM_KEY, claim_token_input[:10] + "...")
            return {
                "success": True,
                "message": "Successfully claimed SimpleFIN Access URL!",
                "access_url": access_url
            }
        else:
            return {
                "success": False,
                "error": f"SimpleFIN server returned status {res.status_code}: {res.text}"
            }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Failed to reach SimpleFIN Bridge: {str(e)}"}


def get_stored_access_url() -> str:
    """Returns stored SimpleFIN Access URL or empty string, checking secrets.json first."""
    url = get_secret("SIMPLEFIN_ACCESS_URL")
    if url:
        return url
    return get_setting(SIMPLEFIN_AUTH_KEY, "")


def infer_account_type(name: str, org_name: str, balance: float) -> str:
    """Heuristic helper to classify SimpleFIN accounts."""
    combined = f"{org_name} {name}".lower()
    if any(k in combined for k in ["mortgage", "home loan", "rocket"]):
        return "mortgage"
    if any(k in combined for k in ["401k", "401(k)", "ira", "roth", "fidelity"]):
        return "retirement"
    if any(k in combined for k in ["brokerage", "schwab", "investment", "stock"]):
        return "investment"
    if any(k in combined for k in ["card", "credit", "cash®", "sapphire", "freedom"]):
        return "credit"
    if any(k in combined for k in ["savings", "hysa", "wealthfront"]):
        return "savings"
    if any(k in combined for k in ["checking", "everyday"]):
        return "checking"
    if balance < -1000:
        return "loan"
    return "checking"


def match_existing_account(existing_accounts, sf_account):
    """
    Attempts to match an incoming SimpleFIN account to an existing seeded account
    to preserve friendly notes, APYs, rewards status, and credit limits.
    """
    sf_name = (sf_account.get("name") or "").lower()
    org_name = (sf_account.get("org", {}).get("name") or "").lower()

    for acc in existing_accounts:
        acc_name = acc["name"].lower()
        acc_org = acc["institution"].lower()

        # Match mortgage
        if ("rocket" in org_name or "rocket" in sf_name or "mortgage" in sf_name) and acc["account_type"] == "mortgage":
            return acc
        # Match wealthfront
        if "wealthfront" in org_name or "wealthfront" in sf_name:
            if acc["account_type"] == "savings":
                return acc
        # Match fidelity 401k
        if "fidelity" in org_name or "401" in sf_name or "5830" in sf_name:
            if "401" in acc_name:
                return acc
        # Match Schwab IRAs & Brokerage
        if "schwab" in org_name or "schwab" in sf_name:
            if ("roth" in sf_name or "476" in sf_name) and "roth" in acc_name:
                return acc
            if ("trad" in sf_name or "traditional" in sf_name or "378" in sf_name) and "trad" in acc_name:
                return acc
            if ("309" in sf_name or "individual" in sf_name or "brokerage" in sf_name) and ("brokerage" in acc_name or "309" in acc["id"]):
                return acc
        # Match Wells Fargo
        if "wells" in org_name or "wells" in sf_name:
            if ("checking" in sf_name or "3484" in sf_name) and acc["account_type"] == "checking":
                return acc
            if ("active" in sf_name or "credit" in sf_name or "4615" in sf_name) and acc["account_type"] == "credit":
                return acc
        # Match Chase
        if "chase" in org_name or "chase" in sf_name:
            if ("sapphire" in sf_name or "6527" in sf_name) and "sapphire" in acc_name:
                return acc
            if ("freedom" in sf_name or "6019" in sf_name) and "freedom" in acc_name:
                return acc
        # Match Wealthfront
        if "wealthfront" in org_name or "wealthfront" in sf_name or "6100" in sf_name:
            if acc["account_type"] == "savings":
                return acc

    return None


def sync_simplefin_accounts() -> dict:
    """
    Connects to SimpleFIN Bridge, fetches live account data,
    updates local accounts, and records a new historical snapshot.
    """
    access_url = get_stored_access_url()
    now_iso = datetime.now(APP_TIMEZONE).isoformat()

    if not access_url:
        # If no access URL is configured yet, record current seeded snapshot as a fresh sync
        record_snapshot(note="Manual sync (Pre-SimpleFIN baseline)")
        set_setting(SIMPLEFIN_LAST_SYNC_KEY, now_iso)
        return {
            "success": True,
            "is_simulated": True,
            "message": "Synced current accounts & recorded snapshot. To pull live institutional balances, paste your SimpleFIN Claim Token in Settings!",
            "synced_at": now_iso
        }

    # Fetch from SimpleFIN Bridge
    try:
        # Parse basic auth from access_url if present
        parsed = urlparse(access_url)
        auth = None
        clean_url = access_url
        if parsed.username and parsed.password:
            auth = (parsed.username, parsed.password)
            clean_url = f"{parsed.scheme}://{parsed.hostname}{':' + str(parsed.port) if parsed.port else ''}{parsed.path}"

        endpoint = f"{clean_url.rstrip('/')}/accounts"
        res = requests.get(endpoint, auth=auth, timeout=25)

        if res.status_code != 200:
            return {
                "success": False,
                "error": f"SimpleFIN Bridge responded with status {res.status_code}: {res.text[:200]}"
            }

        data = res.json()
        sf_accounts = data.get("accounts", [])
        existing_accounts = get_accounts()

        updated_count = 0
        for sf_acc in sf_accounts:
            org = sf_acc.get("org", {})
            org_name = org.get("name") or "Financial Institution"
            name = sf_acc.get("name") or "Account"
            currency = sf_acc.get("currency") or "USD"

            try:
                balance = float(sf_acc.get("balance", 0.0))
            except (ValueError, TypeError):
                balance = 0.0

            matched = match_existing_account(existing_accounts, sf_acc)

            if matched:
                target_id = matched["id"]
                account_type = matched["account_type"]
                is_asset = matched["is_asset"]
                apy = matched.get("apy_interest")
                rewards = matched.get("rewards_status")
                limit = float(matched.get("credit_limit") or 0.0)
                vested = float(matched.get("vested_balance") or balance)
                holdings = matched.get("holdings_summary")
                mask = matched.get("account_number_mask")
            else:
                target_id = f"sf_{sf_acc.get('id', re.sub(r'[^a-zA-Z0-9_]', '_', name.lower()))}"
                account_type = infer_account_type(name, org_name, balance)
                is_asset = 0 if account_type in ("mortgage", "credit", "loan") else 1
                apy = None
                rewards = None
                limit = 0.0
                vested = balance if is_asset else 0.0
                holdings = None
                mask = None

            # Extract institutional sync timestamp from SimpleFIN (balance-date)
            # This represents the exact time SimpleFIN connected to the bank's API
            bdate_epoch = sf_acc.get("balance-date")
            if bdate_epoch:
                try:
                    acct_synced_at = datetime.fromtimestamp(float(bdate_epoch), tz=APP_TIMEZONE).isoformat()
                except Exception:
                    acct_synced_at = now_iso
            else:
                acct_synced_at = now_iso

            # Normalization for liability convention
            if account_type == "mortgage" and balance > 0:
                balance = -abs(balance)

            upsert_account({
                "id": target_id,
                "institution": org_name if not matched else matched["institution"],
                "name": name if not matched else matched["name"],
                "account_number_mask": mask,
                "account_type": account_type,
                "balance": balance,
                "currency": currency,
                "apy_interest": apy,
                "rewards_status": rewards,
                "credit_limit": limit,
                "vested_balance": vested,
                "holdings_summary": holdings,
                "is_asset": is_asset,
                "is_manual": 0 if matched is None else matched.get("is_manual", 0),
                "last_synced": acct_synced_at
            })
            updated_count += 1

        # Record a fresh historical snapshot
        snapshot_id = record_snapshot(note=f"SimpleFIN live sync ({updated_count} accounts)")
        set_setting(SIMPLEFIN_LAST_SYNC_KEY, now_iso)

        return {
            "success": True,
            "is_simulated": False,
            "updated_count": updated_count,
            "snapshot_id": snapshot_id,
            "message": f"Successfully synced {updated_count} accounts from SimpleFIN Bridge!",
            "synced_at": now_iso
        }

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Connection error syncing SimpleFIN: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error parsing SimpleFIN payload: {str(e)}"}
