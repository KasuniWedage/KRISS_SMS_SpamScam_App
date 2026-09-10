# KRISS SMS Shield — System Diagram Drawing Specification

## 1. Purpose and scope

This document contains the information required to draw the principal system-design diagrams for KRISS SMS Shield. It reflects the current Android, FastAPI, ML, database, administration, monitoring, backup, and dataset-governance implementation.

The existing `ANDROID_CLASS_DIAGRAM.puml` is only an Android class diagram. It is **not** a use-case diagram. A complete system-design submission should include the use-case diagram described in Section 3.

### Source-document comparison

Two previous System Design documents were checked:

| Document | Finding | How it should be used |
|---|---|---|
| `KRISS_SMS_Shield_System_Design_Diagrams.docx` (Version 1.0) | Contains one use-case diagram, two ER views, one physical schema, and three sequence diagrams. Several parts no longer match the implementation. | Historical reference only |
| `KRISS_SMS_Shield_System_Design_Diagrams_v2.docx` (Version 2.0) | Contains updated use-case packages, 15-entity ER/schema views, corrected authentication/classification flows, and additional admin sequences. | Primary document reference, subject to verification against current code |

Therefore, the answer to “does the document have a use-case diagram?” is **yes for both documents**. Version 1.0 has a single large use-case figure. Version 2.0 reorganizes the use-case model into eight smaller package figures.

Important Version 1.0 issues that must not be copied into new diagrams:

- It combines backend-native email/password sign-in with Firebase sign-in.
- It shows only nine persistent entities/tables instead of the current fifteen.
- It treats every SMS message as necessarily having a classification result; the stored schema permits `SMSMessage 1 — 0..1 ClassificationResult`.
- It omits audit seals, performance metrics, system errors, training samples, dataset versions, and batch analyses.
- It omits current administration, backup/restore, audit verification, and dataset-governance workflows.
- It describes hybrid rules and ML as parallel logic paths; in the implementation they are evaluated during the same request and their outputs are then combined.

### Current ML scope

- Supported model languages: English, Sinhala, and Singlish.
- Tamil is outside the active model scope.
- Classes: `Legitimate`, `Spam`, and `Scam`.
- Pipeline: word TF-IDF + character TF-IDF + Multinomial Naive Bayes.
- Hybrid high-risk rules supplement the ML result.

Do not label the active model as Tamil-supported or as a calibrated SVM unless a different verified artifact is deployed.

## 2. Recommended diagram set

| No. | Diagram | Purpose |
|---:|---|---|
| 1 | System context diagram | Shows the system boundary and external parties |
| 2 | Use-case diagram | Shows user/admin goals and external actors |
| 3 | Component/architecture diagram | Shows Android, API, ML, database, and external services |
| 4 | Deployment diagram | Shows runtime nodes and communication paths |
| 5 | Android class diagram | Shows Android implementation structure |
| 6 | Backend class diagram | Shows ORM entities and backend services/modules |
| 7 | Chen conceptual ER diagram | Shows conceptual entities, attributes, and relationships |
| 8 | Logical/relational ER diagram | Shows tables, keys, and exact cardinalities |
| 9 | Sequence diagrams | Shows important runtime interactions |
| 10 | Activity diagrams | Shows classification and administrative workflows |
| 11 | Data-flow diagrams | Shows process and data-store movement at Levels 0 and 1 |

## 3. Use-case diagram

### 3.1 System boundary

Draw one rectangle named **KRISS SMS Shield**. All use cases must be inside it. Human and external-system actors stay outside it.

### 3.2 Actors

| Actor | Type | Responsibility |
|---|---|---|
| End User | Primary human actor | Uses classification and account functions |
| Administrator | Specialized human actor | Manages and monitors the system |
| Firebase Authentication | External system | Supports Google/Facebook/Firebase authentication |
| Email Service (SMTP) | External system | Sends password-reset codes |
| ML Classifier | Supporting system/component | Produces class probabilities/prediction |
| Backup Storage / Scheduler | External operational actor | Schedules and retains database backups |

Model `Administrator --|> End User` only if the administrator can perform every end-user use case. Otherwise, keep the actors separate.

### 3.3 End-user use cases

