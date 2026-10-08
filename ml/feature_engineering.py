"""Feature engineering for batch training and single-transaction scoring."""

import pandas as pd

from utils.constants import NUMERIC_FEATURES


def _ensure_time(df):
    data = df.copy()
    if "transaction_time" in data.columns:
        data["transaction_time"] = pd.to_datetime(data["transaction_time"], errors="coerce")
    else:
        data["transaction_time"] = pd.Timestamp.utcnow()
    if "amount" not in data.columns:
        data["amount"] = data.get("transaction_amount", 0)
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce").fillna(0)
    data["account_balance"] = pd.to_numeric(data.get("account_balance", 0), errors="coerce").fillna(0)
    data["is_international"] = pd.to_numeric(data.get("is_international", 0), errors="coerce").fillna(0).astype(int)
    return data


def engineer_features(df):
    """Create numeric model features from a transaction dataframe."""
    data = _ensure_time(df)
    data = data.sort_values(["customer_id", "transaction_time"]) if "customer_id" in data.columns else data

    grouped_amt = data.groupby("customer_id")["amount"] if "customer_id" in data.columns else None
    if grouped_amt is not None:
        data["avg_amount"] = grouped_amt.transform(lambda s: s.expanding().mean().shift(1)).fillna(data["amount"])
        data["transaction_frequency"] = data.groupby("customer_id")["amount"].transform(
            lambda s: s.rolling(window=10, min_periods=1).count()
        )
    else:
        data["avg_amount"] = data["amount"]
        data["transaction_frequency"] = 1

    data["amount_deviation"] = (data["amount"] - data["avg_amount"]).abs() / data["avg_amount"].clip(lower=1)
    data["balance_ratio"] = data["amount"] / data["account_balance"].clip(lower=1)
    data["amount_to_balance"] = data["balance_ratio"]
    data["hour"] = data["transaction_time"].dt.hour.fillna(12)
    data["day_of_week"] = data["transaction_time"].dt.dayofweek.fillna(0)

    if "customer_id" in data.columns and "location" in data.columns:
        mode_loc = data.groupby("customer_id")["location"].transform(lambda s: s.mode().iloc[0] if len(s.mode()) else s.iloc[0])
        data["unusual_location"] = (data["location"] != mode_loc).astype(int)
    else:
        data["unusual_location"] = 0

    if "customer_id" in data.columns and "device_id" in data.columns:
        mode_dev = data.groupby("customer_id")["device_id"].transform(lambda s: s.mode().iloc[0] if len(s.mode()) else s.iloc[0])
        data["unusual_device"] = (data["device_id"] != mode_dev).astype(int)
    else:
        data["unusual_device"] = 0

    if "merchant" in data.columns and "customer_id" in data.columns:
        data["merchant_frequency"] = data.groupby(["customer_id", "merchant"])["amount"].transform("count")
    else:
        data["merchant_frequency"] = 1

    if "customer_id" in data.columns:
        counts = []
        for _, group in data.groupby("customer_id"):
            times = group["transaction_time"]
            vel = []
            for t in times:
                vel.append(((times >= t - pd.Timedelta(minutes=3)) & (times <= t)).sum())
            counts.extend(vel)
        data["velocity_count"] = counts
    else:
        data["velocity_count"] = 1

    feature_df = data[NUMERIC_FEATURES].fillna(0)
    return feature_df, data


def features_from_context(txn, history_rows):
    """Build a single-row feature vector using customer history from the database."""
    amount = float(txn.get("amount") or txn.get("transaction_amount") or 0)
    balance = float(txn.get("account_balance") or 0)
    history = list(history_rows or [])
    hist_amounts = [float(r.get("transaction_amount") or 0) for r in history]
    avg_amount = sum(hist_amounts) / len(hist_amounts) if hist_amounts else amount
    locations = [r.get("location") for r in history if r.get("location")]
    devices = [r.get("device_id") for r in history if r.get("device_id")]
    merchants = [r.get("merchant") for r in history if r.get("merchant")]

    ts = pd.to_datetime(txn.get("transaction_time") or pd.Timestamp.utcnow())
    recent = 0
    window_start = ts - pd.Timedelta(minutes=3)
    for r in history:
        ht = pd.to_datetime(r.get("transaction_time"))
        if window_start <= ht <= ts:
            recent += 1
    recent += 1

    unusual_location = 1 if locations and txn.get("location") not in set(locations) else 0
    unusual_device = 1 if devices and txn.get("device_id") not in set(devices) else 0
    merchant_frequency = merchants.count(txn.get("merchant")) + 1
    intl = txn.get("is_international")
    if isinstance(intl, str):
        intl = 1 if intl.lower() in ("1", "true") else 0
    intl = int(bool(intl))

    row = {
        "amount": amount,
        "transaction_frequency": max(len(history), 1),
        "avg_amount": avg_amount,
        "amount_deviation": abs(amount - avg_amount) / max(avg_amount, 1),
        "balance_ratio": amount / max(balance, 1),
        "is_international": intl,
        "unusual_location": unusual_location,
        "unusual_device": unusual_device,
        "hour": int(ts.hour),
        "day_of_week": int(ts.dayofweek),
        "merchant_frequency": merchant_frequency,
        "velocity_count": recent,
        "amount_to_balance": amount / max(balance, 1),
    }
    return row
