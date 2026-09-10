"""Concurrency and Multithreading Load Tests for KRISS.

Validates that concurrent requests execute without database locking,
deadlocks, or race conditions during classification and audit logging.
"""
import concurrent.futures
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User
from app.auth import create_session_token, hash_password
from app.rate_limit import _hits


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_concurrent_classification_requests(client):
    _hits.clear()
    db = SessionLocal()
    user = db.query(User).filter(User.username == "test_concurrency_user").first()
    if not user:
        user = User(
            name="Concurrent User",
            username="test_concurrency_user",
            email="concurrent@kriss.lk",
            password_hash=hash_password("Pass1234!"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_session_token(db, user)
    db.close()
    headers = {"Authorization": f"Bearer {token}"}

    def send_request(idx):
        payload = {
            "message": f"Concurrent test transaction alert #{idx}. Account balance update.",
            "sender_no": f"077{idx:07d}"
        }
        return client.post("/api/classify", json=payload, headers=headers)

    # Send 20 concurrent requests simultaneously using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_request, i) for i in range(20)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 20
    assert all(r.status_code == 200 for r in results)
    sms_ids = [r.json()["sms_id"] for r in results]
    assert len(set(sms_ids)) == 20  # All IDs must be unique
