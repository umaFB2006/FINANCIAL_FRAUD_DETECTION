"""Format and compare classification metrics."""


def format_metrics(name, metrics):
    lines = [
        f"\n{name}",
        f"Accuracy : {metrics.get('accuracy', 0):.4f}",
        f"Precision: {metrics.get('precision', 0):.4f}",
        f"Recall   : {metrics.get('recall', 0):.4f}",
        f"F1 Score : {metrics.get('f1', 0):.4f}",
        f"ROC-AUC  : {metrics.get('roc_auc', 0):.4f}",
        f"Confusion: {metrics.get('confusion_matrix')}",
    ]
    return "\n".join(lines)


def pick_best(results):
    return max(results.items(), key=lambda kv: (kv[1].get("f1", 0), kv[1].get("roc_auc", 0)))
