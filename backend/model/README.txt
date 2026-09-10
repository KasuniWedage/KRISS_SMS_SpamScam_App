KRISS Machine Learning Model Artifacts
========================================

Model Version: KRISS Multilingual Model v2.5
Supported Languages: English, Sinhala, Singlish

Artifacts:
1. sms_classifier_v2.joblib
   - End-to-end Pipeline with FeatureUnion (Word TF-IDF + Char TF-IDF) and Calibrated LinearSVC classifier
2. model_metadata_v2.json
   - Full evaluation metrics, 5-fold cross-validation scores, per-language breakdown, and inference latency benchmarks
3. sms_classifier.joblib & tfidf_vectorizer.joblib
   - Backward-compatible unigram+bigram artifacts

To retrain and update artifacts:
   cd backend
   python scripts/train_model.py
