from __future__ import annotations

from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools import render_action_report as action_report


def report_fixture(*, failed: bool = False, comparison: bool = False) -> dict[str, object]:
    result = {
        "budget_id": "main-process-p95",
        "description": "Process time policy.",
        "profile": "main_scene",
        "metric": "median_p95_process_time",
        "measured_value": 11.58 if failed else 0.5,
        "maximum_value": 2,
        "unit": "ms",
        "evidence_id": "opaque-candidate",
        "status": "failed" if failed else "passed",
        "explanation": "Fixed deterministic result.",
    }
    report: dict[str, object] = {
        "schema_version": 2 if comparison else 1,
        "deterministic_status": "budget_failed" if failed else "passed",
        "validator": {
            "status": "passed",
            "candidate_file_count": 3,
            "validated_file_count": 3,
            "results_directory": "results/candidate",
        },
        "budget": {
            "status": "failed" if failed else "passed",
            "summary": {"total": 1, "passed": 0 if failed else 1, "failed": 1 if failed else 0},
            "results": [result],
            "limitations": [],
        },
        "investigation": {
            "mode": "never",
            "requested": False,
            "api_request_attempted": False,
            "outcome": "not_requested",
            "rule_ids": [],
            "error_category": None,
            "report": None,
        },
        "authoritative_exit_code": 1 if failed else 0,
        "authoritative_exit_reason": (
            "Validation passed, but one or more configured budgets failed."
            if failed else "Validation passed and every configured budget passed."
        ),
    }
    if comparison:
        report["comparison"] = {
            "status": "failed" if failed else "passed",
            "summary": {"total": 1, "passed": 0 if failed else 1, "failed": 1 if failed else 0},
            "results": [
                {
                    "budget_id": "main-process-p95",
                    "description": "Process time policy.",
                    "profile": "main_scene",
                    "metric": "median_p95_process_time",
                    "unit": "ms",
                    "baseline_value": 0 if failed else 0.5,
                    "candidate_value": 11.58 if failed else 0.5,
                    "delta": 11.58 if failed else 0,
                    "increase_percent": None if failed else 0,
                    "baseline_evidence_id": "opaque-base",
                    "candidate_evidence_id": "opaque-candidate",
                    "absolute": {"maximum": 2, "status": "failed" if failed else "passed"},
                    "relative": {"maximum_increase_percent": 20, "status": "failed" if failed else "passed"},
                    "status": "failed" if failed else "passed",
                }
            ],
            "limitations": [],
        }
    return report


def grounded_report(disclosure: str) -> str:
    return f"""## Validation status
{disclosure}

## Verified facts
Facts are rendered locally.

## Possible explanations
No hypothesis was accepted.

## Recommended next investigation
Repeat a controlled capture.

## Remaining uncertainty
The available evidence does not establish the root cause.
"""


def calibration_fixture() -> dict[str, object]:
    policy = {
        "schema_version": 3,
        "budgets": [{
            "id": "main-scene-process-p95", "profile": "main_scene",
            "metric": "median_p95_process_time", "maximum": 0.8,
            "maximum_increase_percent": 20, "unit": "ms",
            "description": "Balanced process policy.",
        }],
    }
    return {
        "report_type": "performance_budget_calibration",
        "schema_version": 1,
        "status": "proposal_generated",
        "validator": {
            "status": "passed", "candidate_file_count": 5,
            "validated_file_count": 5, "results_directory": "results",
        },
        "calibration": {
            "minimum_validated_runs": 3, "preset": "balanced",
            "proposal_authoritative": False,
        },
        "recommendations": [{
            "budget_id": "main-scene-process-p95", "evidence_id": "opaque-process",
            "margin_percent": 50, "metric": "median_p95_process_time",
            "observed_value": 0.529, "profile": "main_scene",
            "proposed_maximum": 0.8, "relative_allowance_percent": 20,
            "run_count": 5, "unit": "ms",
        }],
        "proposed_policy": policy,
        "limitations": [{"id": "CL1", "statement": "Proposal only."}],
    }


