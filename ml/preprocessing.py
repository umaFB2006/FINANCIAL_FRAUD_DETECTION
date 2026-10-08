"""Shared feature extraction for training and live inference."""

from __future__ import annotations

import math
import re
from datetime import datetime

TRANSACTION_TYPES = ["TRANSFER", "WITHDRAWAL", "DEPOSIT", "PAYMENT", "UPI"]
FEATURE_COLUMNS = [
    "amount",
    "log_amount",
    "is_international",
    "is_new_device",
    "is_new_beneficiary",
    "hour",
    "is_night",
    "type_TRANSFER",
    "type_WITHDRAWAL",
    "type_DEPOSIT",
    "type_PAYMENT",
    "type_UPI",
]


def parse_hour(transaction_time):
    """Parse hour (0-23) from several human and ISO time formats."""
    if transaction_time is None:
        return 12
    text = str(transaction_time).strip()
    if not text:
        return 12

    match = re.match(r"^(\d{1,2}):(\d{2})\s*([APap][Mm])$", text)
    if match:
        hour = int(match.group(1)) % 12
        if match.group(3).upper() == "PM":
            hour += 12
        return hour

    match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", text)
    if match:
        return int(match.group(1)) % 24

    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%H:%M:%S",
        "%H:%M",
    ):
        try:
            cleaned = text.replace("Z", "+00:00")
            if fmt.startswith("%Y") and "T" in cleaned and "+" in cleaned[-6:]:
                dt = datetime.fromisoformat(cleaned)
                return dt.hour
            dt = datetime.strptime(text[:19] if len(text) >= 19 else text, fmt)
            return dt.hour
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).hour
    except ValueError:
        return 12


def to_int_flag(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value != 0)
    text = str(value).strip().lower()
    return int(text in {"1", "true", "yes", "y", "on"})


def normalize_type(value):
    text = str(value or "TRANSFER").strip().upper()
    return text if text in TRANSACTION_TYPES else "TRANSFER"


def transaction_to_features(txn):
    amount = float(txn.get("amount") or 0)
    hour = parse_hour(txn.get("transaction_time"))
    txn_type = normalize_type(txn.get("transaction_type"))
    features = {
        "amount": amount,
        "log_amount": math.log1p(max(amount, 0)),
        "is_international": to_int_flag(txn.get("is_international")),
        "is_new_device": to_int_flag(txn.get("is_new_device")),
        "is_new_beneficiary": to_int_flag(txn.get("is_new_beneficiary")),
        "hour": hour,
        "is_night": int(hour < 6 or hour >= 23),
    }
    for name in TRANSACTION_TYPES:
        features[f"type_{name}"] = int(txn_type == name)
    return features


def features_to_row(features):
    return [features[col] for col in FEATURE_COLUMNS]
