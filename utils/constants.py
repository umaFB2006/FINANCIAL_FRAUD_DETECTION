ROLES = ("ADMIN", "INVESTIGATOR")

PREDICTION_LABELS = ("NORMAL", "SUSPICIOUS", "FRAUD")

SEVERITY_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

CASE_STATUSES = (
    "OPEN",
    "UNDER_REVIEW",
    "ESCALATED",
    "RESOLVED",
    "FALSE_POSITIVE",
)

FINAL_DECISIONS = ("FRAUD_CONFIRMED", "FALSE_POSITIVE", "NEEDS_MORE_REVIEW")

RECOMMENDATIONS = (
    "MONITOR",
    "REQUEST_VERIFICATION",
    "TEMPORARILY_HOLD",
    "ESCALATE_TO_INVESTIGATOR",
)

TRANSACTION_TYPES = (
    "TRANSFER",
    "PAYMENT",
    "WITHDRAWAL",
    "DEPOSIT",
    "UPI_PAYMENT",
)

PAYMENT_METHODS = ("UPI", "CARD", "NETBANKING", "WALLET")

ALERT_STATUSES = ("OPEN", "ACKNOWLEDGED", "RESOLVED")

NUMERIC_FEATURES = [
    "amount",
    "transaction_frequency",
    "avg_amount",
    "amount_deviation",
    "balance_ratio",
    "is_international",
    "unusual_location",
    "unusual_device",
    "hour",
    "day_of_week",
    "merchant_frequency",
    "velocity_count",
    "amount_to_balance",
]
