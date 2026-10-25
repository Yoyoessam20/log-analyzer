import json
import os
import tempfile
import unittest

from log_analyzer import analyze, build_report, classify, main


def write_temp_log(content, binary=False):
    """Create a temporary log file and return its path."""
    mode = "wb" if binary else "w"
    handle = tempfile.NamedTemporaryFile(mode=mode, suffix=".log", delete=False)
    handle.write(content)
    handle.close()
    return handle.name


class ClassifyTests(unittest.TestCase):
    def test_5xx_is_critical(self):
        self.assertEqual(classify({"status_code": 503, "level": "INFO"}), "critical")

    def test_critical_level_is_critical(self):
        self.assertEqual(classify({"status_code": 200, "level": "CRITICAL"}), "critical")

    def test_error_level_is_high(self):
        self.assertEqual(classify({"status_code": 401, "level": "ERROR"}), "high")

    def test_level_is_case_insensitive(self):
        self.assertEqual(classify({"level": "error"}), "high")

    def test_normal_entry_is_ignored(self):
        self.assertIsNone(classify({"status_code": 200, "level": "INFO"}))

    def test_missing_fields_do_not_crash(self):
        self.assertIsNone(classify({}))


class AnalyzeTests(unittest.TestCase):
    def tearDown(self):
        for path in getattr(self, "paths", []):
            os.remove(path)

    def make_log(self, content, binary=False):
        self.paths = getattr(self, "paths", [])
        path = write_temp_log(content, binary)
        self.paths.append(path)
        return path

    def test_bad_lines_are_counted_and_do_not_stop_the_run(self):
        path = self.make_log(
            '{"level": "ERROR", "status_code": 500, "service": "auth"}\n'
            "this is not json\n"
            "\n"
            "42\n"
            '{"level": "INFO", "status_code": 200}\n'
        )
        lines_read, malformed, alerts = analyze(path)
        self.assertEqual(lines_read, 4)
        self.assertEqual(malformed, 2)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["line"], 1)
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_invalid_utf8_bytes_do_not_crash(self):
        path = self.make_log(
            b'{"level": "ERROR", "service": "auth"}\n\xff\xfe broken bytes\n',
            binary=True,
        )
        lines_read, malformed, alerts = analyze(path)
        self.assertEqual(lines_read, 2)
        self.assertEqual(malformed, 1)
        self.assertEqual(len(alerts), 1)

    def test_missing_service_becomes_unknown(self):
        path = self.make_log('{"level": "ERROR"}\n')
        _, _, alerts = analyze(path)
        self.assertEqual(alerts[0]["service"], "unknown")


class ReportTests(unittest.TestCase):
    def test_report_counts_and_is_json_serializable(self):
        alerts = [
            {"line": 1, "severity": "critical", "service": "payment", "status_code": 503},
            {"line": 2, "severity": "critical", "service": "payment", "status_code": 503},
            {"line": 3, "severity": "high", "service": "auth", "status_code": None},
        ]
        report = build_report("x.log", 10, 1, alerts)
        self.assertEqual(report["summary"]["alerts_found"], 3)
        self.assertEqual(report["by_severity"], {"critical": 2, "high": 1})
        self.assertEqual(report["by_service"], {"payment": 2, "auth": 1})
        self.assertEqual(report["by_status_code"], {"503": 2})
        json.dumps(report)


class CommandLineTests(unittest.TestCase):
    def test_missing_file_returns_error_code(self):
        import sys
        from unittest import mock

        with mock.patch.object(sys, "argv", ["log_analyzer.py", "does_not_exist.log"]):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
