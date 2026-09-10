# KRISS SMS Shield

KRISS SMS Shield is a native Android application and FastAPI backend for detecting legitimate, spam, and scam SMS messages. It combines a multilingual machine-learning model with a high-risk rule engine to provide classifications, confidence scores, explanations, and scam categories.

## Technology stack

- Android: Kotlin, XML layouts, Material Components, Retrofit, Firebase Authentication
- Backend: Python 3.11, FastAPI, SQLAlchemy, JWT authentication
- Machine learning: scikit-learn, word/character TF-IDF, Multinomial Naive Bayes
- Development database: SQLite
- Production-ready database option: MySQL

## Main features

- Email/password registration and sign-in
- Google and Facebook sign-in through Firebase
- Email OTP password-reset flow
- Legitimate, Spam, and Scam classification
- V2 word and character TF-IDF pipeline
- High-risk phishing, credential-theft, prize, parcel, loan, and fake-job rules
- Confidence scores, language detection, scam types, and explanations
- Individual and batch SMS analysis
- Searchable history, batch-history details, and PDF reports
- Community reporting and feedback
- Settings, notifications, and account deletion
- Encrypted Android session and batch-history storage
- Rate limiting, audit logs, session revocation, trusted hosts, and restricted CORS
- English, Sinhala, and Singlish model support
- Administrator console for metrics, users, backups, errors, and audit verification
- Dataset review, approval, consent validation, and CSV export
- API performance telemetry and cryptographically tamper-evident audit logs

## Project structure

```text
android-app/   Native Android application
backend/       FastAPI API, database, authentication, and ML runtime
backend/model/ Trained model artifacts and metadata
colab/         Google Colab training notebook
dataset/       Multilingual development and evaluation datasets
docs/          Requirements and design documentation
```

## Requirements

- Python 3.11
- JDK 17
- Android Studio with Android SDK 34
- Android 7.0 or newer
- Firebase project configuration
- Google/Facebook developer configuration for social sign-in

## Backend setup

Open PowerShell in the repository root:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

Copy `backend/.env.example` to `backend/.env` and configure the required values. Never commit environment or credential files.

Start the API from the repository root:

```powershell
uvicorn app.main:app --reload
```

Development URLs:

- API information: `http://127.0.0.1:8000/`
- Health and active model: `http://127.0.0.1:8000/health`
- Swagger documentation: `http://127.0.0.1:8000/docs`

For SQLite development:

```text
DATABASE_URL=sqlite:///./kriss_dev.db
```

For MySQL, run `backend/sql/create_mysql.sql` and configure a MySQL SQLAlchemy URL.

## Active ML model

The backend loads:

```text
backend/model/sms_classifier_v2.joblib
backend/model/model_metadata_v2.json
```

The active version is `KRISS-Colab-2.0-Trilingual`. The serialized artifact is a complete scikit-learn pipeline containing word-level and character-level TF-IDF features with a Multinomial Naive Bayes classifier (`alpha=0.35`). The classifier provides class probabilities that the API returns as confidence scores.

The model predicts `Legitimate`, `Spam`, and `Scam` and is trained for English, Sinhala, and Singlish text. Tamil is outside the active model scope. The artifact does not use the legacy external vectorizer at runtime.

Runtime versions are pinned in `backend/requirements.txt` and `backend/model/model_runtime_requirements.txt`.

## Android setup

1. Open only `android-app/` in Android Studio.
2. Select JDK 17 as the Gradle JDK.
3. Add the Firebase configuration at `android-app/app/google-services.json`.
4. Add local Facebook and backend values to `backend/.env`.
5. Sync Gradle and run the app on an emulator.

The debug build uses `http://10.0.2.2:8000/`. This maps the emulator to the host computer.

A release build requires a real HTTPS URL in `ANDROID_API_BASE_URL`; the build fails when it is missing or invalid. Use HTTPS for all production deployments.

## Authentication

### Email and password

Email/password accounts are managed by the backend. Passwords are hashed, failed logins can temporarily lock an account, and JWT sessions can be revoked.

Password reset flow:

