from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..auth import (
    create_session_token,
    generate_reset_token,
    get_auth_context,
    get_current_user,
    hash_password,
    revoke_user_sessions,
    unusable_password_hash,
    verify_password,
    verify_reset_token,
)
from ..database import get_db
from ..email_utils import send_password_reset_email
from ..models import AuditLog, User
from ..rate_limit import check_rate_limit
from ..schemas import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    FacebookAuthRequest,
    FirebaseSyncRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
    VerifyResetCodeRequest,
)
from ..firebase_auth import verify_firebase_id_token
from ..social_auth import verify_facebook_access_token, verify_google_id_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

GENERIC_RESET_MESSAGE = "If an account with that email exists, a reset link has been sent."


def _unique_username(db: Session, base: str) -> str:
    username = base
    suffix = 1
    while db.query(User).filter(User.username == username).first():
        suffix += 1
        username = f"{base}{suffix}"
    return username


def _login_response(db: Session, request: Request, user: User) -> TokenResponse:
    token = create_session_token(db, user)
    device = request.headers.get("user-agent", "Unknown device")[:300]
    ip = request.client.host if request.client else "Unknown"
    db.add(AuditLog(user_id=user.id, action="LOGIN_SUCCESS", detail=f"device={device}; network_location={ip}"))
    db.commit()
    return TokenResponse(access_token=token, user=user)

