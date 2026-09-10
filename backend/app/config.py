import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


# Always load the backend-local environment file, regardless of whether
# Uvicorn is launched from the repository root, the backend folder, or an IDE.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def _csv_env(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


def _jwt_secret() -> str:
    configured = os.getenv("JWT_SECRET", "")
    weak = {"", "development-secret-change-me", "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"}
    if configured not in weak and len(configured) >= 32:
        return configured
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        return configured
    secret_file = Path(__file__).resolve().parents[1] / ".jwt-secret"
    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()
    generated = secrets.token_urlsafe(48)
    try:
        with secret_file.open("x", encoding="utf-8") as handle:
            handle.write(generated)
    except FileExistsError:
        return secret_file.read_text(encoding="utf-8").strip()
    return generated

@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development").lower()
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./kriss_dev.db")
    jwt_secret: str = _jwt_secret()
    algorithm: str = "HS256"
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
    model_dir: str = os.getenv("MODEL_DIR", "./model")

    # --- Forgot Password (email delivery) ---
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")  # use an app password, never a real account password
    smtp_from: str = os.getenv("SMTP_FROM", "SecureMessage <no-reply@securemessage.app>")
    password_reset_token_minutes: int = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "15"))
    password_reset_max_requests_per_hour: int = int(os.getenv("PASSWORD_RESET_MAX_REQUESTS_PER_HOUR", "3"))
    # Deep link / URL your Android app opens to land on the reset-password screen
    frontend_reset_url: str = os.getenv("FRONTEND_RESET_URL", "securemessage://reset-password")

    # --- Google Sign-In ---
    # Use the WEB client ID from Google Cloud Console (passed as serverClientId
    # on the Android side), not the Android client ID. The idToken's audience
    # will be the Web client ID, which is what must be verified here.
    google_oauth_client_id: str = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")

    # --- Facebook Login ---
    facebook_app_id: str = os.getenv("FACEBOOK_APP_ID", "")
    facebook_app_secret: str = os.getenv("FACEBOOK_APP_SECRET", "")

    # --- Firebase Authentication (alternative identity backend) ---
    # Path to the service account JSON downloaded from Firebase Console ->
    # Project Settings -> Service Accounts -> Generate new private key.
    # When set, POST /api/auth/firebase-sync becomes usable: the Android app
    # authenticates entirely through Firebase (email/password, Google,
    # Facebook — including Forgot Password, which Firebase emails directly,
    # no SMTP setup needed on this backend at all), then exchanges its
    # Firebase ID token for this app's own session JWT via that endpoint.
    firebase_credentials_path: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

    cors_origins: tuple[str, ...] = _csv_env("CORS_ORIGINS")
    allowed_hosts: tuple[str, ...] = _csv_env("ALLOWED_HOSTS", "127.0.0.1,localhost,10.0.2.2,testserver")

    def validate_security(self) -> None:
        weak_secrets = {"", "development-secret-change-me", "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"}
        if self.jwt_secret in weak_secrets or len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be a random value of at least 32 characters")
        if self.environment == "production":
            if not self.database_url.startswith(("mysql+", "postgresql+")):
                raise RuntimeError("Production must use a managed MySQL/PostgreSQL database")
            if any(origin == "*" for origin in self.cors_origins):
                raise RuntimeError("Wildcard CORS origins are forbidden in production")
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise RuntimeError("Explicit ALLOWED_HOSTS are required in production")

settings = Settings()
