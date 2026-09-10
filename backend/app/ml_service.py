from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

from .config import settings
from .text_utils import preprocess_text


class MLService:
    model: Any
    vectorizer: Any
    metadata: dict
    model_file: str

    def __init__(self) -> None:
        self.model = None
        self.vectorizer = None
        self.metadata = {}
        self.model_file = ""
        self.load()

    def load(self) -> None:
        d = Path(settings.model_dir)
        if not d.is_absolute() and not (d / "sms_classifier_v2.joblib").exists():
            backend_d = Path(__file__).resolve().parents[1] / "model"
            if (backend_d / "sms_classifier_v2.joblib").exists():
                d = backend_d

        model_path_v2 = d / "sms_classifier_v2.joblib"
        meta_path_v2 = d / "model_metadata_v2.json"

        model_path_v1 = d / "sms_classifier.joblib"
        vec_path_v1 = d / "tfidf_vectorizer.joblib"
        meta_path_v1 = d / "model_metadata.json"

        if model_path_v2.exists():
            self.model = joblib.load(model_path_v2)
            self.model_file = model_path_v2.name
            self.vectorizer = None
            if meta_path_v2.exists():
                self.metadata = json.loads(meta_path_v2.read_text(encoding="utf-8"))
        elif model_path_v1.exists():
            self.model = joblib.load(model_path_v1)
            self.model_file = model_path_v1.name
            if vec_path_v1.exists():
                self.vectorizer = joblib.load(vec_path_v1)
            if meta_path_v1.exists():
                self.metadata = json.loads(meta_path_v1.read_text(encoding="utf-8"))

    @property
    def ready(self) -> bool:
        return self.model is not None

    def predict(self, text: str) -> tuple[str, float, dict[str, float]]:
        if not self.ready or self.model is None:
            raise RuntimeError("V2 ML model not loaded. Copy sms_classifier_v2.joblib to backend/model/.")
        cleaned = preprocess_text(text)
        # V2 accepts text directly because feature extraction is embedded in
        # the pipeline. Keep the separate-vectorizer branch for compatibility
        # with older artifacts if one is assigned programmatically.
        x = [cleaned] if self.vectorizer is None else self.vectorizer.transform([cleaned])
        label = str(self.model.predict(x)[0])
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(x)[0]
            classes = [str(c) for c in self.model.classes_]
            dist: dict[str, float] = {c: float(p) for c, p in zip(classes, probs)}
            confidence = float(max(probs))
        else:
            dist = {label: 1.0}
            confidence = 1.0
        return label, confidence, dist


ml_service = MLService()
