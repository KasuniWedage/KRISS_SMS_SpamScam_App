from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock
from fastapi import HTTPException

_hits = defaultdict(deque)
_lock = Lock()
_MAX_KEYS = 10_000

def check_rate_limit(key: str, limit: int = 60, window_seconds: int = 60):
    now = datetime.utcnow()
    with _lock:
        if len(_hits) >= _MAX_KEYS and key not in _hits:
            stale = [k for k, values in _hits.items() if not values or values[-1] < now - timedelta(hours=1)]
            for stale_key in stale:
                _hits.pop(stale_key, None)
            if len(_hits) >= _MAX_KEYS:
                raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")
        q = _hits[key]
        cutoff = now - timedelta(seconds=window_seconds)
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")
        q.append(now)
