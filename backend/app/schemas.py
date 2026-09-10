from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, password: str) -> str:
        if not all((any(c.isupper() for c in password), any(c.islower() for c in password),
                    any(c.isdigit() for c in password), any(not c.isalnum() for c in password))):
            raise ValueError("Password must include uppercase, lowercase, number, and special character")
        return password

class LoginRequest(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    username: str
    email: str
    role: str
    language_preference: str
    notifications_enabled: bool
    auto_delete_history: bool = False
    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    token: str = Field(pattern=r"^\d{6}$")

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not any(c.isalpha() for c in self.new_password) or not any(c.isdigit() for c in self.new_password):
            raise ValueError("Password must contain at least one letter and one number")
        return self

class MessageResponse(BaseModel):
    message: str

class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=10, description="idToken returned by Google Sign-In SDK on Android")

class FacebookAuthRequest(BaseModel):
    access_token: str = Field(min_length=10, description="accessToken returned by Facebook Login SDK on Android")

class FirebaseSyncRequest(BaseModel):
    """
    Sent after the Android app has already authenticated with Firebase
    directly (email/password sign-up or sign-in, Google, or Facebook via
    Firebase). This exchanges the Firebase ID token for this backend's own
    session JWT, and creates/updates the local profile row on first sync.
    name/username are only required the first time (registration); on
    subsequent syncs for an existing account they're ignored.
    """
    id_token: str = Field(min_length=10, description="Firebase ID token from FirebaseAuth.getIdToken()")
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    username: Optional[str] = Field(default=None, min_length=3, max_length=60)

class ClassificationRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    sender_no: Optional[str] = Field(default=None, max_length=50)

class ClassificationResponse(BaseModel):
    sms_id: int
    label: str
    status_code: int
    confidence: float
    language: str
    scam_type: Optional[str] = None
    explanation: str
    rule_override: bool
    class_probabilities: dict[str, float]

class BatchRequest(BaseModel):
    messages: List[ClassificationRequest] = Field(min_length=1, max_length=100)

class BatchItemOut(BaseModel):
    sms_id: int
    message: str
    label: str
    confidence: float
    language: str
    scam_type: Optional[str] = None
    explanation: str

class BatchHistoryOut(BaseModel):
    id: int
    batch_id: str
    total_count: int
    safe_count: int
    spam_count: int
    scam_count: int
    report_language: str = "en"
    items: List[BatchItemOut]
    created_at: datetime

class HistoryItem(BaseModel):
    sms_id: int
    message: str
    language: str
    label: str
    confidence: float
    scam_type: Optional[str] = None
    explanation: str
    created_at: datetime

class ReportRequest(BaseModel):
    sms_id: int
    reason: str = Field(min_length=2, max_length=1000)

class FeedbackRequest(BaseModel):
    sms_id: Optional[int] = None
    feedback_text: Optional[str] = Field(default=None, max_length=1000)
    expected_label: Optional[str] = None

class SettingsUpdate(BaseModel):
    language_preference: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    auto_delete_history: Optional[bool] = None

class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2,max_length=100)
    username: str = Field(min_length=3,max_length=60)
    email: EmailStr

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8,max_length=128)

class DeleteAccountRequest(BaseModel):
    confirmation: str = Field(min_length=14, max_length=14)

class ActivityLogOut(BaseModel):
    id: int
    action: str
    detail: Optional[str]
    created_at: datetime

class PublishSpamRequest(BaseModel):
    sms_id: int
    sender_no: str = Field(min_length=2, max_length=50)
    message: str = Field(min_length=1, max_length=2000)

class PublishedSpamOut(BaseModel):
    id: int
    sender_no: str
    message: str
    label: str
    published_at: datetime

class UserReportOut(BaseModel):
    id: int
    sms_id: int
    message: str
    reason: str
    report_date: datetime

class UserFeedbackOut(BaseModel):
    id: int
    sms_id: Optional[int]
    message: Optional[str]
    feedback_text: Optional[str]
    expected_label: Optional[str]
    created_at: datetime


class TrainingSampleCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    label: str
    language: str
    category: Optional[str] = Field(default=None, max_length=100)
    source_type: str
    source_reference: str = Field(min_length=2, max_length=255)
    consent_reference: Optional[str] = Field(default=None, max_length=255)
    license_name: Optional[str] = Field(default=None, max_length=120)


class TrainingSampleReview(BaseModel):
    status: str
