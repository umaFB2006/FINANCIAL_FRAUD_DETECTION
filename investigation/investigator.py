"""Create and manage autonomous investigations."""

from database.db import execute, fetch_all, fetch_one, utcnow_iso
from investigation.evidence_generator import build_evidence_items, persist_evidence
from investigation.summary_generator import generate_recommendation, generate_summary
from investigation.timeline import add_event
from investigation.transaction_analyzer import analyze

VALID_STATUSES = {
    "OPEN",
    "INVESTIGATING",
    "RESOLVED",
    "FALSE_POSITIVE",
    "CONFIRMED_FRAUD",
}


def create_investigation(txn, history, ml_result, behavior_reasons):
    existing = fetch_one(
        "SELECT * FROM investigations WHERE transaction_id = ?",
        (txn["transaction_id"],),
    )
    if existing:
        return existing

    now = utcnow_iso()
    analysis = analyze(txn, history)
    evidence_items = build_evidence_items(txn, ml_result, behavior_reasons)
    summary = generate_summary(txn, analysis, evidence_items)
    recommendation = generate_recommendation(txn.get("risk_level"))

    investigation_id = execute(
        """
        INSERT INTO investigations (
            transaction_pk, transaction_id, user_id, assigned_to, status,
            summary, recommendation, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            txn.get("id"),
            txn["transaction_id"],
            txn.get("user_id"),
            None,
            "OPEN",
            summary,
            recommendation,
            now,
            now,
        ),
    )
    add_event(investigation_id, "INVESTIGATION_CREATED", "Autonomous investigation opened for high-risk transaction.")
    add_event(investigation_id, "ANALYSIS_STARTED", "Historical transaction analysis started.")
    add_event(
        investigation_id,
        "ANALYSIS_COMPLETED",
        f"Analysis completed. History size={analysis['history_count']}.",
    )
    persist_evidence(investigation_id, evidence_items)
    add_event(investigation_id, "EVIDENCE_GENERATED", f"{len(evidence_items)} evidence item(s) recorded.")
    return fetch_one("SELECT * FROM investigations WHERE id = ?", (investigation_id,))


def create_alert(transaction_id, severity, message):
    existing = fetch_one(
        "SELECT * FROM alerts WHERE transaction_id = ? AND message = ?",
        (transaction_id, message),
    )
    if existing:
        return existing
    alert_id = execute(
        """
        INSERT INTO alerts (transaction_id, severity, message, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (transaction_id, severity, message, "OPEN", utcnow_iso()),
    )
    return fetch_one("SELECT * FROM alerts WHERE id = ?", (alert_id,))


def update_status(investigation_id, status, actor_name="system"):
    if status not in VALID_STATUSES:
        raise ValueError("Invalid investigation status")
    execute(
        "UPDATE investigations SET status = ?, updated_at = ? WHERE id = ?",
        (status, utcnow_iso(), investigation_id),
    )
    add_event(investigation_id, "STATUS_CHANGED", f"Status changed to {status} by {actor_name}.")
    return fetch_one("SELECT * FROM investigations WHERE id = ?", (investigation_id,))


def assign_investigation(investigation_id, user_id, actor_name="system"):
    execute(
        "UPDATE investigations SET assigned_to = ?, status = CASE WHEN status = 'OPEN' THEN 'INVESTIGATING' ELSE status END, updated_at = ? WHERE id = ?",
        (user_id, utcnow_iso(), investigation_id),
    )
    add_event(investigation_id, "ASSIGNED", f"Assigned to user id {user_id} by {actor_name}.")
    return fetch_one("SELECT * FROM investigations WHERE id = ?", (investigation_id,))


def add_feedback(investigation_id, user_id, comment):
    execute(
        "INSERT INTO feedback (investigation_id, user_id, comment, created_at) VALUES (?, ?, ?, ?)",
        (investigation_id, user_id, comment, utcnow_iso()),
    )
    add_event(investigation_id, "FEEDBACK_RECEIVED", "Investigator feedback recorded.")
    return fetch_all(
        "SELECT * FROM feedback WHERE investigation_id = ? ORDER BY created_at ASC",
        (investigation_id,),
    )
