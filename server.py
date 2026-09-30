from flask import Flask, jsonify, request, send_from_directory
from threading import Lock
from datetime import datetime, timezone
import os
import json
import uuid

# ============================================================
# SAINT BOT ROOM
# DEDICATED MT5 SCANNER + TERMINAL CONTROL SERVER
#
# IMPORTANT:
# - No Firebase
# - No Firestore
# - No SAINT ADMIN connection
# - Does not create trades
# - Scans only registered/active bot accounts
# - MT5 controller remains responsible for terminal actions
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(BASE_DIR, "DASHBOARD")
REGISTRY_FILE = os.path.join(BASE_DIR, "bot_accounts.json")

app = Flask(
    __name__,
    static_folder=DASHBOARD_DIR,
    static_url_path=""
)

lock = Lock()

MT5_TIMEOUT_SECONDS = int(
    os.getenv("MT5_OFFLINE_SECONDS", "45")
)

MONITOR_KEY = os.getenv(
    "SAINT_MT5_MONITOR_KEY",
    "CHANGE_THIS_MT5_KEY"
)

ADMIN_KEY = os.getenv(
    "SAINT_BOT_ADMIN_KEY",
    "CHANGE_THIS_ADMIN_KEY"
)

accounts = {}
commands = {}


# ============================================================
# TIME
# ============================================================

def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


# ============================================================
# LOCAL ACTIVE BOT ACCOUNT REGISTRY
# ============================================================

def load_registry():
    try:
        if not os.path.exists(REGISTRY_FILE):
            return {}

        with open(
            REGISTRY_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception as exc:
        print("[REGISTRY] Load failed:", exc)
        return {}


authorized_accounts = load_registry()


def save_registry():
    temp_file = REGISTRY_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            authorized_accounts,
            f,
            indent=2
        )

    os.replace(
        temp_file,
        REGISTRY_FILE
    )


def mt5_authorized(req):
    return (
        req.headers.get(
            "x-saint-mt5-key",
            ""
        )
        == MONITOR_KEY
    )


def admin_authorized(req):
    return (
        req.headers.get(
            "x-saint-admin-key",
            ""
        )
        == ADMIN_KEY
    )


def require_mt5_key():
    if not mt5_authorized(request):
        return jsonify({
            "ok": False,
            "error": "UNAUTHORIZED"
        }), 401

    return None


def require_admin_key():
    if not admin_authorized(request):
        return jsonify({
            "ok": False,
            "error": "UNAUTHORIZED"
        }), 401

    return None


# ============================================================
# ACCOUNT STATUS
# ============================================================

def is_online(account):
    last_seen = account.get("lastSeen")

    if not last_seen:
        return False

    try:
        last = datetime.fromisoformat(
            last_seen.replace("Z", "+00:00")
        )

        age = (
            now() - last
        ).total_seconds()

        return age <= MT5_TIMEOUT_SECONDS

    except Exception:
        return False


def public_account(account_id):
    registered = authorized_accounts.get(
        account_id,
        {}
    )

    live = accounts.get(
        account_id
    )

    result = {
        "accountId": account_id,
        "active": bool(
            registered.get(
                "active",
                False
            )
        ),
        "online": False,
        "broker": "",
        "server": "",
        "terminal": "",
        "currency": "",
        "balance": 0.0,
        "equity": 0.0,
        "freeMargin": 0.0,
        "margin": 0.0,
        "marginLevel": 0.0,
        "floatingPnl": 0.0,
        "positions": [],
        "positionCount": 0,
        "botStatus": "NOT_CONNECTED",
        "autotrading": "UNKNOWN",
        "lastSeen": None,
        "updatedAt": None
    }

    if live:
        result.update(live)
        result["online"] = is_online(live)

    return result


# ============================================================
# DASHBOARD FILES
# ============================================================

@app.get("/")
def index():
    return send_from_directory(
        DASHBOARD_DIR,
        "index.html"
    )


@app.get("/style.css")
def style():
    return send_from_directory(
        DASHBOARD_DIR,
        "style.css"
    )


@app.get("/app.js")
def javascript():
    return send_from_directory(
        DASHBOARD_DIR,
        "app.js"
    )


@app.get("/DASHBOARD/app.js")
def javascript_dashboard():
    return send_from_directory(
        DASHBOARD_DIR,
        "app.js"
    )


