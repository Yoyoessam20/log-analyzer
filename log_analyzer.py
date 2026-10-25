"""Automated Application Log Analyzer.

Reads a JSON-lines server log, finds critical errors (HTTP 5xx, ERROR and
CRITICAL levels) and writes a structured JSON report for the support team.

Usage:
    python log_analyzer.py sample_logs/server.log -o alerts.json
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone

SERVER_ERROR_MIN = 500


def classify(entry):
    """Return 'critical', 'high' or None for one parsed log entry."""
    status = entry.get("status_code")
    level = str(entry.get("level", "")).upper()

    if (isinstance(status, int) and status >= SERVER_ERROR_MIN) or level == "CRITICAL":
        return "critical"
    if level == "ERROR":
        return "high"
    return None


def analyze(path):
    """Scan the log file line by line.

    Returns (lines_read, malformed_lines, alerts). A bad line never stops the run.
    """
    lines_read = 0
    malformed = 0
    alerts = []

    with open(path, encoding="utf-8", errors="replace") as log_file:
        for line_number, raw_line in enumerate(log_file, start=1):
            line = raw_line.strip()
            if not line:
                continue

            lines_read += 1

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue

            if not isinstance(entry, dict):
                malformed += 1
                continue

            severity = classify(entry)
            if severity:
                alerts.append(
                    {
                        "line": line_number,
                        "severity": severity,
                        "timestamp": entry.get("timestamp"),
                        "service": entry.get("service") or "unknown",
                        "level": entry.get("level"),
                        "status_code": entry.get("status_code"),
                        "message": entry.get("message"),
                    }
                )

    return lines_read, malformed, alerts


def build_report(path, lines_read, malformed, alerts):
    """Group the alerts into a report dictionary ready to be saved as JSON."""
    by_status = Counter(
        str(alert["status_code"])
        for alert in alerts
        if alert["status_code"] is not None
    )

    return {
        "summary": {
            "log_file": str(path),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "lines_read": lines_read,
            "malformed_lines": malformed,
            "alerts_found": len(alerts),
        },
        "by_severity": dict(Counter(a["severity"] for a in alerts).most_common()),
        "by_service": dict(Counter(a["service"] for a in alerts).most_common()),
        "by_status_code": dict(by_status.most_common()),
        "alerts": alerts,
    }


def main():
    """Command-line entry point. Returns 0 on success, 1 on failure."""
    parser = argparse.ArgumentParser(
        description="Find critical errors in a JSON-lines log and write a JSON report."
    )
    parser.add_argument("log_file", help="path to the log file to analyze")
    parser.add_argument(
        "-o", "--output", default="alerts.json", help="report file (default: alerts.json)"
    )
    args = parser.parse_args()

    try:
        lines_read, malformed, alerts = analyze(args.log_file)
    except OSError as error:
        print(f"Cannot read log file: {error}", file=sys.stderr)
        return 1

    report = build_report(args.log_file, lines_read, malformed, alerts)

    try:
        with open(args.output, "w", encoding="utf-8") as report_file:
            json.dump(report, report_file, indent=2, ensure_ascii=False)
    except OSError as error:
        print(f"Cannot write report: {error}", file=sys.stderr)
        return 1

    print(f"Lines read      : {lines_read}")
    print(f"Malformed lines : {malformed}")
    print(f"Alerts found    : {len(alerts)}")
    print(f"Report saved to : {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
