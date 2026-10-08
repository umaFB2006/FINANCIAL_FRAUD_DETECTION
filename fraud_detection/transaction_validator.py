"""Validate incoming transaction API payloads."""

from utils.validators import validate_transaction_payload


def validate_transaction(payload):
    errors = validate_transaction_payload(payload)
    return {"valid": not errors, "errors": errors}
