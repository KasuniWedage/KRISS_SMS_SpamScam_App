"""
app/firebase_auth.py

Verifies Firebase ID tokens sent up from the Android app. The Android app
authenticates directly against Firebase (email/password sign-up/sign-in,
Google Sign-In, Facebook Login, and — importantly — Forgot Password, which
Firebase emails on its own infrastructure with zero SMTP setup needed here).

This backend's job is narrower than before: it doesn't manage passwords or
send any auth emails itself when Firebase is used. It only verifies that a
Firebase ID token is genuine (signature + expiry + project match) and then
issues its own session JWT for the rest of the API (classify, history,
reports, etc. all keep using the existing get_current_user dependency).

Firebase is entirely optional here: if FIREBASE_CREDENTIALS_PATH isn't set,
POST /api/auth/firebase-sync returns a clear 500 instead of crashing, and
the original email/password + Google/Facebook flows keep working exactly
as before.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from .config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional firebase_admin import — the SDK is not required for local dev.
# Pyrefly / type checkers see the real types when the package is installed;
# at runtime we fall back gracefully when it is absent.
# ---------------------------------------------------------------------------
_FIREBASE_AVAILABLE = False
try:
    import firebase_admin  # type: ignore[import-untyped]
    from firebase_admin import auth as firebase_admin_auth  # type: ignore[import-untyped]
    from firebase_admin import credentials  # type: ignore[import-untyped]
    _FIREBASE_AVAILABLE = True
except ImportError:
    firebase_admin = None  # type: ignore[assignment]
    firebase_admin_auth = None  # type: ignore[assignment]
    credentials = None  # type: ignore[assignment]

_app_lock = threading.Lock()
_firebase_app: Any = None


def _get_firebase_app() -> Any:
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    with _app_lock:
        if _firebase_app is not None:
            return _firebase_app
        if not settings.firebase_credentials_path:
            return None
        if not _FIREBASE_AVAILABLE:
            logger.warning("firebase_admin package is not installed; Firebase auth unavailable.")
            return None
        try:
            credential_path = Path(settings.firebase_credentials_path)
            if not credential_path.is_absolute():
                credential_path = Path(__file__).resolve().parents[1] / credential_path
            if not credential_path.is_file():
                raise FileNotFoundError(f"Firebase service-account file not found: {credential_path}")
            cred = credentials.Certificate(str(credential_path))  # type: ignore[union-attr]
            _firebase_app = firebase_admin.initialize_app(cred)  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("Failed to initialize Firebase Admin SDK: %s", exc)
            return None
        return _firebase_app


def verify_firebase_id_token(id_token: str) -> dict:
    """
    Returns the decoded token claims (uid, email, email_verified, name, ...)
    on success. Raises HTTPException(401) on any invalid/expired/tampered
    token, and HTTPException(500) if Firebase isn't configured at all.
    """
    app = _get_firebase_app()
    if app is None:
        raise HTTPException(
            500,
            detail="Firebase authentication is not configured on this server "
                   "(FIREBASE_CREDENTIALS_PATH is not set).",
        )

    if not _FIREBASE_AVAILABLE or firebase_admin_auth is None:
        raise HTTPException(500, detail="Firebase Admin SDK is not installed.")

    try:
        decoded = firebase_admin_auth.verify_id_token(id_token, app=app, check_revoked=True)
    except firebase_admin_auth.RevokedIdTokenError as exc:  # type: ignore[union-attr]
        raise HTTPException(401, detail="This session has been revoked. Please sign in again.") from exc
    except firebase_admin_auth.ExpiredIdTokenError as exc:  # type: ignore[union-attr]
        raise HTTPException(401, detail="Session expired. Please sign in again.") from exc
    except firebase_admin_auth.InvalidIdTokenError as exc:  # type: ignore[union-attr]
        raise HTTPException(401, detail="Invalid authentication token.") from exc
    except Exception as exc:
        logger.warning("Unexpected error verifying Firebase token: %s", exc)
        raise HTTPException(401, detail="Could not verify authentication token.") from exc

    if "uid" not in decoded or "email" not in decoded:
        raise HTTPException(401, detail="Firebase token is missing required profile fields.")

    return decoded  # type: ignore[no-any-return]


def delete_firebase_user(firebase_uid: str) -> None:
    app = _get_firebase_app()
    if app is None:
        raise HTTPException(500, detail="Firebase authentication is not configured on this server.")
    if not _FIREBASE_AVAILABLE or firebase_admin_auth is None:
        raise HTTPException(500, detail="Firebase Admin SDK is not installed.")
    try:
        firebase_admin_auth.delete_user(firebase_uid, app=app)  # type: ignore[union-attr]
    except firebase_admin_auth.UserNotFoundError:  # type: ignore[union-attr]
        return
    except Exception as exc:
        logger.error("Failed to delete Firebase user: %s", exc)
        raise HTTPException(502, detail="Could not delete the identity-provider account.") from exc
