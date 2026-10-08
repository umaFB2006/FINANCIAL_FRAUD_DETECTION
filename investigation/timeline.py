"""Investigation timeline events."""

from database.db import execute, fetch_all, utcnow_iso

EVENT_TYPES = (
    "INVESTIGATION_CREATED",
    "ANALYSIS_STARTED",
    "ANALYSIS_COMPLETED",
    "EVIDENCE_GENERATED",
    "STATUS_CHANGED",
    "ASSIGNED",
    "FEEDBACK_RECEIVED",
    "REPORT_GENERATED",
)


def add_event(investigation_id, event_type, description):
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown timeline event type: {event_type}")
    execute(
        """
        INSERT INTO timeline_events (investigation_id, event_type, description, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (investigation_id, event_type, description, utcnow_iso()),
    )


def list_events(investigation_id):
    return fetch_all(
        """
        SELECT * FROM timeline_events
        WHERE investigation_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (investigation_id,),
    )
