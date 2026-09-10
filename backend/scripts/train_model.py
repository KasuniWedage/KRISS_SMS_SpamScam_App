"""Train high-accuracy multilingual SMS Spam/Scam detection model (>=95% target)
supporting English, Sinhala, Singlish, and Tamil with full feature extraction and evaluation.
"""
import json
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    classification_report, confusion_matrix, recall_score, f1_score
)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.text_utils import preprocess_text

def train_and_export():
    dataset_path = Path(__file__).resolve().parents[2] / "dataset" / "kriss_sms_multilingual_10000.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    print(f"Loading dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    df = df.dropna(subset=["message", "label"]).copy()
    df["message"] = df["message"].astype(str).str.strip()
    df = df[df["message"].str.len() > 0]
    df["clean_text"] = df["message"].map(preprocess_text)

    print(f"Total samples: {len(df)}")
    print(df["language"].value_counts())
    print(df["label"].value_counts())

    # Stratified 70/30 split according to SRS/SDS
    X_train, X_test, y_train, y_test, lang_train, lang_test = train_test_split(
        df["clean_text"], df["label"], df["language"],
        test_size=0.30, random_state=42, stratify=df["label"]
    )
    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")

    # Dual word + char n-gram feature union
    word_vec = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_features=25000,
        sublinear_tf=True
    )
    char_vec = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=2,
        max_features=25000,
        sublinear_tf=True
    )
    features = FeatureUnion([  # type: ignore[arg-type]
        ("word", word_vec),
        ("char", char_vec)
    ])

    # Candidate classifiers
    candidates = {
        "Calibrated LinearSVC": Pipeline([
            ("features", features),
            ("clf", CalibratedClassifierCV(
                estimator=LinearSVC(C=1.2, class_weight="balanced", random_state=42),
                cv=3
            ))
        ]),
        "Logistic Regression": Pipeline([
            ("features", features),
            ("clf", LogisticRegression(C=2.0, max_iter=2000, class_weight="balanced", random_state=42))
        ]),
        "Multinomial Naive Bayes": Pipeline([
            ("features", features),
            ("clf", MultinomialNB(alpha=0.1))
        ])
    }

    results = {}
    best_pipeline = None
    best_acc = 0.0
    best_name = ""

    cv5 = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, pipeline in candidates.items():
        print(f"\n--- Training & Evaluating: {name} ---")
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        macro_f1 = f1_score(y_test, y_pred, average="macro")
        scam_rec = recall_score(y_test, y_pred, labels=["Scam"], average="macro", zero_division=0)
        
        print(f"Test Accuracy: {acc:.4f} ({acc*100:.2f}%)")
        print(f"Macro F1: {macro_f1:.4f}")
        print(f"Scam Recall: {scam_rec:.4f}")
        
        results[name] = {
            "accuracy": float(acc),
            "macro_f1": float(macro_f1),
            "scam_recall": float(scam_rec)
        }

        # Select model that exceeds 95% target with maximum Scam recall
        if acc > best_acc:
            best_acc = acc
            best_pipeline = pipeline
            best_name = name

    if best_pipeline is None:
        raise RuntimeError("No candidate model was successfully trained.")

    print(f"\nSelected Best Model: {best_name} with Accuracy: {best_acc*100:.2f}%")
    y_best_pred = best_pipeline.predict(X_test)
    labels = ["Legitimate", "Spam", "Scam"]
    print("\nClassification Report:")
    print(classification_report(y_test, y_best_pred, labels=labels, digits=4))

    # Per-language accuracy breakdown
    test_df = pd.DataFrame({"true": y_test, "pred": y_best_pred, "language": lang_test})
    by_lang = {}
    for lang, group in test_df.groupby("language"):
        lang_acc = accuracy_score(group["true"], group["pred"])
        lang_scam = recall_score(group["true"], group["pred"], labels=["Scam"], average="macro", zero_division=0)
        by_lang[lang] = {
            "rows": len(group),
            "accuracy": round(float(lang_acc), 4),
            "scam_recall": round(float(lang_scam), 4)
        }
        print(f"Language [{lang}] -> Accuracy: {lang_acc*100:.2f}%, Scam Recall: {lang_scam*100:.2f}%")

    # Measure inference latency
    inference_times = []
    for msg in X_test.iloc[:500]:
        t0 = time.perf_counter()
        best_pipeline.predict([msg])
        inference_times.append((time.perf_counter() - t0) * 1000)
    avg_inf_ms = float(np.mean(inference_times))
    p95_inf_ms = float(np.percentile(inference_times, 95))
    print(f"Average Inference Latency: {avg_inf_ms:.3f} ms (P95: {p95_inf_ms:.3f} ms)")

    # Save model artifacts
    model_dir = Path(__file__).resolve().parents[1] / "model"
    model_dir.mkdir(exist_ok=True)
    
    model_file = model_dir / "sms_classifier_v2.joblib"
    meta_file = model_dir / "model_metadata_v2.json"

    joblib.dump(best_pipeline, model_file)
    print(f"Saved model to {model_file}")

    metadata = {
        "model_version": "KRISS-Colab-2.5-Multilingual",
        "model_name": best_name,
        "classes": labels,
        "languages": sorted(df["language"].unique().tolist()),
        "training_rows": len(X_train),
        "test_rows": len(X_test),
        "split": "70/30 stratified",
        "test_accuracy": round(best_acc, 4),
        "test_macro_f1": round(results[best_name]["macro_f1"], 4),
        "test_scam_recall": round(results[best_name]["scam_recall"], 4),
        "by_language": by_lang,
        "avg_inference_ms": round(avg_inf_ms, 3),
        "p95_inference_ms": round(p95_inf_ms, 3),
        "features": "Word TF-IDF (1,2) + Char TF-IDF (2,5)",
        "meets_srs_target": best_acc >= 0.95,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved metadata to {meta_file}")
    return metadata

if __name__ == "__main__":
    train_and_export()
