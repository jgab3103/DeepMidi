import time
from datetime import datetime, timezone

def now_ts() -> float:
    # high-resolution epoch time
    return time.time()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
