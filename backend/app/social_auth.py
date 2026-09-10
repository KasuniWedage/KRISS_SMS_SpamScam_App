"""
app/social_auth.py

Verifies tokens produced by the Google Sign-In and Facebook Login SDKs on
the Android app. The backend NEVER trusts a client-supplied email/name/id
directly — it re-validates the token against Google's / Facebook's own
servers first. Skipping this step would let anyone POST a fabricated
payload and log in as any user.
"""

import requests  # type: ignore[import-untyped]
from fastapi import HTTPException

_GOOGLE_AUTH_AVAILABLE = False
try:
    from google.auth.transport import requests as google_requests  # type: ignore[import-untyped]
    from google.oauth2 import id_token as google_id_token  # type: ignore[import-untyped]
    _GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    google_requests = None  # type: ignore[assignment]
    google_id_token = None  # type: ignore[assignment]

from .config import settings


def verify_google_id_token(raw_id_token: str) -> dict:
    if not settings.google_oauth_client_id:
        raise HTTPException(500, detail="Google Sign-In is not configured on this server")
    if not _GOOGLE_AUTH_AVAILABLE or google_id_token is None or google_requests is None:
        raise HTTPException(500, detail="Google Auth library is not installed on this server")
    try:
        payload = google_id_token.verify_oauth2_token(  # type: ignore[union-attr]
            raw_id_token, google_requests.Request(), settings.google_oauth_client_id  # type: ignore[union-attr]
        )
    except Exception as exc:
        raise HTTPException(401, detail="Invalid or expired Google token") from exc

    if payload.get("aud") != settings.google_oauth_client_id:
        raise HTTPException(401, detail="Google token audience mismatch")
    if not payload.get("email_verified", False):
        raise HTTPException(401, detail="Google account email is not verified")
    if "email" not in payload or "sub" not in payload:
        raise HTTPException(401, detail="Google token is missing required profile fields")
    return payload  # type: ignore[no-any-return]


def verify_facebook_access_token(raw_access_token: str) -> dict:
    if not settings.facebook_app_id or not settings.facebook_app_secret:
        raise HTTPException(500, detail="Facebook Login is not configured on this server")

    app_access_token = f"{settings.facebook_app_id}|{settings.facebook_app_secret}"

    try:
        debug_resp = requests.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": raw_access_token, "access_token": app_access_token},
            timeout=5,
        )
        debug_data = debug_resp.json().get("data", {})
    except requests.RequestException as exc:
        raise HTTPException(502, detail="Could not reach Facebook to verify token") from exc

    if not debug_data.get("is_valid"):
        raise HTTPException(401, detail="Invalid Facebook access token")
    if debug_data.get("app_id") != settings.facebook_app_id:
        raise HTTPException(401, detail="Facebook token was not issued for this app")

    try:
        profile_resp = requests.get(
            "https://graph.facebook.com/me",
            params={"fields": "id,name,email", "access_token": raw_access_token},
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(502, detail="Could not reach Facebook to fetch profile") from exc

    if profile_resp.status_code != 200:
        raise HTTPException(401, detail="Failed to fetch Facebook profile")

    profile = profile_resp.json()
    if "email" not in profile:
        raise HTTPException(
            400,
            detail="Your Facebook account has no email available. "
                   "Please allow email access or use another sign-in method.",
        )
    return profile
