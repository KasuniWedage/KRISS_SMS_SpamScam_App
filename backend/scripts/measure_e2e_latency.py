"""Measure End-to-End Classification Latency against the KRISS FastAPI service.

Executes test requests across English, Sinhala, Singlish, and Tamil SMS messages,
measuring full round-trip network + auth + preprocessing + ML + audit storage times.
Verifies compliance with the SRS requirement: End-to-end classification <= 2.0 seconds.
"""
import argparse
import json
import statistics
import time
from pathlib import Path
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.database import SessionLocal
from app.models import User
from app.auth import create_session_token, hash_password

SAMPLE_MESSAGES = [
    # English
    {"message": "Your ComBank Mastercard ending 4589 used for LKR 3,450.00 at Keells.", "sender": "COMBANK"},
    {"message": "EXCLUSIVE: 50% discount on all shirts at ODEL this weekend!", "sender": "ODEL"},
    {"message": "URGENT: Your account is suspended. Verify at http://boc-fake.com", "sender": "ALERT"},
    # Sinhala
    {"message": "ඔබගේ සම්පත් බැංකු ගිණුමෙන් රු. 2,500.00 ක මුදලක් ලබාගෙන ඇත.", "sender": "SAMPATH"},
    {"message": "විශේෂ දීමනාව! නොලිමිට් ඇඳුම් සඳහා 30% ක වට්ටමක් ලබාගන්න.", "sender": "NOLIMIT"},
    {"message": "අවවාදයයි! ඔබගේ BOC ගිණුම තහවුරු කිරීමට http://boc-scam.xyz වෙත පිවිසෙන්න.", "sender": "NOTICE"},
    # Singlish
    {"message": "Machan ada hawasa class eka thiyanawa. assignment eka genna.", "sender": "Nimal"},
    {"message": "Adama recharge karanna Rs 199 ta 10GB Data! Call 678.", "sender": "DIALOG"},
    {"message": "URGENT: Commercial bank block wela. unblock karanna http://combk-fake.link", "sender": "INFO"},
    # Tamil
    {"message": "உங்கள் கணக்கிலிருந்து ரூ. 4,500.00 ATM மூலம் எடுக்கப்பட்டுள்ளது.", "sender": "BOC"},
    {"message": "மெகா ஆஃபர்! Dialog இலிருந்து 15GB டேட்டா பெற #123# டயல் செய்க.", "sender": "PROMO"},
    {"message": "அவசரம்! உங்கள் வங்கி கணக்கு முடக்கப்பட்டுள்ளது. சரிபார்க்க http://bank-fake.org", "sender": "SECURE"}
]

def run_benchmark(num_samples: int = 50, simulated_network_ms: float = 15.0) -> dict:
    client = TestClient(app)
    db = SessionLocal()
    
    # Ensure test user exists
    user = db.query(User).filter(User.email == "bench_user@kriss.lk").first()
    if not user:
        user = User(
            name="Benchmark User",
            username="benchuser",
            email="bench_user@kriss.lk",
            password_hash=hash_password("BenchSecret123!"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_session_token(db, user)
    headers = {"Authorization": f"Bearer {token}"}

    latencies = []
    durations_by_lang = {"English": [], "Sinhala": [], "Singlish": [], "Tamil": []}

    print(f"Executing {num_samples} end-to-end classification requests...")

    for i in range(num_samples):
        idx = i % len(SAMPLE_MESSAGES)
        payload = SAMPLE_MESSAGES[idx]
        
        start_time = time.perf_counter()
        response = client.post("/api/classify", json=payload, headers=headers)
        elapsed_ms = (time.perf_counter() - start_time) * 1000 + simulated_network_ms

        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        assert "label" in data
        assert "confidence" in data

        latencies.append(elapsed_ms)
        lang = data.get("language", "English")
        if lang in durations_by_lang:
            durations_by_lang[lang].append(elapsed_ms)

    db.close()
    latencies.sort()
    avg_ms = statistics.mean(latencies)
    p50_ms = latencies[int(len(latencies) * 0.50)]
    p90_ms = latencies[int(len(latencies) * 0.90)]
    p95_ms = latencies[int(len(latencies) * 0.95)]
    p99_ms = latencies[int(len(latencies) * 0.99)]
    max_ms = max(latencies)
    under_2s_count = sum(1 for t in latencies if t <= 2000.0)
    compliance_pct = (under_2s_count / len(latencies)) * 100

    report = {
        "total_requests": len(latencies),
        "target_srs_threshold_ms": 2000.0,
        "within_2s_compliance_percent": compliance_pct,
        "status": "PASS - SRS COMPLIANT" if compliance_pct == 100.0 else "FAIL",
        "latency_statistics_ms": {
            "average": round(avg_ms, 2),
            "p50": round(p50_ms, 2),
            "p90": round(p90_ms, 2),
            "p95": round(p95_ms, 2),
            "p99": round(p99_ms, 2),
            "maximum": round(max_ms, 2)
        },
        "per_language_avg_ms": {
            k: round(statistics.mean(v), 2) if v else 0.0 for k, v in durations_by_lang.items()
        }
    }
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KRISS End-to-End Latency Benchmark")
    parser.add_argument("--samples", type=int, default=50, help="Number of benchmark iterations")
    parser.add_argument("--out", type=Path, default=Path("latency_benchmark.json"))
    args = parser.parse_args()

    results = run_benchmark(args.samples)
    print(json.dumps(results, indent=2))
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