@app.get("/DASHBOARD/style.css")
def style_dashboard():
    return send_from_directory(
        DASHBOARD_DIR,
        "style.css"
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():
    with lock:
        active_ids = [
            account_id
            for account_id, data
            in authorized_accounts.items()
            if data.get("active", False)
        ]

        online = sum(
            1
            for account_id in active_ids
            if account_id in accounts
            and is_online(accounts[account_id])
        )

        return jsonify({
            "ok": True,
            "service": "SAINT BOT ROOM",
            "mode": "MT5 SCANNER + TERMINAL CONTROL",
            "firebase": False,
            "saintAdmin": False,
            "activeAccounts": len(active_ids),
            "onlineAccounts": online,
            "updatedAt": now_iso()
        })


# ============================================================
# ACTIVE ACCOUNT REGISTRY
# ============================================================

@app.get("/api/admin/accounts")
def admin_list_accounts():
    denied = require_admin_key()

    if denied:
        return denied

    with lock:
        result = []

        for account_id in authorized_accounts:
            result.append(
                public_account(account_id)
            )

        return jsonify({
            "ok": True,
            "accounts": result,
            "count": len(result)
        })


@app.post("/api/admin/accounts/register")
def register_account():
    denied = require_admin_key()

    if denied:
        return denied

    data = request.get_json(
        silent=True
    ) or {}

    account_id = str(
        data.get(
            "accountId",
            ""
        )
    ).strip()

    if not account_id:
        return jsonify({
            "ok": False,
            "error": "accountId is required"
        }), 400

    with lock:
        existing = authorized_accounts.get(
            account_id,
            {}
        )

        authorized_accounts[
            account_id
        ] = {
            "accountId": account_id,
            "active": bool(
                data.get(
                    "active",
                    True
                )
            ),
            "label": str(
                data.get(
                    "label",
                    existing.get(
                        "label",
                        ""
                    )
                )
            ),
            "registeredAt": existing.get(
                "registeredAt",
                now_iso()
            ),
            "updatedAt": now_iso()
        }

        save_registry()

        return jsonify({
            "ok": True,
            "account": public_account(
                account_id
            )
        }), 201


@app.post("/api/admin/accounts/<account_id>/activate")
def activate_account(account_id):
    denied = require_admin_key()

    if denied:
        return denied

    account_id = str(account_id)

    with lock:
        if account_id not in authorized_accounts:
            return jsonify({
                "ok": False,
                "error": "ACCOUNT_NOT_REGISTERED"
            }), 404

        authorized_accounts[
            account_id
        ]["active"] = True

        authorized_accounts[
            account_id
        ]["updatedAt"] = now_iso()

        save_registry()

        return jsonify({
            "ok": True,
            "account": public_account(
                account_id
            )
        })


@app.post("/api/admin/accounts/<account_id>/deactivate")
def deactivate_account(account_id):
    denied = require_admin_key()

    if denied:
        return denied

    account_id = str(account_id)

    with lock:
        if account_id not in authorized_accounts:
            return jsonify({
                "ok": False,
                "error": "ACCOUNT_NOT_REGISTERED"
            }), 404

        authorized_accounts[
            account_id
        ]["active"] = False

        authorized_accounts[
            account_id
        ]["updatedAt"] = now_iso()

        save_registry()

        return jsonify({
            "ok": True,
            "account": public_account(
                account_id
            )
        })


# ============================================================
# MT5 HEARTBEAT
# ============================================================

@app.post("/api/mt5/monitor/heartbeat")
def mt5_heartbeat():
    denied = require_mt5_key()

    if denied:
        return denied

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        raw = request.get_data(
            cache=False,
            as_text=False
        )

        try:
            raw_text = raw.decode(
                "utf-8",
                errors="replace"
            )
        except Exception:
            raw_text = str(raw)

        raw_text = raw_text.replace(
            "\x00",
            ""
        ).strip()

        try:
            data = json.loads(
                raw_text
            )
        except Exception:
            data = None

    if not isinstance(data, dict):
        return jsonify({
            "ok": False,
            "error": "INVALID_JSON"
        }), 400

    account_id = str(
        data.get(
            "accountId",
            data.get(
                "login",
                ""
            )
        )
    ).strip()

    if not account_id:
        return jsonify({
            "ok": False,
            "error": "accountId is required"
        }), 400

    with lock:
        registered = authorized_accounts.get(
            account_id
        )

        if not registered or not registered.get(
            "active",
            False
        ):
            print(
                "[MT5] BLOCKED inactive/unregistered account:",
                account_id
            )

            return jsonify({
                "ok": False,
                "error": "ACCOUNT_NOT_AUTHORIZED"
            }), 403

        positions = data.get(
            "positions",
            []
        )

        if not isinstance(
            positions,
            list
        ):
            positions = []

        accounts[
            account_id
        ] = {
            "accountId": account_id,
            "login": account_id,
            "broker": str(
                data.get(
                    "broker",
                    ""
                )
            ),
            "server": str(
                data.get(
                    "server",
                    ""
                )
            ),
            "terminal": str(
                data.get(
                    "terminal",
                    ""
                )
            ),
            "currency": str(
                data.get(
                    "currency",
                    ""
                )
            ),
            "balance": float(
                data.get(
                    "balance",
                    0
                ) or 0
            ),
            "equity": float(
                data.get(
                    "equity",
                    0
                ) or 0
            ),
            "freeMargin": float(
                data.get(
                    "freeMargin",
                    0
                ) or 0
            ),
            "margin": float(
                data.get(
                    "margin",
                    0
                ) or 0
            ),
            "marginLevel": float(
                data.get(
                    "marginLevel",
                    0
                ) or 0
            ),
            "floatingPnl": float(
                data.get(
                    "floatingPnl",
                    0
                ) or 0
            ),
            "positions": positions,
            "positionCount": len(
                positions
            ),
            "botStatus": str(
                data.get(
                    "botStatus",
                    "UNKNOWN"
                )
            ),
            "autotrading": str(
                data.get(
                    "autotrading",
                    "UNKNOWN"
                )
            ),
            "lastSeen": now_iso(),
            "updatedAt": now_iso()
        }

        print(
            "[MT5] HEARTBEAT",
            account_id,
            "positions=",
            len(positions),
            "status=",
            accounts[account_id][
                "botStatus"
            ]
        )

        return jsonify({
            "ok": True,
            "accountId": account_id,
            "acceptedAt": accounts[
                account_id
            ]["updatedAt"]
        })


# ============================================================
# ACCOUNT SCANNER API
# ============================================================

@app.get("/api/accounts")
def list_accounts():
    denied = require_mt5_key()

    if denied:
        return denied

    with lock:
        active_ids = [
            account_id
            for account_id, data
            in authorized_accounts.items()
            if data.get(
                "active",
                False
            )
        ]

        result = [
            public_account(account_id)
            for account_id in active_ids
        ]

        return jsonify({
            "ok": True,
            "accounts": result,
            "count": len(result)
        })


@app.get("/api/accounts/<account_id>")
def account_details(account_id):
    denied = require_mt5_key()

    if denied:
        return denied

    account_id = str(account_id)

    with lock:
        registered = authorized_accounts.get(
            account_id
        )

        if not registered or not registered.get(
            "active",
            False
        ):
            return jsonify({
                "ok": False,
                "error": "ACCOUNT_NOT_AUTHORIZED"
            }), 404

        return jsonify({
            "ok": True,
            "account": public_account(
                account_id
            )
        })


# ============================================================
# COMMAND QUEUE
# ============================================================

ALLOWED_COMMANDS = {
    "START_BOT",
    "STOP_BOT",
    "CLOSE_ALL",
    "REFRESH"
}


@app.post(
    "/api/accounts/<account_id>/command"
)
def create_command(account_id):
    denied = require_mt5_key()

    if denied:
        return denied

    data = request.get_json(
        silent=True
    ) or {}

    command = str(
        data.get(
            "command",
            ""
        )
    ).strip().upper()

    if command not in ALLOWED_COMMANDS:
        return jsonify({
            "ok": False,
            "error": "INVALID_COMMAND",
            "allowed": sorted(
                ALLOWED_COMMANDS
            )
        }), 400

    account_id = str(account_id)

    with lock:
        registered = authorized_accounts.get(
            account_id
        )

        if not registered or not registered.get(
            "active",
            False
        ):
            return jsonify({
                "ok": False,
                "error": "ACCOUNT_NOT_AUTHORIZED"
            }), 404

        if account_id not in accounts:
            return jsonify({
                "ok": False,
                "error": "ACCOUNT_NOT_CONNECTED"
            }), 409

        command_id = uuid.uuid4().hex

        commands[
            command_id
        ] = {
            "id": command_id,
            "accountId": account_id,
            "command": command,
            "symbol": str(
                data.get(
                    "symbol",
                    ""
                )
            ),
            "status": "PENDING",
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "result": None
        }

        print(
            "[COMMAND]",
            command,
            "account=",
            account_id,
            "id=",
            command_id
        )

        return jsonify({
            "ok": True,
            "command": commands[
                command_id
            ]
        }), 201


# ============================================================
# MT5 COMMAND POLLING
# ============================================================

@app.get(
    "/api/mt5/monitor/commands"
)
def poll_commands():
    denied = require_mt5_key()

    if denied:
        return denied

    account_id = str(
        request.args.get(
            "accountId",
            ""
        )
    ).strip()

    if not account_id:
        return jsonify({
            "ok": False,
            "error": "accountId is required"
        }), 400

    with lock:
        registered = authorized_accounts.get(
            account_id
        )

        if not registered or not registered.get(
            "active",
            False
        ):
            return jsonify({
                "ok": True,
                "commands": []
            })

        pending = []

        for command in commands.values():
            if (
                command["accountId"]
                == account_id
                and command["status"]
                == "PENDING"
            ):
                pending.append(
                    dict(command)
                )

                command[
                    "status"
                ] = "DELIVERED"

                command[
                    "deliveredAt"
                ] = now_iso()

                command[
                    "updatedAt"
                ] = now_iso()

        return jsonify({
            "ok": True,
            "commands": pending
        })


# ============================================================
# COMMAND ACKNOWLEDGEMENT
# ============================================================

@app.post(
    "/api/mt5/monitor/commands/<command_id>/ack"
)
def acknowledge_command(command_id):
    denied = require_mt5_key()

    if denied:
        return denied

    data = request.get_json(
        silent=True
    ) or {}

    status = str(
        data.get(
            "status",
            ""
        )
    ).strip().upper()

    if status not in {
        "COMPLETED",
        "FAILED"
    }:
        return jsonify({
            "ok": False,
            "error": "INVALID_STATUS"
        }), 400

    with lock:
        command = commands.get(
            command_id
        )

        if not command:
            return jsonify({
                "ok": False,
                "error": "COMMAND_NOT_FOUND"
            }), 404

        command[
            "status"
        ] = status

        command[
            "result"
        ] = data.get(
            "result"
        )

        command[
            "updatedAt"
        ] = now_iso()

        command[
            "acknowledgedAt"
        ] = now_iso()

        print(
            "[COMMAND ACK]",
            command_id,
            status
        )

        return jsonify({
            "ok": True,
            "command": dict(
                command
            )
        })


# ============================================================
# COMMAND HISTORY
# ============================================================

@app.get("/api/commands")
def command_history():
    denied = require_mt5_key()

    if denied:
        return denied

    account_id = str(
        request.args.get(
            "accountId",
            ""
        )
    ).strip()

    with lock:
        result = list(
            commands.values()
        )

        if account_id:
            result = [
                command
                for command in result
                if command[
                    "accountId"
                ] == account_id
            ]

        result.sort(
            key=lambda command:
                command.get(
                    "createdAt",
                    ""
                ),
            reverse=True
        )

        return jsonify({
            "ok": True,
            "commands": result[:200]
        })


# ============================================================
# LEGACY SINGLE-ACCOUNT API
# Kept temporarily so the existing dashboard does not crash
# while we replace it with the multi-account Bot Room UI.
# ============================================================

@app.get("/api/state")
def legacy_state():
    denied = require_mt5_key()

    if denied:
        return denied

    with lock:
        active = [
            public_account(account_id)
            for account_id, data
            in authorized_accounts.items()
            if data.get(
                "active",
                False
            )
        ]

        online = [
            account
            for account in active
            if account["online"]
        ]

        total_positions = sum(
            account["positionCount"]
            for account in active
        )

        return jsonify({
            "ok": True,
            "mode": "SCANNER_ONLY",
            "trading_from_dashboard": False,
            "active_accounts": len(
                active
            ),
            "online_accounts": len(
                online
            ),
            "open_positions": total_positions,
            "accounts": active,
            "updated_at": now_iso()
        })


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    host = os.getenv(
        "SAINT_HOST",
        "0.0.0.0"
    )

    port = int(
        os.getenv(
            "SAINT_PORT",
            os.getenv(
                "PORT",
                "5000"
            )
        )
    )

    print("")
    print("=" * 60)
    print("             SAINT BOT ROOM")
    print("       MT5 SCANNER + TERMINAL CONTROL")
    print("=" * 60)
    print("Firebase: DISABLED")
    print("SAINT ADMIN: DISCONNECTED")
    print(
        "Active account registry:",
        len(authorized_accounts)
    )
    print(
        f"Dashboard: http://127.0.0.1:{port}"
    )
    print(
        f"Health:    http://127.0.0.1:{port}/api/health"
    )
    print("=" * 60)
    print("")

    app.run(
        host=host,
        port=port,
        debug=False,
        threaded=True
    )

@app.delete("/api/admin/accounts/<account_id>")
def delete_account(account_id):
    denied = require_admin_key()

    if denied:
        return denied

    account_id = str(account_id).strip()

    with lock:
        if account_id not in authorized_accounts:
            return jsonify({
                "ok": False,
                "error": "ACCOUNT_NOT_REGISTERED"
            }), 404

        del authorized_accounts[account_id]
        accounts.pop(account_id, None)

        command_ids = [
            command_id
            for command_id, command in commands.items()
            if command.get("accountId") == account_id
        ]

        for command_id in command_ids:
            commands.pop(command_id, None)

        save_registry()

        print("[DELETE ACCOUNT]", account_id)

        return jsonify({
            "ok": True,
            "deletedAccount": account_id,
            "message": "Account permanently removed from SAINT BOT ROOM."
        })