- Register account
- Sign in with email and password
- Sign in with Google
- Sign in with Facebook
- Verify email
- Recover password
- Verify reset code
- Reset password
- Log out
- Analyze a single SMS
- Analyze a batch of SMS messages
- View classification result
- View analysis history
- Search/filter history
- View batch history
- Download/export PDF report
- Submit feedback
- Report suspicious message
- Publish classified message to community list
- View community warnings
- Update profile
- Change password
- Manage app settings
- Manage notification preference
- Delete account

### 3.4 Recommended eight-package layout

The Version 2.0 document uses eight use-case packages for readability. Preserve this grouping when recreating the document:

#### Package 1 — Authentication

- Register account
- Sign in with email/password
- Sign in with Google
- Sign in with Facebook
- Verify email
- Recover password
- Verify reset code
- Reset password
- Log out

External actors: Firebase Authentication, Google, Facebook, and Email Service/SMTP. Keep them separate. Email/password login is backend-native and must not be connected to Firebase.

#### Package 2 — SMS Analysis

- Analyze single SMS
- Analyze batch SMS
- Classify message
- Validate session and rate limit
- Preprocess/mask text
- Detect language
- Apply hybrid scam rules
- Run ML classification
- Combine outcomes
- Store result
- View classification result

Both single and batch analysis include the shared `Classify message` routine. Batch analysis does **not** include the single-analysis screen/use case.

#### Package 3 — History and Reports

- View analysis history
- Search/filter history
- Delete individual history item
- Clear history by category
- View batch history
- Delete batch-history item
- Clear batch history
- Download single-analysis PDF
- Download batch-analysis PDF

#### Package 4 — Community

- View community warnings
- Report suspicious message
- View own reports
- Submit feedback
- View own feedback
- Publish message to community list

#### Package 5 — Account and Settings

- View/update profile
- Change password
- Change interface language
- Manage notification preference
- Manage automatic history deletion
- Delete account

#### Package 6 — Administration

- View registered users
- Update user role
- View all user reports
- Access administrator dashboard

#### Package 7 — Backup and Monitoring

- View system metrics
- View request latency/performance
- View centralized error log
- Verify audit-chain integrity
- Export audit-chain head/anchor
- List backups
- Create backup and checksum manifest
- Run sandbox restoration test
- Restore live database after explicit confirmation

#### Package 8 — Dataset Governance

- View/filter training samples
- Detect duplicate samples
- Validate source, licence, and consent information
- Approve/reject sample
- Export approved dataset CSV
- Create dataset version

Dataset review/versioning does not automatically train or deploy a model.

### 3.5 Administrator use cases

- View system metrics
- View API performance and latency statistics
- View centralized error records
- View user reports
- Manage user roles
- Trigger database backup
- View available backups
- Run isolated restoration test
- Restore a live backup, subject to confirmation
- Verify audit-log hash chain
- Export audit-chain anchor
- Review dataset samples
- Approve/reject dataset samples
- Filter dataset samples by status/language
- Validate dataset provenance and consent
- Detect duplicate dataset samples
- Export approved dataset CSV
- Create dataset-version snapshot

### 3.6 Correct `include` and `extend` relationships

Use a dashed arrow pointing **toward the included/base use case**.

| Source use case | Relationship | Target use case | Reason |
|---|---|---|---|
| Analyze single SMS | `<<include>>` | Validate session | Always required |
| Analyze single SMS | `<<include>>` | Preprocess and mask SMS | Always required |
| Analyze single SMS | `<<include>>` | Detect language | Always required |
| Analyze single SMS | `<<include>>` | Apply hybrid scam rules | Always required |
| Analyze single SMS | `<<include>>` | Run ML classification | Always required |
| Analyze single SMS | `<<include>>` | Store result | Always required |
| Analyze batch SMS | `<<include>>` | Analyze single SMS | Repeated for every item |
| Recover password | `<<include>>` | Send reset code | Required when eligible account exists |
| Reset password | `<<include>>` | Verify reset code | Reset requires a valid code |
| Sign in with Google | `<<include>>` | Verify Firebase/Google token | Token verification is mandatory |
| Sign in with Facebook | `<<include>>` | Verify Firebase/Facebook token | Token verification is mandatory |
| Download PDF report | `<<extend>>` | View classification result | Optional action from a result |
| Submit feedback | `<<extend>>` | View classification result | Optional action |
| Report suspicious message | `<<extend>>` | View classification result | Optional action |
| Publish to community list | `<<extend>>` | View classification result | Optional action |

