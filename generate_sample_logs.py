"""Generate a synthetic server log (JSON lines) for testing the analyzer.

The data is fake. It simulates normal traffic, scattered errors, a payment
outage in the middle of the file, and a few corrupted lines.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_FILE = Path("sample_logs") / "server.log"
TOTAL_LINES = 10_000
SEED = 42
SERVICES = ["auth", "payment", "orders", "inventory", "notifications"]
OUTAGE_START, OUTAGE_END = 6_000, 6_300

CORRUPTED_LINES = [
    "",
    "Segmentation fault (core dumped)",
    "42",
    '["unexpected", "array"]',
    '{"level": "ERROR", "message": "missing closing brace"',
    "[2026-10-20 10:15:02] ERROR plain text line, not JSON",
]


def make_entry(index, timestamp, rng):
    """Build one log entry as a dictionary."""
    service = rng.choice(SERVICES)

    if OUTAGE_START <= index < OUTAGE_END and rng.random() < 0.7:
        service = "payment"
        status = 503
        level = "CRITICAL" if rng.random() < 0.3 else "ERROR"
        message = "Upstream payment gateway unavailable"
        response_time = rng.randint(3000, 6000)
    else:
        roll = rng.random()
        if roll < 0.90:
            status, level, message = 200, "INFO", "Request completed"
            response_time = rng.randint(20, 300)
        elif roll < 0.95:
            status, level, message = rng.choice([400, 404, 429]), "WARNING", "Client error"
            response_time = rng.randint(10, 200)
        elif roll < 0.97:
            status = rng.choice([500, 502, 504])
            level = "ERROR"
            message = {500: "Internal server error", 502: "Bad gateway", 504: "Gateway timeout"}[status]
            response_time = rng.randint(800, 5000)
        elif roll < 0.985:
            status, level, message = 401, "ERROR", "Authentication failed repeatedly"
            response_time = rng.randint(50, 400)
        else:
            status, level, message = 500, "CRITICAL", "Database connection timeout"
            response_time = rng.randint(3000, 6000)

    return {
        "timestamp": timestamp.isoformat(),
        "level": level,
        "service": service,
        "status_code": status,
        "message": message,
        "response_time_ms": response_time,
    }


def main():
    rng = random.Random(SEED)
    timestamp = datetime(2026, 10, 20, 8, 0, 0)
    lines = []

    for index in range(TOTAL_LINES):
        timestamp += timedelta(seconds=rng.randint(0, 3))
        lines.append(json.dumps(make_entry(index, timestamp, rng)))

        if rng.random() < 0.015:
            lines.append(rng.choice(CORRUPTED_LINES))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} lines to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
