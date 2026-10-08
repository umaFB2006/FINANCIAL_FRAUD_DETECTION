from flask import Blueprint, request, session

from database.database import query_one, write_audit
from utils.helpers import json_error, json_ok, verify_password

bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        return json_error("Username and password are required", 400)
    user = query_one("SELECT * FROM users WHERE username = ?", (username,))
    if not user or not verify_password(user["password_hash"], password):
        return json_error("Invalid username or password", 401)
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    write_audit(user["id"], "LOGIN", "users", user["id"])
    return json_ok(
        {
            "username": user["username"],
            "role": user["role"],
            "email": user["email"],
        }
    )


@bp.post("/logout")
def logout():
    user_id = session.get("user_id")
    session.clear()
    if user_id:
        write_audit(user_id, "LOGOUT", "users", user_id)
    return json_ok(message="Logged out")
