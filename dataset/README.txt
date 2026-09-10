KRISS Multilingual SMS Dataset Information
============================================

1. Training Dataset: kriss_sms_multilingual_10000.csv
- 13,784 unique localized SMS samples across 4 Sri Lankan languages
- Languages: English (3,572), Sinhala (3,520), Singlish (3,536), Tamil (3,156)
- Classes: Legitimate (5,096), Spam (4,335), Scam (4,353)
- Columns: id, message, label, language, category, source_type
- UTF-8 with BOM encoded for full Sinhala and Tamil script support
- Features: Dual Word TF-IDF (1,2) + Char TF-IDF (2,5)

2. Held-Out Evaluation Dataset: kriss_real_world_evaluation_dataset.csv
- 47 representative real-world Sri Lankan SMS samples across English, Sinhala, Singlish, and Tamil
- Categorized by threat vectors: Phishing/Banking, Lottery/Prize, Parcel Scam, Fake Loan, Job Scam, Promos, Transactional
- Evaluated with scripts/evaluate_labeled_dataset.py achieving 100% Scam recall

To retrain the model locally or export new artifacts:
  python backend/scripts/train_model.py
