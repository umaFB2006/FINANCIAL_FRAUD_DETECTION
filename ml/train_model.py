"""Train, compare, and persist fraud detection models."""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from ml.feature_engineering import engineer_features  # noqa: E402
from ml.model_evaluation import format_metrics  # noqa: E402
from ml.preprocessing import load_transactions_csv  # noqa: E402
from utils.constants import NUMERIC_FEATURES  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def _metrics(y_true, y_pred, y_prob):
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }
    try:
        out["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    except ValueError:
        out["roc_auc"] = 0.0
    return out


def ensure_training_csv():
    csv_path = ROOT / "data" / "raw" / "transactions.csv"
    if csv_path.exists():
        return csv_path
    from database.seed import generate_customers, generate_transactions, write_csv

    customers = generate_customers()
    df = generate_transactions(customers)
    write_csv(df, csv_path)
    write_csv(df.head(50), ROOT / "data" / "sample" / "sample_transactions.csv")
    return csv_path


def train(csv_path=None):
    csv_path = Path(csv_path) if csv_path else ensure_training_csv()
    raw = load_transactions_csv(csv_path)
    features, enriched = engineer_features(raw)
    y = enriched["actual_label"].astype(int) if "actual_label" in enriched.columns else pd.Series([0] * len(enriched))

    processed_path = ROOT / "data" / "processed" / "processed_transactions.csv"
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([enriched.reset_index(drop=True), features.reset_index(drop=True)], axis=1).to_csv(
        processed_path, index=False
    )

    X = features[NUMERIC_FEATURES].astype(float)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    strat = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.25, random_state=42, stratify=strat
    )

    candidates = {
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(
            n_estimators=120, random_state=42, class_weight="balanced", n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
    }

    results = {}
    fitted = {}
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        if hasattr(model, "predict_proba"):
            prob = model.predict_proba(X_test)[:, 1]
        else:
            prob = pred
        results[name] = _metrics(y_test, pred, prob)
        fitted[name] = model
        print(format_metrics(name, results[name]))

    def rank(item):
        name, m = item
        return (m["f1"], m["roc_auc"], m["recall"])

    best_name, best_metrics = max(results.items(), key=rank)
    best_model = fitted[best_name]
    print(f"\nSelected model: {best_name} (F1={best_metrics['f1']:.3f}, ROC-AUC={best_metrics['roc_auc']:.3f})")

    iso = IsolationForest(n_estimators=100, contamination=0.12, random_state=42)
    iso.fit(X_train)

    Config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, Config.FRAUD_MODEL_PATH)
    joblib.dump(iso, Config.ANOMALY_MODEL_PATH)
    joblib.dump(scaler, Config.SCALER_PATH)
    joblib.dump(NUMERIC_FEATURES, Config.FEATURE_COLUMNS_PATH)
    joblib.dump({"name": best_name, "metrics": results}, Config.MODEL_META_PATH)
    logger.info("Saved models to %s", Config.MODEL_DIR)
    return {"selected": best_name, "metrics": results}


if __name__ == "__main__":
    train()
