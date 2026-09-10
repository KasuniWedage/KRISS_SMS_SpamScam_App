import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import PasswordResetToken, SessionToken, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def unusable_password_hash() -> str:
    """
    Used for accounts created via Google/Facebook, which have no local
    password. password_hash stays NOT NULL, but the value is a bcrypt hash
    of a random, never-revealed string, so it can never validate against
    anything a user types in.
    """
    return pwd_context.hash(secrets.token_urlsafe(32))

# ---------------------------------------------------------------------------
# Forgot Password reset tokens
# ---------------------------------------------------------------------------

RESET_TOKEN_MAX_ATTEMPTS = 5

def _reset_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()

def generate_reset_token(db: Session, user: User) -> str:
    # Invalidate any previous unused tokens so only the newest one is valid
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False)
    ).update({"used": True})

    # Mobile-friendly OTP; only its SHA-256 hash is persisted.
    raw_token = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.utcnow() + timedelta(minutes=settings.password_reset_token_minutes)
    db.add(PasswordResetToken(user_id=user.id, token_hash=_reset_token_hash(raw_token), expires_at=expires_at))
    db.commit()
    return raw_token

def verify_reset_token(db: Session, raw_token: str, user_id: int | None = None) -> PasswordResetToken | None:
    token_hash = _reset_token_hash(raw_token)
    query = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash)
    if user_id is not None:
        query = query.filter(PasswordResetToken.user_id == user_id)
    record = query.first()
    if record is None:
        # A wrong OTP has a different hash, so account the failure against the
        # user's latest outstanding token instead of silently allowing
        # unlimited guesses until the IP rate limit is reached.
        if user_id is not None:
            latest = (
                db.query(PasswordResetToken)
                .filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used.is_(False))
                .order_by(PasswordResetToken.created_at.desc())
                .first()
            )
            if latest is not None:
                latest.attempts += 1
                if latest.attempts >= RESET_TOKEN_MAX_ATTEMPTS:
                    latest.used = True
                db.commit()
        return None
    if record.used or record.expires_at < datetime.utcnow() or record.attempts >= RESET_TOKEN_MAX_ATTEMPTS:
        record.attempts += 1
        if record.attempts >= RESET_TOKEN_MAX_ATTEMPTS:
            record.used = True
        db.commit()
        return None
    return record

def create_session_token(db: Session, user: User) -> str:
    now = datetime.utcnow()
    expires = now + timedelta(minutes=settings.access_token_minutes)
    jti = str(uuid4())
    payload = {"sub": str(user.id), "jti": jti, "role": user.role, "iat": now, "exp": expires}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.algorithm)
    db.add(SessionToken(user_id=user.id, jti=jti, expires_at=expires))
    db.commit()
    return token

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.algorithm],
            options={"require": ["sub", "exp", "iat", "jti"]},
        )
        if not payload.get("jti"):
            raise jwt.InvalidTokenError("Missing jti")
        return payload
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

def revoke_user_sessions(db: Session, user_id: int) -> None:
    db.query(SessionToken).filter(
        SessionToken.user_id == user_id,
        SessionToken.revoked.is_(False),
    ).update({"revoked": True})
    db.commit()

def get_auth_context(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    jti = payload.get("jti")
    session = db.query(SessionToken).filter(SessionToken.jti == jti, SessionToken.user_id == user_id).first()
    if not session or session.revoked or session.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired or logged out")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user, session

def get_current_user(ctx=Depends(get_auth_context)) -> User:
    return ctx[0]

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user
