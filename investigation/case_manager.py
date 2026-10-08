"""Create and update investigation cases (simulation only)."""

import json
from datetime import datetime

from database.database import execute, query_one, write_audit
from utils.constants import CASE_STATUSES, FINAL_DECISIONS


def next_case_id():
    year = datetime.now().year
    row = query_one(
        "SELECT COUNT(*) AS n FROM investigations WHERE investigation_id LIKE ?",
        (f"CASE-{year}-%",),
    )
    n = int(row["n"] if row else 0) + 1
    return f"CASE-{year}-{n:04d}"


def create_case(transaction_id, alert_id, summary, evidence, recommendation, investigator="SYSTEM"):
    existing = query_one(
        "SELECT investigation_id FROM investigations WHERE transaction_id = ?",
        (transaction_id,),
    )
    if existing:
        return existing["investigation_id"]

    case_id = next_case_id()
    execute(
        """
        INSERT INTO investigations (
            investigation_id, transaction_id, alert_id, investigator,
            case_status, investigation_summary, evidence, recommendation
        ) VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?)
        """,
        (
            case_id,
            transaction_id,
            alert_id,
            investigator,
            summary,
            json.dumps(evidence),
            recommendation,
        ),
    )
    add_event(case_id, "CREATED", "Autonomous investigation case opened")
    write_audit(None, "CREATE_INVESTIGATION", "investigations", case_id)
    return case_id


def add_event(investigation_id, event_type, description):
    execute(
        """
        INSERT INTO investigation_events (investigation_id, event_type, description)
        VALUES (?, ?, ?)
        """,
        (investigation_id, event_type, description),
    )


def get_case(investigation_id):
    case = query_one("SELECT * FROM investigations WHERE investigation_id = ?", (investigation_id,))
    if not case:
        return None
    case["events"] = query_events(investigation_id)
    try:
        case["evidence"] = json.loads(case["evidence"] or "[]")
    except json.JSONDecodeError:
        case["evidence"] = [case["evidence"]]
    return case


def query_events(investigation_id):
    from database.database import query_all

    return query_all(
        """
        SELECT * FROM investigation_events
        WHERE investigation_id = ?
        ORDER BY timestamp ASC
        """,
        (investigation_id,),
    )


def update_case(investigation_id, status=None, notes=None, decision=None, user_id=None, investigator=None):
    case = query_one("SELECT * FROM investigations WHERE investigation_id = ?", (investigation_id,))
    if not case:
        return None
    new_status = status or case["case_status"]
    if new_status not in CASE_STATUSES:
        raise ValueError("Invalid case status")
    summary = case["investigation_summary"] or ""
    if notes:
        summary = (summary + "\nInvestigator notes: " + notes).strip()
    if decision:
        if decision not in FINAL_DECISIONS:
            raise ValueError("Invalid final decision")
        summary = (summary + f"\nFinal decision: {decision}").strip()
        if decision == "FALSE_POSITIVE":
            new_status = "FALSE_POSITIVE"
        elif decision == "FRAUD_CONFIRMED":
            new_status = "RESOLVED"

    execute(
        """
        UPDATE investigations
        SET case_status = ?, investigation_summary = ?, investigator = COALESCE(?, investigator),
            updated_at = datetime('now')
        WHERE investigation_id = ?
        """,
        (new_status, summary, investigator, investigation_id),
    )
    add_event(investigation_id, "UPDATED", f"Status={new_status}; decision={decision or 'n/a'}")
    write_audit(user_id, "UPDATE_INVESTIGATION", "investigations", investigation_id)
    return get_case(investigation_id)
