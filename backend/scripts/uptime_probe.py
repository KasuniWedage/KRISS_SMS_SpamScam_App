import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


def probe(url: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        response = requests.get(url, timeout=timeout)
        latency = round((time.perf_counter() - started) * 1000, 3)
        payload = response.json() if "json" in response.headers.get("content-type", "") else {}
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "up": response.ok, "status": response.status_code, "latency_ms": latency, "model_ready": payload.get("model_ready")}
    except requests.RequestException as exc:
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "up": False, "status": None, "latency_ms": None, "error": type(exc).__name__}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    result = probe(args.url, args.timeout)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result) + "\n")
    print(json.dumps(result))
