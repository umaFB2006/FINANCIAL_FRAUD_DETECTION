"""Input validation helpers."""

import ipaddress
import re

from utils.constants import PAYMENT_METHODS, TRANSACTION_TYPES

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(value):
    return bool(value and EMAIL_RE.match(str(value)))


def is_valid_ip(value):
    try:
        ipaddress.ip_address(str(value))
        return True
    except ValueError:
        return False


def validate_transaction_payload(payload):
    errors = []
    if not payload or not isinstance(payload, dict):
        return ["Request body must be a JSON object"]

    customer_id = str(payload.get("customer_id") or "").strip()
    if not customer_id:
        errors.append("customer_id is required")

    amount = payload.get("amount")
    try:
        amount = float(amount)
        if amount <= 0:
            errors.append("amount must be greater than 0")
    except (TypeError, ValueError):
        errors.append("amount must be a number")

    txn_type = str(payload.get("transaction_type") or "").strip().upper()
    if txn_type not in TRANSACTION_TYPES:
        errors.append(
            "transaction_type must be one of: " + ", ".join(TRANSACTION_TYPES)
        )

    merchant = str(payload.get("merchant") or "").strip()
    if not merchant:
        errors.append("merchant is required")

    location = str(payload.get("location") or "").strip()
    if not location:
        errors.append("location is required")

    device_id = str(payload.get("device_id") or "").strip()
    if not device_id:
        errors.append("device_id is required")

    ip_address = str(payload.get("ip_address") or "").strip()
    if not ip_address or not is_valid_ip(ip_address):
        errors.append("ip_address must be a valid IPv4 or IPv6 address")

    payment_method = str(payload.get("payment_method") or "").strip().upper()
    if payment_method not in PAYMENT_METHODS:
        errors.append("payment_method must be one of: " + ", ".join(PAYMENT_METHODS))

    try:
        balance = float(payload.get("account_balance"))
        if balance < 0:
            errors.append("account_balance cannot be negative")
    except (TypeError, ValueError):
        errors.append("account_balance must be a number")

    intl = payload.get("is_international", False)
    if not isinstance(intl, bool) and str(intl).lower() not in ("true", "false", "0", "1"):
        errors.append("is_international must be a boolean")

    return errors
