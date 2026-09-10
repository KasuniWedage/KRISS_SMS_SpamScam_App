"""Evaluate the deployed model on an independently supplied labeled CSV.

Required columns: message,label,language. The script never trains on this
file, making it suitable for a final held-out or consented real-world set.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ml_service import ml_service  # noqa: E402


def evaluate(csv_path: Path) -> dict:
    frame = pd.read_csv(csv_path)
    required = {"message", "label", "language"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    if not ml_service.ready:
        raise RuntimeError("Model artifact is not loaded")
    predictions = []
    durations = []
    for message in frame["message"].astype(str):
        started = time.perf_counter()
        predictions.append(ml_service.predict(message)[0])
        durations.append((time.perf_counter() - started) * 1000)
    frame = frame.assign(prediction=predictions)

    def metrics(part: pd.DataFrame) -> dict:
        labels = ["Legitimate", "Spam", "Scam"]
        return {
            "rows": len(part),
            "accuracy": round(float(accuracy_score(part.label, part.prediction)), 6),
            "classification_report": classification_report(part.label, part.prediction, labels=labels, output_dict=True, zero_division=0),
            "confusion_matrix": confusion_matrix(part.label, part.prediction, labels=labels).tolist(),
            "labels": labels,
        }

    ordered = sorted(durations)
    report = metrics(frame)
    report["by_language"] = {str(language): metrics(group) for language, group in frame.groupby("language")}
    report["latency_ms"] = {
        "average": round(sum(durations) / len(durations), 3) if durations else 0.0,
        "p95": round(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))], 3) if ordered else 0.0,
        "maximum": round(max(durations), 3) if durations else 0.0,
    }
    report["dataset"] = str(csv_path)
    report["model_version"] = ml_service.metadata.get("model_version", "unknown")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.csv)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
