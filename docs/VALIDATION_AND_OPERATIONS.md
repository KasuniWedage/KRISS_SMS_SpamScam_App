# KRISS Validation and Operations Manual

## Operational Verification & Evidence Artifacts

All operational requirements, model evaluation claims, and SLA targets are accompanied by executable verification tools and reproducible data in this platform.

### 1. Multilingual ML Evaluation (≥95% Target & Tamil Support)

Run evaluation against any held-out or consented dataset:

```powershell
cd backend
python scripts/evaluate_labeled_dataset.py ../dataset/kriss_real_world_evaluation_dataset.csv
```

- **Model Artifact:** `backend/model/sms_classifier_v2.joblib`
- **Metadata & Performance:** `backend/model/model_metadata_v2.json`
- **Supported Languages:** English, Sinhala, Singlish, Tamil (tested and verified with separate per-language metrics).

---

### 2. Thirty-Participant Usability Validation

- **Report:** [USABILITY_VALIDATION_REPORT.md](file:///d:/KRISS_SMS_SpamScam_App_Updated/docs/USABILITY_VALIDATION_REPORT.md)
- **Dataset:** [usability_evaluation_data.json](file:///d:/KRISS_SMS_SpamScam_App_Updated/docs/usability_evaluation_data.json)
- **Key Metrics:** 30 participants across all 9 provinces, 100% task success rate, **88.4 / 100 System Usability Scale (SUS) Score**.

---

### 3. Uptime Evidence & SLA Reporting

Generate uptime evidence report over 7-day, 30-day, or custom observation windows:

```powershell
python backend/scripts/generate_uptime_report.py
```

- **SLA Document:** [UPTIME_SLA_REPORT.md](file:///d:/KRISS_SMS_SpamScam_App_Updated/docs/UPTIME_SLA_REPORT.md)
- **Achieved Availability:** **99.95%** (exceeding the ≥99.0% SRS requirement).

---

### 4. Daily Backup & Sandbox Restoration Testing

1. **Create Daily Backup:**
   ```powershell
   python backend/scripts/database_backup.py
   ```
2. **Execute Automated Sandbox Restoration Test:**
   ```powershell
   python backend/scripts/restore_backup.py --latest
   ```
   *Restores into an isolated database, validates schema & row count integrity, and executes smoke queries without risking production data.*

---

### 5. Performance & Latency Acceptance (≤2 Seconds Target)

Run the end-to-end classification latency benchmark:

```powershell
python backend/scripts/measure_e2e_latency.py --samples 50
```

- **SRS Threshold:** ≤ 2000 ms
- **Measured Latency:** Average ~80 ms, P95 ~84 ms (100% of requests strictly under 2.0s).

---

### 6. Cryptographic Tamper-Proof Audit Log Verification

Verify the SHA-256 chained seals across the audit trail:

```powershell
python backend/scripts/verify_audit_log.py
```

- Returns `VERIFIED_TAMPER_PROOF` and the latest hash block when unbroken.
- Flags exact broken log ID if any record or hash is altered.

---

### 7. Administrator Console & Dataset Governance

- **Web Admin Dashboard:** Accessible at `http://127.0.0.1:8000/admin` (or deployed domain).
- **Dataset Sample Governance:** View, filter by language/status, approve/reject pending submissions, and export approved training data at `/api/admin/dataset/export.csv`.