class ActionReportTests(unittest.TestCase):
    def test_observed_absolute_failure_is_actionable_and_annotated_once(self) -> None:
        report = action_report.validate_report(report_fixture(failed=True))
        log = action_report.render_log(report, "evidence-name")
        self.assertIn("11.58 ms > 2 ms", log)
        self.assertIn("Authoritative exit 1", log)
        self.assertEqual(log.count("::error title="), 1)
        self.assertIn("main-process-p95", log)

    def test_absolute_pass_is_listed_without_error_annotation(self) -> None:
        report = action_report.validate_report(report_fixture())
        log = action_report.render_log(report, "evidence-name")
        self.assertIn("0.5 ms <= 2 ms", log)
        self.assertNotIn("::error", log)

    def test_comparison_combines_absolute_and_relative_failure(self) -> None:
        report = action_report.validate_report(report_fixture(failed=True, comparison=True))
        log = action_report.render_log(report, "evidence-name")
        self.assertEqual(log.count("::error title="), 1)
        self.assertIn("absolute: 11.58 ms > 2 ms", log)
        self.assertIn("relative: baseline 0", log)
        self.assertIn("increase undefined%25", log)

    def test_github_command_values_are_escaped(self) -> None:
        report = report_fixture(failed=True)
        report["budget"]["results"][0]["budget_id"] = "rule:one,100%\nnext"  # type: ignore[index]
        log = action_report.render_log(action_report.validate_report(report), "evidence")
        annotation = next(line for line in log.splitlines() if line.startswith("::error"))
        self.assertIn("%3A", annotation)
        self.assertIn("%2C", annotation)
        self.assertIn("%25", annotation)
        self.assertIn("%0A", annotation)
        self.assertNotIn("\nnext failed", annotation)

    def test_evaluation_error_emits_one_safe_annotation(self) -> None:
        report = report_fixture()
        report.update(
            deterministic_status="error",
            authoritative_exit_code=2,
            authoritative_exit_reason="budget configuration is invalid",
        )
        report["validator"]["status"] = "not_run"  # type: ignore[index]
        report["budget"]["status"] = "error"  # type: ignore[index]
        report["budget"]["results"] = []  # type: ignore[index]
        log = action_report.render_log(action_report.validate_report(report), "evidence")
        self.assertEqual(log.count("::error title="), 1)
        self.assertIn("evaluation error", log)

    def test_summary_contains_table_authority_and_evidence_guidance(self) -> None:
        summary = action_report.render_summary(
            action_report.validate_report(report_fixture(failed=True, comparison=True)),
            "performance-evidence",
        )
        self.assertIn("Deterministic validation and budgets decide", summary)
        self.assertIn("| `main-process-p95` |", summary)
        self.assertIn("## Protected-base comparison", summary)
        self.assertIn("Optional AI explanation — non-authoritative", summary)
        self.assertIn("Download artifact `performance-evidence`", summary)

    def test_accepted_and_fallback_ai_are_shown(self) -> None:
        for outcome, disclosure in (
            ("accepted", action_report.MODEL_DISCLOSURE),
            ("fallback", action_report.FALLBACK_DISCLOSURE),
        ):
            with self.subTest(outcome=outcome):
                report = report_fixture()
                report["investigation"].update(  # type: ignore[union-attr]
                    mode="always", requested=True, api_request_attempted=True,
                    outcome=outcome, report=grounded_report(disclosure),
                )
                summary = action_report.render_summary(action_report.validate_report(report), "evidence")
                self.assertIn(disclosure, summary)
                self.assertIn("### Verified facts", summary)

    def test_skipped_and_api_error_show_only_safe_status(self) -> None:
        for outcome, category in (("skipped_no_key", None), ("api_error", "rate_limit")):
            report = report_fixture()
            report["investigation"].update(outcome=outcome, error_category=category)  # type: ignore[union-attr]
            summary = action_report.render_summary(action_report.validate_report(report), "evidence")
            self.assertIn(category or outcome, summary)
            self.assertNotIn("raw response", summary)

    def test_unsafe_ai_text_is_suppressed(self) -> None:
        unsafe_values = (
            "sk-" + "proj-" + "abcdefghijklmnopqrstuvwxyz123456",
            "C:\\Users\\person\\private.json",
            "source revision: secret-value",
        )
        for unsafe in unsafe_values:
            with self.subTest(unsafe=unsafe):
                report = report_fixture()
                report["investigation"].update(  # type: ignore[union-attr]
                    outcome="accepted",
                    report=grounded_report(action_report.MODEL_DISCLOSURE) + unsafe,
                )
                summary = action_report.render_summary(action_report.validate_report(report), "evidence")
                self.assertNotIn(unsafe, summary)
                self.assertIn("omitted", summary)

    def test_cli_appends_summary_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "report.json"
            summary_path = root / "summary.md"
            report_path.write_text(json.dumps(report_fixture(failed=True)), encoding="utf-8")
            outputs = []
            for _ in range(2):
                summary_path.write_text("", encoding="utf-8")
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = action_report.main(
                        ["--summary-file", str(summary_path), "--artifact-name", "evidence", str(report_path)]
                    )
                self.assertEqual(exit_code, 0)
                outputs.append((stdout.getvalue(), summary_path.read_text(encoding="utf-8")))
            self.assertEqual(outputs[0], outputs[1])

    def test_malformed_report_fails_without_exposing_path_or_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "private-report.json"
            report_path.write_text("not json", encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = action_report.main(
                    ["--summary-file", str(root / "summary.md"), "--artifact-name", "evidence", str(report_path)]
                )
            self.assertEqual(exit_code, 2)
            self.assertIn("failed safely", stdout.getvalue())
            self.assertNotIn(str(root), stdout.getvalue())

    def test_render_does_not_modify_canonical_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "report.json"
            original = json.dumps(report_fixture(), sort_keys=True, separators=(",", ":")) + "\n"
            report_path.write_text(original, encoding="utf-8")
            action_report.render(report_path, root / "summary.md", "evidence")
            self.assertEqual(report_path.read_text(encoding="utf-8"), original)

    def test_calibration_dispatch_is_proposal_only_and_actionable(self) -> None:
        report = action_report.validate_calibration_report(calibration_fixture())
        log = action_report.render_calibration_log(report, "calibration-evidence")
        summary = action_report.render_calibration_summary(report, "calibration-evidence")
        self.assertIn("PROPOSAL ONLY", log)
        self.assertIn("0.529 ms", log)
        self.assertIn("0.8 ms", log)
        self.assertIn("relative allowance 20%", log)
        self.assertNotIn("::error", log)
        self.assertIn("Proposal only—not an enforced verdict", summary)
        self.assertIn("Apply it explicitly", summary)
        self.assertIn("Enable protected-base comparison in a later pull request", summary)

    def test_calibration_cli_is_deterministic_and_suppresses_unsafe_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "calibration.json"
            summary_path = root / "summary.md"
            report_path.write_text(json.dumps(calibration_fixture()), encoding="utf-8")
            outputs = []
            for _ in range(2):
                summary_path.write_text("", encoding="utf-8")
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    code = action_report.main([
                        "--summary-file", str(summary_path), "--artifact-name", "evidence", str(report_path)
                    ])
                self.assertEqual(code, 0)
                outputs.append((stdout.getvalue(), summary_path.read_text(encoding="utf-8")))
            self.assertEqual(outputs[0], outputs[1])
            unsafe = calibration_fixture()
            unsafe["validator"]["results_directory"] = "C:\\Users\\person\\private"  # type: ignore[index]
            with self.assertRaises(action_report.ActionReportError):
                action_report.validate_calibration_report(unsafe)


if __name__ == "__main__":
    unittest.main()
