"""Password hashing, session helpers, and role checks."""

from __future__ import annotations

import re
from functools import wraps

from flask import flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import execute, fetch_one, utcnow_iso

ROLES = ("USER", "INVESTIGATOR", "ADMIN")
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def validate_password_strength(password):
    if not password or not PASSWORD_PATTERN.match(password):
        return False, "Password must be at least 8 characters and include upper, lower, digit, and special character."
    return True, ""


def create_user(email, password, full_name, role="USER"):
    ok, message = validate_password_strength(password)
    if not ok:
        raise ValueError(message)
    role = role.upper()
    if role not in ROLES:
        raise ValueError("Invalid role")
    existing = fetch_one("SELECT id FROM users WHERE email = ?", (email.lower().strip(),))
    if existing:
        raise ValueError("An account with this email already exists.")
    user_id = execute(
        """
        INSERT INTO users (email, password_hash, full_name, role, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (email.lower().strip(), hash_password(password), full_name.strip(), role, utcnow_iso()),
    )
    return fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))


def authenticate(email, password):
    user = fetch_one("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    if not user or not verify_password(user["password_hash"], password):
        return None
    return user


def login_user_session(user):
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["email"] = user["email"]
    session["full_name"] = user["full_name"]


def logout_user_session():
    session.clear()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return fetch_one("SELECT id, email, full_name, role, created_at FROM users WHERE id = ?", (user_id,))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You are not authorized to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator
