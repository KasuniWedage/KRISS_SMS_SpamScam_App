from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "mobile_users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(60), unique=True, index=True, nullable=False)
    email = Column(String(160), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    language_preference = Column(String(20), default="English", nullable=False)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    auto_delete_history = Column(Boolean, default=False, nullable=False)
    # --- Social auth (Google / Facebook) ---
    auth_provider = Column(String(20), default="email", nullable=False)  # "email" | "google" | "facebook"
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    facebook_id = Column(String(255), unique=True, index=True, nullable=True)
    firebase_uid = Column(String(128), unique=True, index=True, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    messages = relationship("SMSMessage", back_populates="user", cascade="all, delete-orphan")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

class PasswordResetToken(Base):
    """
    Only the SHA-256 hash of the reset token is stored. The raw token is
    generated once, emailed to the user, and never persisted anywhere —
    so a leaked database dump on its own cannot be used to reset accounts.
    """
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    attempts = Column(SmallInteger, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user = relationship("User", back_populates="reset_tokens")

class SessionToken(Base):
    __tablename__ = "session_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class SMSMessage(Base):
    __tablename__ = "sms_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_no = Column(String(50), nullable=True)
    masked_text = Column(Text, nullable=False)
    language = Column(String(20), nullable=False)
    received_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    user = relationship("User", back_populates="messages")
    result = relationship("ClassificationResult", back_populates="sms", uselist=False, cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="sms", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="sms", cascade="all, delete-orphan")

class ClassificationResult(Base):
    __tablename__ = "classification_results"
    id = Column(Integer, primary_key=True, index=True)
    sms_id = Column(Integer, ForeignKey("sms_messages.id", ondelete="CASCADE"), unique=True, nullable=False)
    predicted_class = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=False)
    scam_type = Column(String(100), nullable=True)
    explanation = Column(Text, nullable=False)
    model_version = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sms = relationship("SMSMessage", back_populates="result")

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    sms_id = Column(Integer, ForeignKey("sms_messages.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=False)
    report_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    sms = relationship("SMSMessage", back_populates="reports")

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    sms_id = Column(Integer, ForeignKey("sms_messages.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="CASCADE"), nullable=False)
    feedback_text = Column(Text, nullable=True)
    expected_label = Column(String(20), nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    review_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sms = relationship("SMSMessage", back_populates="feedback")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id = Column(Integer, primary_key=True, index=True)
    version_tag = Column(String(50), unique=True, nullable=False)
    sample_count = Column(Integer, nullable=False)
    file_path = Column(String(255), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("mobile_users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class PublishedSpam(Base):
    __tablename__ = "published_spam"
    id = Column(Integer, primary_key=True, index=True)
    sms_id = Column(Integer, ForeignKey("sms_messages.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_no = Column(String(50), nullable=False)
    message_text = Column(Text, nullable=False)
    label = Column(String(20), nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(80), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditSeal(Base):
    """Tamper-evident hash-chain entry for an AuditLog row."""
    __tablename__ = "audit_seals"
    id = Column(Integer, primary_key=True)
    audit_log_id = Column(Integer, ForeignKey("audit_logs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    previous_hash = Column(String(64), nullable=False)
    record_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ApiPerformanceMetric(Base):
    __tablename__ = "api_performance_metrics"
    id = Column(Integer, primary_key=True)
    request_id = Column(String(36), unique=True, nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(160), nullable=False, index=True)
    status_code = Column(Integer, nullable=False, index=True)
    duration_ms = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class SystemError(Base):
    __tablename__ = "system_errors"
    id = Column(Integer, primary_key=True)
    request_id = Column(String(36), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(160), nullable=False, index=True)
    error_type = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class TrainingSample(Base):
    __tablename__ = "training_samples"
    id = Column(Integer, primary_key=True)
    masked_text = Column(Text, nullable=False)
    label = Column(String(20), nullable=False, index=True)
    language = Column(String(20), nullable=False, index=True)
    category = Column(String(100), nullable=True)
    source_type = Column(String(30), nullable=False, index=True)
    source_reference = Column(String(255), nullable=False)
    consent_reference = Column(String(255), nullable=True)
    license_name = Column(String(120), nullable=True)
    review_status = Column(String(20), default="pending", nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)


class BatchAnalysis(Base):
    __tablename__ = "batch_analyses"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("mobile_users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_count = Column(Integer, default=0, nullable=False)
    safe_count = Column(Integer, default=0, nullable=False)
    spam_count = Column(Integer, default=0, nullable=False)
    scam_count = Column(Integer, default=0, nullable=False)
    report_language = Column(String(10), default="en", nullable=False)
    items_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")