Do not connect Firebase Authentication directly to unrelated operations such as history export. Do not use ordinary solid arrows between use cases to represent screen navigation.

## 4. System context diagram

Place **KRISS SMS Shield** in the center and connect it to:

- End User: credentials, SMS content, settings, feedback; receives classifications and reports.
- Administrator: management commands; receives metrics, errors, backup, audit, and dataset information.
- Firebase Authentication: ID/access tokens and verified identity claims.
- Email Service: password-reset email request and delivery status.
- Backup Storage/Scheduler: scheduled backup trigger, backup files, checksum manifests.
- Monitoring/Health Probe: health requests and uptime/latency observations.

The database and ML model are internal components and normally should not be external actors in a context diagram.

## 5. Component/architecture diagram

### 5.1 Components

**Android client**

- Activities and XML layouts
- Retrofit API client
- SessionManager/encrypted preferences
- Authentication helpers
- PDF report generators
- Batch-history cache
- Threat notification manager

**FastAPI backend**

- Authentication router
- Classification router
- Batch router
- History/user router
- Admin router
- Dataset and dataset-admin routers
- JWT/session validation
- Rate limiter
- Classification service
- Observability middleware
- Audit-chain service
- Backup/restore utilities

**ML subsystem**

- Text normalization and masking
- Language detection
- Hybrid rule engine
- TF-IDF pipeline
- Multinomial Naive Bayes model
- Model metadata

**Persistence**

- SQLite for development or MySQL for production
- Model artifact files
- Backup files and checksum manifests
- Dataset CSV/version snapshots

**External services**

- Firebase/Google/Facebook authentication
- SMTP email service

### 5.2 Main connectors

```text
End User / Administrator
        -> Android Client
        -> HTTPS REST/JSON through Retrofit
        -> FastAPI routers and authorization
        -> services / hybrid rules / ML pipeline
        -> SQL database

Android Client -> Firebase Authentication
FastAPI Backend -> Firebase/Google/Facebook token verification
FastAPI Backend -> SMTP service
Backup utility -> backup storage
Health probe -> FastAPI /health
```

Show the hybrid-rule engine and ML model as parallel inputs to the final classification decision, not as database tables.

## 6. Deployment diagram

### 6.1 Nodes and artifacts

| Node | Artifacts/components |
|---|---|
| Android device/emulator | APK, Activities, Retrofit, encrypted local preferences/cache |
| Backend application server | Python 3.11, Uvicorn, FastAPI application, ML runtime |
| Database server | SQLite file in development or MySQL service in production |
| Model storage | `sms_classifier_v2.joblib`, `model_metadata_v2.json` |
| Backup storage | database backup, SHA-256 manifest, audit anchor |
| Firebase/identity-provider cloud | Firebase, Google, Facebook authentication |
| SMTP server | Password-reset email delivery |
| Monitoring host/scheduler | health probe, uptime log, scheduled backup task |

### 6.2 Protocol labels

- Android to backend: HTTPS/REST/JSON in production.
- Emulator to local backend: HTTP via `10.0.2.2:8000` for development only.
- Backend to database: SQLAlchemy database connection.
- Backend to identity providers: HTTPS token verification.
- Backend to SMTP: authenticated SMTP/TLS where configured.
- Scheduler to backup script: operating-system scheduled task.

Do not depict SQLite as a separate network server. It is a file used by the backend process.

## 7. Android class diagram

Use `docs/ANDROID_CLASS_DIAGRAM.puml` as the source. The essential groups are:

