"""Shared helpers for auth, JSON, and risk mapping."""

from functools import wraps

from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from utils.constants import ROLES


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def json_error(message, status=400):
    return jsonify({"success": False, "error": message}), status


def json_ok(data=None, message=None, status=200):
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def severity_from_score(score):
    if score <= Config.RISK_LOW_MAX:
        return "LOW"
    if score <= Config.RISK_MEDIUM_MAX:
        return "MEDIUM"
    if score <= Config.RISK_HIGH_MAX:
        return "HIGH"
    return "CRITICAL"


def classification_from_score(score):
    if score <= Config.RISK_LOW_MAX:
        return "NORMAL"
    if score < Config.FRAUD_THRESHOLD:
        return "SUSPICIOUS"
    return "FRAUD"


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return json_error("Authentication required", 401)
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    allowed = set(roles) if roles else set(ROLES)

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                if request.path.startswith("/api/"):
                    return json_error("Authentication required", 401)
                return redirect(url_for("login"))
            if session.get("role") not in allowed:
                if request.path.startswith("/api/"):
                    return json_error("You do not have permission for this action", 403)
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def current_user():
    if "user_id" not in session:
        return None
    return {
        "id": session.get("user_id"),
        "username": session.get("username"),
        "role": session.get("role"),
    }
