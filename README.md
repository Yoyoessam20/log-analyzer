# Automated Application Log Analyzer

A small Python command-line tool that reads a server log, finds the critical errors
(HTTP 5xx, `ERROR`, `CRITICAL`) and writes a structured JSON report that an
application support team can read straight away.

It is built for the first minutes of an incident: instead of scrolling through
thousands of log lines, you get a summary of **what failed, where, and how often**.

## Features

- Reads the log **line by line**, so large files do not fill the memory.
- **Never crashes on bad data**: corrupted lines, empty lines, valid JSON that is not
  an object, and invalid UTF-8 bytes are skipped and counted.
- Classifies each problem entry by severity:

  | Severity   | Rule                                            |
  |------------|-------------------------------------------------|
  | `critical` | `status_code` >= 500, or `level` is `CRITICAL`  |
  | `high`     | `level` is `ERROR` (and not already critical)   |

- Groups the results by severity, service and HTTP status code.
- Saves everything to a JSON report (`alerts.json` by default).
- Pure Python standard library. **No dependencies.**

## Requirements

- Python 3.9 or newer

## Quick start

```bash
git clone https://github.com/Yoyoessam20/log-analyzer.git
cd log-analyzer

# 1. Create a synthetic 10,000+ line log to play with
python generate_sample_logs.py

# 2. Analyze it
python log_analyzer.py sample_logs/server.log -o alerts.json
```

Console output on the included sample log:

```
Lines read      : 10112
Malformed lines : 112
Alerts found    : 663
Report saved to : alerts.json
```

> The sample log is **synthetic data** created by `generate_sample_logs.py`
> (fixed random seed, so the numbers above are reproducible). It simulates normal
> traffic, scattered errors, a payment-gateway outage in the middle of the file,
> and some corrupted lines.

## Expected log format

One JSON object per line:

```json
{"timestamp": "2026-10-20T08:00:09", "level": "ERROR", "service": "payment", "status_code": 503, "message": "Upstream payment gateway unavailable", "response_time_ms": 4210}
```

Only `level` and `status_code` are used for classification. Missing fields are tolerated.

## Example report

```json
{
  "summary": {
    "log_file": "sample_logs/server.log",
    "generated_at": "2026-10-25T12:04:38+00:00",
    "lines_read": 10112,
    "malformed_lines": 112,
    "alerts_found": 663
  },
  "by_severity": { "critical": 527, "high": 136 },
  "by_service": { "payment": 295, "auth": 110, "inventory": 94, "notifications": 85, "orders": 79 },
  "by_status_code": { "500": 204, "503": 202, "401": 136, "502": 62, "504": 59 },
  "alerts": [
    {
      "line": 10,
      "severity": "critical",
      "timestamp": "2026-10-20T08:00:09",
      "service": "orders",
      "level": "CRITICAL",
      "status_code": 500,
      "message": "Database connection timeout"
    }
  ]
}
```

In this sample, the `payment` service stands out immediately with 295 alerts, which is
exactly the kind of signal a support engineer needs when starting root cause analysis.

## Project structure

```
log-analyzer/
├── log_analyzer.py          # the analyzer (main program)
├── generate_sample_logs.py  # creates the synthetic sample log
├── test_log_analyzer.py     # unit tests
├── sample_logs/
│   └── server.log           # generated sample data
└── README.md
```

## Run the tests

```bash
python -m unittest -v
```

The tests cover severity rules, corrupted input (including invalid bytes),
report counting, and the missing-file error path.

## Error handling

| Situation                         | Behavior                                   |
|-----------------------------------|--------------------------------------------|
| Line is not valid JSON            | Skipped and counted in `malformed_lines`   |
| Line is valid JSON but not an object (e.g. `42`) | Skipped and counted        |
| Empty line                        | Ignored                                    |
| Invalid UTF-8 bytes               | Replaced, the line is then handled normally|
| Log file missing or unreadable    | Clear message on stderr, exit code `1`     |

## Limitations and roadmap

- Only JSON-lines logs are supported. Plain-text lines such as
  `[2026-10-20 10:15:02] ERROR ...` are currently counted as malformed.
- Planned improvements:
  - [ ] Parse plain-text logs with regular expressions
  - [ ] Analyze trends over time with Pandas (errors per minute, outage windows)
  - [ ] Store alerts in a SQL database for historical queries
  - [ ] Generate a human-readable RCA summary (Markdown)