- Framework: `Application`, `AppCompatActivity`, `RecyclerView.Adapter`.
- Authentication UI: `KrissApplication`, `SplashActivity`, `LoginActivity`, `RegisterActivity`, `ForgotPasswordActivity`.
- Authentication helpers: `FirebaseAuthManager`, `GoogleAuthHelper`, `FacebookAuthHelper`.
- End-user UI: `HomeActivity`, `ResultActivity`, `BatchActivity`, `BatchHistoryActivity`, `HistoryActivity`, `CommunityActivity`, `SettingsActivity`, `AccountSettingsActivity`, `GuideActivity`.
- Admin UI: `AdminActivity`, `DatasetAdminActivity`.
- Infrastructure: `ApiService`, `RetrofitClient`, `SessionManager`, `AuthGuard`.
- Reports/cache: `AnalysisPdfReport`, `BatchAnalysisPdfReport`, `BatchHistoryStore`, `ThreatNotificationManager`.
- Adapters: `HistoryAdapter`, `CommunityAdapter`, `BatchHistoryAdapter`, `DatasetSampleAdapter`.
- DTOs: authentication, classification, history, batch, admin, audit, and dataset DTOs.

Important modeling rules:

- Activities inherit from `AppCompatActivity`.
- Adapters inherit from `RecyclerView.Adapter`.
- Android launches `SplashActivity` from the manifest; `KrissApplication` does not instantiate it.
- Navigation via `Intent` is a dependency, not composition.
- `RetrofitClient` creates/provides `ApiService`.
- `BatchHistoryStore` aggregates/serializes report data; it does not own the DTO class definition.

## 8. Backend class diagram

Use `docs/BACKEND_CLASS_DIAGRAM.puml` as the starting source and separate these concepts:

### 8.1 ORM entity classes

- `User`
- `SessionToken`
- `PasswordResetToken`
- `SMSMessage`
- `ClassificationResult`
- `Report`
- `Feedback`
- `PublishedSpam`
- `AuditLog`
- `AuditSeal`
- `ApiPerformanceMetric`
- `SystemError`
- `TrainingSample`
- `DatasetVersion`
- `BatchAnalysis`

### 8.2 Runtime services/modules

- `MLService`
- classification service (`classify_and_store`)
- hybrid-rule module
- text utility module
- authentication module
- Firebase/social-token verifier modules
- observability middleware
- audit-chain functions
- backup/restore utilities

Python modules containing functions should be marked `<<module>>`; do not present every module as a concrete service class.

## 9. Chen conceptual ER diagram

### 9.1 Entities

Draw rectangles for all entities listed in Section 8.1. Draw attributes as ovals and underline primary keys. At conceptual level, do not repeat foreign keys as ordinary attributes when the relationship already represents them.

### 9.2 Relationships and min-max cardinalities

| Entity A | Relationship | Entity B | A participation | B participation |
|---|---|---|---|---|
| User | owns | SessionToken | `(0,N)` | `(1,1)` |
| User | requests | PasswordResetToken | `(0,N)` | `(1,1)` |
| User | submits | SMSMessage | `(0,N)` | `(1,1)` |
| SMSMessage | has result | ClassificationResult | `(0,1)` | `(1,1)` |
| User | files | Report | `(0,N)` | `(1,1)` |
| SMSMessage | is subject of | Report | `(0,N)` | `(1,1)` |
| User | gives | Feedback | `(0,N)` | `(1,1)` |
| SMSMessage | relates to | Feedback | `(0,N)` | `(0,1)` |
| User | publishes | PublishedSpam | `(0,N)` | `(1,1)` |
| SMSMessage | may be published as | PublishedSpam | `(0,1)` | `(1,1)` |
| User | generates | AuditLog | `(0,N)` | `(0,1)` |
| AuditLog | protected by | AuditSeal | `(0,1)` | `(1,1)` |
| User | owns | BatchAnalysis | `(0,N)` | `(1,1)` |
| User | reviews | TrainingSample | `(0,N)` | `(0,1)` |
| User | creates | DatasetVersion | `(0,N)` | `(1,1)` |

`ApiPerformanceMetric` and `SystemError` can exist independently and need not have a direct `User` relationship because a request may be anonymous or may fail before authentication.

## 10. Logical/relational ER diagram

### 10.1 Key constraints

