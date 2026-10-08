"""SQLite access layer. Swap engine later for PostgreSQL/MySQL by replacing this module."""

import sqlite3
from pathlib import Path

from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection(db_path=None):
    path = db_path or Config.DATABASE_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    conn = get_connection(db_path)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    conn.close()
    logger.info("Database initialized at %s", db_path or Config.DATABASE_PATH)


def query_all(sql, params=(), db_path=None):
    conn = get_connection(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_one(sql, params=(), db_path=None):
    conn = get_connection(db_path)
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def execute(sql, params=(), db_path=None):
    conn = get_connection(db_path)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def execute_many(sql, rows, db_path=None):
    conn = get_connection(db_path)
    try:
        conn.executemany(sql, rows)
        conn.commit()
    finally:
        conn.close()


def write_audit(user_id, action, entity=None, entity_id=None, db_path=None):
    execute(
        """
        INSERT INTO audit_logs (user_id, action, entity, entity_id)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, action, entity, str(entity_id) if entity_id is not None else None),
        db_path=db_path,
    )
