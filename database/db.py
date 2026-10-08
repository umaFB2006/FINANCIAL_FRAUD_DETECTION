"""SQLite helpers using parameterized SQL only."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import get_database_path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'USER',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    transaction_type TEXT NOT NULL,
    beneficiary TEXT NOT NULL,
    location TEXT NOT NULL,
    device_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    transaction_time TEXT NOT NULL,
    is_international INTEGER NOT NULL DEFAULT 0,
    is_new_device INTEGER NOT NULL DEFAULT 0,
    is_new_beneficiary INTEGER NOT NULL DEFAULT 0,
    ml_score REAL,
    rule_score REAL,
    behavior_score REAL,
    risk_score REAL,
    risk_level TEXT,
    status TEXT,
    prediction TEXT,
    explanation TEXT,
    recommended_action TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_pk INTEGER,
    transaction_id TEXT NOT NULL,
    user_id INTEGER,
    assigned_to INTEGER,
    status TEXT NOT NULL DEFAULT 'OPEN',
    summary TEXT,
    recommendation TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL,
    evidence_type TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id)
);

CREATE TABLE IF NOT EXISTS otp_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    comment TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (investigation_id) REFERENCES investigations(id)
);
"""


def utcnow_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection(db_path=None):
    path = get_database_path(db_path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def fetch_one(query, params=(), db_path=None):
    conn = get_connection(db_path)
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_all(query, params=(), db_path=None):
    conn = get_connection(db_path)
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def execute(query, params=(), db_path=None):
    conn = get_connection(db_path)
    try:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
