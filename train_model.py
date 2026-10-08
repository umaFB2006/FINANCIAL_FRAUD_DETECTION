"""Generate synthetic data and train a fraud classifier."""

from __future__ import annotations

import random
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from config import Config
from ml.preprocessing import FEATURE_COLUMNS, features_to_row, transaction_to_features

try:
    from xgboost import XGBClassifier

    HAS_XGBOOST = True
except Exception:
    HAS_XGBOOST = False

TYPES = ["TRANSFER", "WITHDRAWAL", "DEPOSIT", "PAYMENT", "UPI"]
LOCATIONS = ["Hyderabad", "Mumbai", "Delhi", "Bengaluru", "Chennai", "Pune"]
BENEFICIARIES = ["ABC", "Rahul", "Priya", "Merchant_01", "UtilityCo", "Family"]


def _synthetic_row(i, fraud=False):
    if fraud:
        amount = random.choice([25000, 48000, 75000, 120000, 180000, 250000])
        international = random.choice([1, 1, 1, 0])
        new_device = random.choice([1, 1, 0])
        new_ben = random.choice([1, 1, 0])
        hour = random.choice([1, 2, 3, 4, 23, 0, 14])
        status = random.choice(["COMPLETED", "FAILED", "COMPLETED"])
    else:
        amount = random.choice([400, 500, 800, 900, 1200, 1500, 2200, 3500, 5000])
        international = 0 if random.random() > 0.08 else 1
        new_device = 0 if random.random() > 0.1 else 1
        new_ben = 0 if random.random() > 0.12 else 1
        hour = random.randint(9, 20)
        status = "COMPLETED"
    ampm = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    txn = {
        "transaction_id": f"SYN{i:06d}",
        "amount": amount,
        "transaction_type": random.choice(TYPES),
        "beneficiary": random.choice(BENEFICIARIES),
        "location": random.choice(LOCATIONS),
        "device_id": f"DEVICE_{random.randint(1, 40):02d}",
        "ip_address": f"192.168.{random.randint(0, 3)}.{random.randint(2, 250)}",
        "transaction_time": f"{display_hour:02d}:{random.randint(0, 59):02d} {ampm}",
        "is_international": international,
        "is_new_device": new_device,
        "is_new_beneficiary": new_ben,
        "status": status,
        "fraud": int(fraud),
    }
    return txn


def generate_dataset(n_legit=4000, n_fraud=1200, path=None):
    rows = [_synthetic_row(i, fraud=False) for i in range(n_legit)]
    rows += [_synthetic_row(n_legit + i, fraud=True) for i in range(n_fraud)]
    random.shuffle(rows)
    df = pd.DataFrame(rows)
    out = Path(path or Config.DATA_CSV_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return df


def train(df=None):
    if df is None:
        csv_path = Config.DATA_CSV_PATH
        if csv_path.exists():
            df = pd.read_csv(csv_path)
        else:
            df = generate_dataset()

    X = []
    y = []
    for _, row in df.iterrows():
        features = transaction_to_features(row.to_dict())
        X.append(features_to_row(features))
        y.append(int(row["fraud"]))
    X = np.array(X, dtype=float)
    y = np.array(y, dtype=int)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    if HAS_XGBOOST:
        model = XGBClassifier(
            n_estimators=120,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            n_jobs=1,
            random_state=42,
        )
        backend = "xgboost"
    else:
        model = RandomForestClassifier(
            n_estimators=180,
            max_depth=12,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=1,
        )
        backend = "random_forest"

    model.fit(X_train, y_train)
    acc = float((model.predict(X_test) == y_test).mean())
    Config.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, Config.MODEL_PATH)
    joblib.dump({"scaler": scaler, "columns": FEATURE_COLUMNS, "backend": backend}, Config.PREPROCESSOR_PATH)
    print(f"Trained {backend} accuracy={acc:.3f} samples={len(df)}")
    print(f"Saved {Config.MODEL_PATH}")
    print(f"Saved {Config.PREPROCESSOR_PATH}")
    return acc


if __name__ == "__main__":
    df = generate_dataset()
    train(df)