1. Submit the account email.
2. Receive a six-digit OTP through configured SMTP.
3. Verify the OTP with the backend.
4. New-password fields appear only after verification.
5. Resetting the password invalidates existing sessions and reset codes.

### Google and Facebook

Google and Facebook authentication uses Firebase on Android. The Firebase ID token is verified by the backend before an application session is issued.

Relevant environment variables:

```text
GOOGLE_OAUTH_CLIENT_ID=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_CLIENT_TOKEN=
FIREBASE_CREDENTIALS_PATH=./firebase-service-account.json
```

The Facebook App Secret and Firebase private key belong on the backend only. Never add them to Android XML or source code.

## Security

- Secrets, service accounts, local databases, signing keys, and builds are excluded by `.gitignore`.
- Android access tokens and batch-history messages use encrypted preferences.
- Android backup excludes application preferences, databases, and files.
- Production Android traffic requires HTTPS.
- Authorization and cookie headers are redacted from HTTP logs.
- JWT claims and server-side sessions are validated.
- Authentication and reset endpoints are rate-limited.
- Reset OTPs are bound to the requested email account.
- Production rejects wildcard CORS origins and trusted hosts.
- Audit records and their SHA-256 chain seals are append-only at the application layer.
- Audit verification detects missing, modified, or out-of-order records and can export chain-head anchors.

The audit design is cryptographically **tamper-evident**, not absolutely tamper-proof. Production deployments should store exported chain-head anchors in a separate immutable or append-only system.

If a secret was committed previously, remove it from Git history and rotate it. Adding a file to `.gitignore` does not erase old commits.

## Dataset and validation

The main bundled multilingual development dataset currently contains 13,784 rows across English, Sinhala, Singlish, and Tamil:

- 5,096 Legitimate
- 4,335 Spam
- 4,353 Scam
- 10,000 rows containing template-generated localized development data
- 3,784 rows marked as consented/localized data

The active trilingual model metadata reports 7,000 training rows, 3,000 test rows, no template or cleaned-text overlap, 0.883 test accuracy, and approximately 0.8322 scam recall. The required minimum accuracy is 90%, while 95% is an aspirational improvement target. Therefore, the restored model does not currently meet the minimum accuracy threshold reported by the project.

A separate 47-message multilingual evaluation file produces 0.5532 overall accuracy with the restored model. Because that file includes Tamil messages outside the model scope, a new English/Sinhala/Singlish-only independent evaluation set is required for a fair final assessment. Its source and consent provenance must be independently verified before it is described as real-world research evidence.

Final research validation should use licensed or verifiably user-consented messages, preserve a sufficiently large unseen test set, document source and consent references, and report measured results honestly. Template-generated, localized, and consented data must remain clearly distinguished.

## Administration and operations

Administrators can access system metrics, request latency summaries, centralized error records, user-role management, backup operations, restoration tests, audit-chain verification, and dataset-governance functions. The Android application includes dedicated administrator and dataset-management screens, and the backend also exposes an administrator web console at `/admin`.

Operational scripts are available for:

- database backup, checksum verification, and isolated restoration testing;
- Windows Task Scheduler setup for daily backups;
- health probes and evidence-based uptime reporting;
- local API latency benchmarking;
- audit-chain verification and chain-head export.

The scheduler setup script must be executed by an administrator before daily backups are considered active. Uptime reports require genuine probe logs; the report generator does not create simulated observations. Local `TestClient` latency results measure API integration performance and must not be presented as physical-device or production-network latency.

## Basic test flow

```text
Register or sign in
-> Analyze an SMS
-> Review its label, confidence, and explanation
-> Submit feedback or a report
-> Review and search history
-> Run batch analysis
-> View batch history or download a PDF
-> Update settings
-> Log out
```

## Important files

- `backend/app/main.py`: FastAPI application
- `backend/app/ml_service.py`: V2 model service
- `backend/app/hybrid_rules.py`: high-risk scam rules
- `backend/.env.example`: environment template
- `android-app/app/build.gradle.kts`: Android build configuration
- `START_HERE_SI.txt`: short English quick-start guide retained under its original filename