- Every table has integer `id` as its primary key, except the business identifier `BatchAnalysis.batch_id`, which is unique but not the primary key.
- Unique fields: username, email, social IDs, Firebase UID, session JTI, reset-token hash, classification `sms_id`, published-spam `sms_id`, audit-seal `audit_log_id`, audit record hash, performance request ID, dataset version tag, batch ID.
- Nullable foreign keys: `AuditLog.user_id`, `TrainingSample.reviewer_id`, and `Feedback.sms_id`.
- All other foreign keys shown in the ERD are mandatory.

### 10.2 Table relationships

```text
mobile_users 1 ---- 0..* session_tokens
mobile_users 1 ---- 0..* password_reset_tokens
mobile_users 1 ---- 0..* sms_messages
sms_messages 1 ---- 0..1 classification_results
mobile_users 1 ---- 0..* reports
sms_messages 1 ---- 0..* reports
mobile_users 1 ---- 0..* feedback
sms_messages 0..1 ---- 0..* feedback
mobile_users 1 ---- 0..* published_spam
sms_messages 1 ---- 0..1 published_spam
mobile_users 0..1 ---- 0..* audit_logs
audit_logs 1 ---- 0..1 audit_seals
mobile_users 1 ---- 0..* batch_analyses
mobile_users 0..1 ---- 0..* training_samples (reviewer)
mobile_users 1 ---- 0..* dataset_versions (creator)
```

Include `Feedback.status` and `Feedback.review_note`; older ER diagrams often omit these current fields.

## 11. Required sequence diagrams

### 11.1 Email/password sign-in

Participants: End User, Android App, FastAPI Auth API, Database.

1. User submits username/email and password.
2. Android calls `POST /api/auth/login`.
3. API applies IP/account rate limits.
4. API looks up the user and checks lock status/provider.
5. API verifies password.
6. Invalid attempt increments the counter; the third failure locks the account temporarily.
7. Valid login creates `SessionToken` and `AuditLog`.
8. API returns JWT and user/role.
9. Android saves token and role.
10. Android opens `HomeActivity` or `AdminActivity` according to role.

### 11.2 Firebase/Google/Facebook sign-in

Participants: End User, Android App, Firebase/Provider, FastAPI Auth API, Database.

1. User selects provider.
2. Android authenticates with Firebase/provider.
3. Provider returns a token.
4. Android sends the token to the backend sync/provider endpoint.
5. Backend independently verifies signature, audience, expiry, and verified email where applicable.
6. Backend finds user by provider ID/Firebase UID.
7. If no profile exists, check email conflict, then create a local profile.
8. Backend creates application session and audit record.
9. Backend returns application JWT and profile.

Show `alt` fragments for invalid/unverified token, email conflict, existing profile, and new profile.

### 11.3 Password recovery

Participants: End User, Android App, Auth API, Database, SMTP.

1. Submit email to `forgot-password`.
2. Rate-limit request and look up an eligible email account.
3. Store only the reset-token hash and expiry.
4. Send the raw code through SMTP.
5. Always return a generic response where appropriate.
6. Submit email and code to `verify-reset-code`.
7. Show an `alt` fragment for invalid/expired and valid code.
8. Submit new password to `reset-password`.
9. Update password hash, mark codes used, revoke existing sessions, and write audit log.

### 11.4 Single-SMS classification

Participants: End User, Android App, Classification API, Rate Limiter/Auth, Text Utilities, Hybrid Rule Engine, ML Service, Database, Notification Manager.

1. Submit message, optional sender, and access token.
2. Validate session, rate limit, non-empty text, and maximum length.
3. Normalize, mask sensitive values, and detect language.
4. Evaluate high-risk rules.
5. Run ML prediction and obtain class probabilities.
6. Combine rule and ML outcomes into final label, confidence, scam type, and explanation.
7. Store `SMSMessage`, `ClassificationResult`, and `AuditLog`/seal.
8. Return response to Android.
9. Android displays result and optionally shows a threat notification.

### 11.5 Batch classification

Use a `loop` fragment around the single-message classification operation. After all items, calculate legitimate/spam/scam totals, persist `BatchAnalysis`, cache/display results, and optionally create a PDF.

### 11.6 Feedback/report/community publication

Show three optional flows from a classification result:

- Submit feedback -> store pending feedback.
- Report suspicious message -> store report.
- Publish warning -> create one `PublishedSpam` row per SMS; enforce unique `sms_id`.