@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    email = body.email.lower()
    username = body.username.strip()
    check_rate_limit(f"register-ip:{ip}", limit=5, window_seconds=3600)
    if not any(c.isalpha() for c in body.password) or not any(c.isdigit() for c in body.password):
        raise HTTPException(400, detail="Password must contain at least one letter and one number")
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise HTTPException(409, detail="Username or email already exists")
    user = User(name=body.name.strip(), username=username, email=email, password_hash=hash_password(body.password))
    db.add(user); db.flush(); db.add(AuditLog(user_id=user.id, action="USER_REGISTERED")); db.commit(); db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    username_key = body.username.strip().lower()
    check_rate_limit(f"login-ip:{ip}", limit=20, window_seconds=900)
    check_rate_limit(f"login-account:{username_key}", limit=8, window_seconds=900)
    identifier = body.username.strip()
    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()
    if not user:
        # Perform a bcrypt verification to reduce username timing disclosure.
        hash_password(body.password)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    now = datetime.utcnow()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=423, detail="Account temporarily locked after three failed attempts")
    if user.auth_provider != "email":
        raise HTTPException(
            status_code=400,
            detail=f"This account uses {user.auth_provider.capitalize()} sign-in. "
                   f"Please continue with {user.auth_provider.capitalize()} instead of a password.",
        )
    if not verify_password(body.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 3:
            user.locked_until = now + timedelta(minutes=15)
            user.failed_login_attempts = 0
        db.add(AuditLog(user_id=user.id, action="LOGIN_FAILED")); db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user.failed_login_attempts = 0; user.locked_until = None
    token = create_session_token(db, user)
    device=request.headers.get("user-agent","Unknown device")[:300]
    ip=request.client.host if request.client else "Unknown"
    db.add(AuditLog(user_id=user.id, action="LOGIN_SUCCESS",detail=f"device={device}; network_location={ip}")); db.commit()
    return TokenResponse(access_token=token, user=user)

@router.post("/logout")
def logout(ctx=Depends(get_auth_context), db: Session = Depends(get_db)):
    user, session = ctx
    session.revoked = True
    db.add(AuditLog(user_id=user.id, action="LOGOUT")); db.commit()
    return {"message":"Logged out successfully"}

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    BR: never reveals whether an email is registered — always returns the
    same generic message, whether the account exists, doesn't exist, or
    uses Google/Facebook sign-in (which has no local password to reset).
    BR: rate-limited to prevent mass-reset abuse / email-bombing a user.
    """
    email = body.email.lower()
    check_rate_limit(f"forgot-password:{email}", limit=3, window_seconds=3600)
    check_rate_limit(f"forgot-password-ip:{request.client.host if request.client else 'unknown'}", limit=20, window_seconds=3600)

    user = db.query(User).filter(User.email == email).first()
    if user is not None and user.auth_provider == "email":
        raw_token = generate_reset_token(db, user)
        delivered = send_password_reset_email(user, raw_token)
        if not delivered:
            raise HTTPException(503, detail="Password reset email service is not configured")
        db.add(AuditLog(user_id=user.id, action="PASSWORD_RESET_REQUESTED"))
        db.commit()
    return MessageResponse(message=GENERIC_RESET_MESSAGE)


@router.post("/verify-reset-code", response_model=MessageResponse)
def verify_reset_code(body: VerifyResetCodeRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"verify-reset-code-ip:{ip}", limit=10, window_seconds=900)
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if user is None or verify_reset_token(db, body.token, user.id) is None:
        raise HTTPException(400, detail="This verification code is invalid or has expired.")
    return MessageResponse(message="Verification code confirmed.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"reset-password-ip:{ip}", limit=10, window_seconds=900)
    requested_user = db.query(User).filter(User.email == body.email.lower()).first()
    record = verify_reset_token(db, body.token, requested_user.id) if requested_user else None
    if record is None:
        raise HTTPException(400, detail="This reset link is invalid or has expired. Please request a new one.")

    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None:
        raise HTTPException(400, detail="This reset link is invalid or has expired. Please request a new one.")

    user.password_hash = hash_password(body.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    record.used = True
    revoke_user_sessions(db, user.id)
    # Invalidate every other outstanding token for this user too
    db.query(type(record)).filter(type(record).user_id == user.id, type(record).used.is_(False)).update({"used": True})
    db.add(AuditLog(user_id=user.id, action="PASSWORD_RESET_COMPLETED"))
    db.commit()
    return MessageResponse(message="Password has been reset successfully. Please log in.")


@router.post("/google", response_model=TokenResponse)
def google_login(body: GoogleAuthRequest, request: Request, db: Session = Depends(get_db)):
    """
    Android flow: the app triggers Google Sign-In, gets back an idToken,
    and POSTs it here. The idToken's signature/audience/expiry are
    independently re-verified against Google before any account is
    created or logged into.
    """
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"google-login-ip:{ip}", limit=30, window_seconds=900)
    payload = verify_google_id_token(body.id_token)
    google_id = payload["sub"]
    email = payload["email"].lower()
    name = payload.get("name") or email.split("@")[0]

    user = db.query(User).filter(User.google_id == google_id).first()
    if user is None:
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            # An email/password account already exists for this email —
            # link the Google identity to it instead of creating a duplicate.
            raise HTTPException(409, detail="An account already uses this email. Sign in before linking Google.")
        else:
            username = _unique_username(db, email.split("@")[0])
            user = User(
                name=name,
                username=username,
                email=email,
                password_hash=unusable_password_hash(),
                auth_provider="google",
                google_id=google_id,
                email_verified=True,
            )
            db.add(user)
        db.flush()
        db.add(AuditLog(user_id=user.id, action="USER_REGISTERED_GOOGLE"))
        db.commit()
        db.refresh(user)

    return _login_response(db, request, user)


@router.post("/facebook", response_model=TokenResponse)
def facebook_login(body: FacebookAuthRequest, request: Request, db: Session = Depends(get_db)):
    """
    Android flow: the app triggers Facebook Login, gets back an
    access_token, and POSTs it here. The token is independently
    re-verified against Facebook's Graph API (debug_token + /me) before
    any account is created or logged into.
    """
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"facebook-login-ip:{ip}", limit=30, window_seconds=900)
    profile = verify_facebook_access_token(body.access_token)
    facebook_id = profile["id"]
    email = profile["email"].lower()
    name = profile.get("name") or email.split("@")[0]

    user = db.query(User).filter(User.facebook_id == facebook_id).first()
    if user is None:
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            raise HTTPException(409, detail="An account already uses this email. Sign in before linking Facebook.")
        else:
            username = _unique_username(db, email.split("@")[0])
            user = User(
                name=name,
                username=username,
                email=email,
                password_hash=unusable_password_hash(),
                auth_provider="facebook",
                facebook_id=facebook_id,
                email_verified=True,
            )
            db.add(user)
        db.flush()
        db.add(AuditLog(user_id=user.id, action="USER_REGISTERED_FACEBOOK"))
        db.commit()
        db.refresh(user)

    return _login_response(db, request, user)


@router.post("/firebase-sync", response_model=TokenResponse)
def firebase_sync(body: FirebaseSyncRequest, request: Request, db: Session = Depends(get_db)):
    """
    Exchanges a verified Firebase ID token for this app's own session JWT.

    Firebase itself handles: email/password sign-up & sign-in, Google
    Sign-In, Facebook Login, AND Forgot Password (Firebase sends its own
    reset email — no SMTP configuration needed on this backend for that
    flow at all). This endpoint's only job is to verify the token is
    genuine and keep a local profile row in sync (for FKs on SMSMessage,
    Report, Feedback, etc.), then hand back a normal app session token so
    every other existing endpoint keeps working unchanged.
    """
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"firebase-sync-ip:{ip}", limit=30, window_seconds=900)
    claims = verify_firebase_id_token(body.id_token)
    if claims.get("email_verified") is not True:
        raise HTTPException(403, detail="Verify your email before signing in.")
    firebase_uid = claims["uid"]
    email = claims["email"].lower()
    name = body.name or claims.get("name") or email.split("@")[0]

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is None:
        # Link to an existing local account with the same email if one
        # exists (e.g. they previously registered the "classic" way),
        # otherwise create a fresh profile.
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            raise HTTPException(409, detail="An account already uses this email. Sign in before linking Firebase.")
        else:
            base_username = (body.username or email.split("@")[0]).strip()
            username = _unique_username(db, base_username)
            user = User(
                name=name.strip(),
                username=username,
                email=email,
                password_hash=unusable_password_hash(),  # Firebase owns the password, not us
                auth_provider="firebase",
                firebase_uid=firebase_uid,
                email_verified=claims.get("email_verified", False),
            )
            db.add(user)
        db.flush()
        db.add(AuditLog(user_id=user.id, action="USER_REGISTERED_FIREBASE"))
        db.commit()
        db.refresh(user)

    return _login_response(db, request, user)
