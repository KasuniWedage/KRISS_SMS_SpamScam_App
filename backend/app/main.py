from pathlib import Path
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import inspect, text

from .database import Base, engine
from .ml_service import ml_service
from .routers import admin_routes, auth_routes, batch_routes, classification_routes, dataset_admin_routes, dataset_routes, history_routes, user_routes
from .config import settings
from .observability import ObservabilityMiddleware, backfill_audit_seals

settings.validate_security()

Base.metadata.create_all(bind=engine)
backfill_audit_seals()
_existing_columns = {c["name"] for c in inspect(engine).get_columns("mobile_users")}
if "auto_delete_history" not in _existing_columns:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE mobile_users ADD COLUMN auto_delete_history BOOLEAN NOT NULL DEFAULT 0"))

# Social auth columns
_social_auth_columns = {
    "auth_provider": "ALTER TABLE mobile_users ADD COLUMN auth_provider VARCHAR(20) NOT NULL DEFAULT 'email'",
    "google_id": "ALTER TABLE mobile_users ADD COLUMN google_id VARCHAR(255)",
    "facebook_id": "ALTER TABLE mobile_users ADD COLUMN facebook_id VARCHAR(255)",
    "firebase_uid": "ALTER TABLE mobile_users ADD COLUMN firebase_uid VARCHAR(128)",
    "email_verified": "ALTER TABLE mobile_users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0",
}
with engine.begin() as connection:
    for column_name, ddl in _social_auth_columns.items():
        if column_name not in _existing_columns:
            connection.execute(text(ddl))

# Feedback status/review columns
_feedback_columns = {c["name"] for c in inspect(engine).get_columns("feedback")}
if "status" not in _feedback_columns:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE feedback ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'"))
if "review_note" not in _feedback_columns:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE feedback ADD COLUMN review_note VARCHAR(255)"))

app = FastAPI(title="KRISS Hybrid SMS Spam & Scam Detection API", version="1.0.0")
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth_routes.router)
app.include_router(classification_routes.router)
app.include_router(batch_routes.router)
app.include_router(history_routes.router)
app.include_router(user_routes.router)
app.include_router(admin_routes.router)
app.include_router(dataset_admin_routes.router)
app.include_router(dataset_routes.router)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/admin", tags=["System"], response_class=FileResponse)
def admin_panel():
    admin_html = Path(__file__).resolve().parent / "static" / "admin.html"
    return FileResponse(str(admin_html))

@app.get("/", tags=["System"])
def root():
    return {
        "name": "KRISS Hybrid SMS Spam & Scam Detection API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "admin": "/admin",
        "model_ready": ml_service.ready,
    }

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/health")
def health():
    version = (
        ml_service.metadata.get("model_version")
        or ml_service.metadata.get("model_name")
        or ("v2.5-Multilingual" if ml_service.ready else "not-loaded")
    )
    return {
        "status": "online",
        "model_ready": ml_service.ready,
        "model_version": version,
    }
