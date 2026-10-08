"""End-to-end new-transaction fraud detection pipeline."""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone

from config import Config
from database.db import execute, fetch_all, fetch_one, utcnow_iso
from investigation.investigator import create_alert, create_investigation
from ml.behaviour_profiler import build_profile, calculate_behavior_score
from ml.explainer import explain_transaction
from ml.fraud_detector import get_detector
from ml.preprocessing import normalize_type, to_int_flag
from ml.risk_engine import calculate_final_risk, calculate_rule_score


def generate_transaction_id():
    suffix = "".join(random.choices(string.digits, k=8))
    return f"TXN{suffix}"


def load_user_history(user_id, exclude_transaction_id=None):
    if exclude_transaction_id:
        return fetch_all(
            """
            SELECT * FROM transactions
            WHERE user_id = ? AND transaction_id != ?
            ORDER BY datetime(created_at) ASC, id ASC
            """,
            (user_id, exclude_transaction_id),
        )
    return fetch_all(
        """
        SELECT * FROM transactions
        WHERE user_id = ?
        ORDER BY datetime(created_at) ASC, id ASC
        """,
        (user_id,),
    )


def validate_transaction_payload(data):
    errors = []
    amount = data.get("amount")
    try:
        amount = float(amount)
        if amount <= 0:
            errors.append("Amount must be greater than zero.")
    except (TypeError, ValueError):
        errors.append("Amount must be a valid number.")
        amount = None

    transaction_id = str(data.get("transaction_id") or "").strip()
    if transaction_id and fetch_one(
        "SELECT id FROM transactions WHERE transaction_id = ?", (transaction_id,)
    ):
        errors.append("Transaction ID must be unique.")

    required = {
        "transaction_type": "Transaction type",
        "beneficiary": "Beneficiary",
        "location": "Location",
        "device_id": "Device ID",
        "ip_address": "IP address",
        "transaction_time": "Transaction time",
    }
    for field, label in required.items():
        if not str(data.get(field) or "").strip():
            errors.append(f"{label} is required.")

    return errors, amount


def _insert_transaction(user_id, payload):
    txn_id = str(payload.get("transaction_id") or "").strip() or generate_transaction_id()
    while fetch_one("SELECT id FROM transactions WHERE transaction_id = ?", (txn_id,)):
        txn_id = generate_transaction_id()
    pk = execute(
        """
        INSERT INTO transactions (
            transaction_id, user_id, amount, transaction_type, beneficiary, location,
            device_id, ip_address, transaction_time, is_international, is_new_device,
            is_new_beneficiary, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            txn_id,
            user_id,
            float(payload["amount"]),
            normalize_type(payload.get("transaction_type")),
            str(payload.get("beneficiary")).strip(),
            str(payload.get("location")).strip(),
            str(payload.get("device_id")).strip(),
            str(payload.get("ip_address")).strip(),
            str(payload.get("transaction_time")).strip(),
            to_int_flag(payload.get("is_international")),
            to_int_flag(payload.get("is_new_device")),
            to_int_flag(payload.get("is_new_beneficiary")),
            "PENDING_ANALYSIS",
            utcnow_iso(),
        ),
    )
    return fetch_one("SELECT * FROM transactions WHERE id = ?", (pk,))


def _create_otp(transaction_id):
    code = f"{random.randint(0, 999999):06d}"
    expires = datetime.now(timezone.utc) + timedelta(seconds=Config.OTP_EXPIRY_SECONDS)
    execute(
        """
        INSERT INTO otp_verifications (transaction_id, otp_code, expires_at, verified, created_at)
        VALUES (?, ?, ?, 0, ?)
        """,
        (transaction_id, code, expires.isoformat(), utcnow_iso()),
    )
    return code, expires.isoformat()


def process_new_transaction(user_id, payload):
    """
    USER ENTERS TRANSACTION
      -> validation
      -> save
      -> load history
      -> behavior profile
      -> ML
      -> rules
      -> behavior anomaly
      -> hybrid risk
      -> explanation / action
      -> save result
      -> OTP / investigation
    """
    errors, amount = validate_transaction_payload(payload)
    if errors:
        return {"ok": False, "errors": errors}

    payload = dict(payload)
    payload["amount"] = amount
    saved = _insert_transaction(user_id, payload)
    history = load_user_history(user_id, exclude_transaction_id=saved["transaction_id"])
    profile = build_profile(history)

    ml_result = get_detector().predict(saved)
    rule_score = calculate_rule_score(saved)
    behavior_score, behavior_reasons = calculate_behavior_score(saved, profile)
    risk_score, risk_level, action = calculate_final_risk(
        ml_result["ml_score"], rule_score, behavior_score
    )
    reasons = explain_transaction(
        saved, ml_result, rule_score, behavior_score, behavior_reasons, profile
    )
    explanation = "\n".join(f"- {reason}" for reason in reasons)

    if risk_level == "LOW":
        status = "AUTO_APPROVED"
        prediction = "LEGITIMATE"
    elif risk_level == "MEDIUM":
        status = "PENDING_OTP"
        prediction = "SUSPICIOUS"
    else:
        status = "UNDER_INVESTIGATION"
        prediction = "FRAUD"

    execute(
        """
        UPDATE transactions
        SET ml_score = ?, rule_score = ?, behavior_score = ?, risk_score = ?,
            risk_level = ?, status = ?, prediction = ?, explanation = ?,
            recommended_action = ?
        WHERE id = ?
        """,
        (
            ml_result["ml_score"],
            rule_score,
            behavior_score,
            risk_score,
            risk_level,
            status,
            prediction,
            explanation,
            action,
            saved["id"],
        ),
    )
    result = fetch_one("SELECT * FROM transactions WHERE id = ?", (saved["id"],))

    otp_code = None
    investigation = None
    if risk_level == "MEDIUM":
        otp_code, _expires = _create_otp(result["transaction_id"])
        create_alert(
            result["transaction_id"],
            "MEDIUM",
            f"Additional verification required for {result['transaction_id']}.",
        )
    elif risk_level == "HIGH":
        investigation = create_investigation(result, history, ml_result, behavior_reasons)
        create_alert(
            result["transaction_id"],
            "HIGH",
            f"High-risk transaction {result['transaction_id']} sent to investigation.",
        )

    return {
        "ok": True,
        "transaction": result,
        "profile": profile,
        "reasons": reasons,
        "otp_code": otp_code,
        "investigation": investigation,
        "ml": ml_result,
    }


def verify_otp(transaction_id, submitted_code):
    txn = fetch_one("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    if not txn:
        return False, "Transaction not found."
    row = fetch_one(
        """
        SELECT * FROM otp_verifications
        WHERE transaction_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (transaction_id,),
    )
    if not row:
        return False, "No OTP was issued for this transaction."
    if row["verified"]:
        return False, "OTP was already used."
    now = datetime.now(timezone.utc)
    expires = datetime.fromisoformat(row["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        return False, "OTP has expired."
    if str(submitted_code).strip() != str(row["otp_code"]):
        return False, "Invalid OTP."
    execute("UPDATE otp_verifications SET verified = 1 WHERE id = ?", (row["id"],))
    execute(
        "UPDATE transactions SET status = ? WHERE transaction_id = ?",
        ("VERIFIED", transaction_id),
    )
    return True, "OTP verified. Transaction marked as VERIFIED."
