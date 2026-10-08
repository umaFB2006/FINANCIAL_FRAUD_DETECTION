# ML pipeline

1. Load `data/raw/transactions.csv` (generated if missing).
2. Clean: duplicates, invalid amounts, timestamps, categories.
3. Engineer numeric features: amount, frequency, deviation, balance ratio, international flag, unusual location/device, hour, weekday, merchant frequency, velocity.
4. Scale with `StandardScaler`.
5. Train Logistic Regression, Random Forest, Gradient Boosting; Isolation Forest on the same scaled matrix.
6. Compare Accuracy, Precision, Recall, F1, ROC-AUC, confusion matrix. **Select by F1 then ROC-AUC.**
7. Save `models/fraud_model.pkl`, `anomaly_model.pkl`, `scaler.pkl`, `feature_columns.pkl`.

Inference (`ml/predict.py`) only loads artifacts. If they are missing, a conservative heuristic is used so the UI still runs.