### 11.7 Admin backup and restoration test

Participants: Administrator, Admin UI, Admin API, Backup Utility, Database, Backup Storage, Audit Service.

Show authorization first. Create backup, calculate checksum, save manifest, then run restoration against an isolated target. Live restore must be a separate confirmed alternative, never part of the automatic test.

### 11.8 Dataset governance

Participants: Administrator, Dataset UI, Dataset Admin API, Database, CSV/Snapshot Storage.

Load/filter samples, review provenance/consent, approve or reject, detect duplicates, export approved CSV, and create a version snapshot. End with a note that snapshot creation does not retrain or deploy the model.

## 12. Activity diagrams

### 12.1 Classification activity

```text
Start
-> Enter/paste SMS
-> Validate input and session
-> [invalid] show error -> End
-> Normalize and mask
-> Detect language
-> Evaluate hybrid rules
-> Run ML model
-> Combine decisions
-> Store message/result/audit record
-> Display label, confidence, scam type, explanation
-> [threat and notifications enabled] show notification
-> Optional feedback/report/PDF
-> End
```

### 12.2 Administrator activity

```text
Start -> Authenticate -> Check admin role
-> [not admin] return 403 / login
-> Load dashboard
-> Choose metrics | errors | users | backups | audit | dataset
-> Perform selected authorized operation
-> Record audit event
-> Refresh result
-> End or choose another operation
```

## 13. Data-flow diagrams

### 13.1 Level 0

External entities: End User, Administrator, Identity Provider, Email Service, Backup/Scheduler.

Single process: `0 — KRISS SMS Shield`.

Flows include credentials/tokens, SMS messages, classifications, reports/feedback, admin commands/metrics, password-reset messages, and backup artifacts.

### 13.2 Level 1 processes

- `1.0 Manage Authentication and Sessions`
- `2.0 Classify SMS Messages`
- `3.0 Manage History, Reports, Feedback, and Community Warnings`
- `4.0 Manage Administration and Observability`
- `5.0 Manage Dataset Governance`
- `6.0 Manage Backup, Restore, and Audit Integrity`

Data stores:

- `D1 Users and Sessions`
- `D2 SMS Messages and Classification Results`
- `D3 Reports, Feedback, and Published Spam`
- `D4 Audit, Performance, and Error Records`
- `D5 Training Samples and Dataset Versions`
- `D6 Batch Analyses`
- `D7 Backup Files and Integrity Manifests`
- `D8 ML Model Artifacts`

Do not draw direct data flow between an external actor and a data store; every flow must pass through a process.

## 14. Cross-diagram consistency checklist

- Use the same names in every diagram: `SMSMessage`, `ClassificationResult`, `PublishedSpam`, and so forth.
- Use English/Sinhala/Singlish as the active model scope.
- Use `Legitimate`, `Spam`, and `Scam` consistently; do not alternate between `Safe` and `Legitimate` without explaining response normalization.
- Show administrator authorization on every admin flow.
- Show JWT/session verification before protected API operations.
- Keep Firebase authentication separate from the application JWT/session.
- Keep the hybrid rule engine and ML classifier as separate components.
- Represent nullable foreign keys with optional cardinality.
- Represent unique `sms_id` in classification results and published spam as one-to-zero-or-one.
- Include `BatchAnalysis`, `AuditSeal`, monitoring/error entities, and dataset-governance entities in current database diagrams.
- Describe the audit mechanism as **tamper-evident**, not absolutely tamper-proof.
- Do not claim that a scheduled backup is active merely because a setup script exists; show the scheduler as a deployment/operations dependency.
- Do not claim measured uptime, latency, usability, or accuracy without genuine test evidence.
- Dataset approval/versioning does not automatically retrain or deploy the ML model.

## 15. Suggested drawing order

1. Draw the system context diagram.
2. Draw the use-case diagram.
3. Draw component and deployment diagrams.
4. Draw conceptual and logical ER diagrams.
5. Finalize Android and backend class diagrams.
6. Draw the eight sequence flows.
7. Draw classification/admin activity diagrams.
8. Draw DFD Levels 0 and 1.
9. Run the cross-diagram consistency checklist.
