from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools import run_submission_evaluation as evaluation


class SubmissionEvaluationContractTests(unittest.TestCase):
    def test_case_manifest_has_ten_unique_cases_and_one_challenge(self) -> None:
        manifest = evaluation.load_cases(evaluation.REPOSITORY_ROOT / evaluation.DEFAULT_CASES)
        self.assertEqual(len(manifest["cases"]), 10)
        self.assertEqual(len({item["id"] for item in manifest["cases"]}), 10)
        challenges = [item["id"] for item in manifest["cases"] if item.get("challenging")]
        self.assertEqual(challenges, ["relative-only-process-regression"])

    def test_integrity_manifest_verifies_frozen_baseline_and_final_tools(self) -> None:
        manifest = evaluation.verify_integrity(evaluation.REPOSITORY_ROOT / evaluation.DEFAULT_INTEGRITY)
        entries = {item["path"]: item["sha256"] for item in manifest["files"]}
        self.assertEqual(
            entries["evaluation/baseline/validate_results.py"],
            "6277baaacfc9a62734e3b72d94fa4fe03e742c5a78fd8b40d52b2f0c3226d412",
        )
        self.assertIn("tools/run_guardian.py", entries)
        self.assertIn("evaluation/fixtures/synthetic/healthy-20260828T193246205Z-run-01.json", entries)

    def test_integrity_mismatch_fails_safely(self) -> None:
        with patch.object(evaluation, "_sha256", return_value="0" * 64):
            with self.assertRaisesRegex(evaluation.EvaluationError, "integrity mismatch"):
                evaluation.verify_integrity(evaluation.REPOSITORY_ROOT / evaluation.DEFAULT_INTEGRITY)

    def test_repository_member_rejects_absolute_and_traversal_paths(self) -> None:
        for value in (str(evaluation.REPOSITORY_ROOT), "../outside.json"):
            with self.subTest(value=value):
                with self.assertRaises(evaluation.EvaluationError):
                    evaluation._repository_member(value, kind="case manifest file")

    def test_subprocess_boundary_is_bounded_and_never_uses_shell(self) -> None:
        completed = subprocess.CompletedProcess(["fixed"], 0, "ok", "")
        with patch.object(evaluation.subprocess, "run", return_value=completed) as runner:
            result = evaluation._run(["fixed"])
        self.assertIs(result, completed)
        kwargs = runner.call_args.kwargs
        self.assertFalse(kwargs["shell"])
        self.assertFalse(kwargs["check"])
        self.assertTrue(kwargs["capture_output"])
        self.assertEqual(kwargs["timeout"], evaluation.TIMEOUT_SECONDS)

    def test_timeout_and_os_error_are_safe(self) -> None:
        with patch.object(
            evaluation.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["fixed"], evaluation.TIMEOUT_SECONDS),
        ):
            with self.assertRaisesRegex(evaluation.EvaluationError, "timed out"):
                evaluation._run(["fixed"])
        with patch.object(evaluation.subprocess, "run", side_effect=OSError("private raw error")):
            with self.assertRaisesRegex(evaluation.EvaluationError, "could not be launched") as caught:
                evaluation._run(["fixed"])
        self.assertNotIn("private raw error", str(caught.exception))

    def test_malformed_case_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cases.json"
            path.write_text('{"schema_version":1,"cases":[]}', encoding="utf-8")
            with self.assertRaisesRegex(evaluation.EvaluationError, "fields or schema"):
                evaluation.load_cases(path)


class SubmissionEvaluationResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = evaluation.run_evaluation()

    def test_real_ten_case_evaluation_passes_every_final_oracle(self) -> None:
        self.assertEqual(self.report["baseline"]["correct_actionable_outcomes"], 1)
        self.assertEqual(self.report["baseline"]["percent"], 10.0)
        self.assertEqual(self.report["final"]["correct_actionable_outcomes"], 10)
        self.assertEqual(self.report["final"]["percent"], 100.0)
        self.assertEqual(self.report["change_percentage_points"], 90.0)
        self.assertTrue(all(item["final"]["correct_actionable_outcome"] for item in self.report["cases"]))

    def test_challenge_records_absolute_pass_and_relative_failure(self) -> None:
        challenge = next(item for item in self.report["cases"] if item["challenging"])
        rule = challenge["final"]["evidence"]["comparison_rules"]["main-scene-process-p95"]
        self.assertEqual(rule["baseline"], 0.5)
        self.assertEqual(rule["candidate"], 0.61)
        self.assertEqual(rule["delta"], 0.11)
        self.assertEqual(rule["increase_percent"], 22.0)
        self.assertEqual(rule["absolute_status"], "passed")
        self.assertEqual(rule["relative_status"], "failed")

    def test_failures_include_named_measurements_and_thresholds(self) -> None:
        by_id = {item["id"]: item for item in self.report["cases"]}
        process = by_id["absolute-process-failure"]["final"]["evidence"]["rules"]["main-scene-process-p95"]
        nodes = by_id["absolute-node-failure"]["final"]["evidence"]["rules"]["main-scene-peak-nodes"]
        self.assertEqual(process, {"maximum": 0.4, "measured": 0.5, "status": "failed", "unit": "ms"})
        self.assertEqual(nodes, {"maximum": 2, "measured": 3.0, "status": "failed", "unit": "nodes"})

    def test_malformed_case_has_safe_marker_without_raw_error_text(self) -> None:
        malformed = next(item for item in self.report["cases"] if item["id"] == "malformed-evidence-error")
        self.assertEqual(malformed["final"]["outcome"], "safe_error")
        self.assertTrue(malformed["final"]["evidence"]["error_markers"]["missing_schema_version"])
        self.assertNotIn("errors", malformed["final"]["evidence"])

    def test_calibration_recommendations_match_balanced_formulas(self) -> None:
        item = next(item for item in self.report["cases"] if item["id"] == "calibration-proposal")
        recommendations = item["final"]["evidence"]["recommendations"]
        self.assertEqual(recommendations["main_scene-process-p95"]["proposed_maximum"], 0.8)
        self.assertEqual(recommendations["main_scene-peak-nodes"]["proposed_maximum"], 4)
        self.assertEqual(recommendations["main_scene-peak-objects"]["proposed_maximum"], 24)

    def test_score_recomputation_matches_raw_cases(self) -> None:
        for side in ("baseline", "final"):
            count = sum(1 for item in self.report["cases"] if item[side]["correct_actionable_outcome"])
            self.assertEqual(count, self.report[side]["correct_actionable_outcomes"])
            self.assertEqual(round(count * 10.0, 3), self.report[side]["percent"])

    def test_canonical_json_is_byte_stable(self) -> None:
        first = evaluation.canonical_json(self.report)
        second = evaluation.canonical_json(evaluation.run_evaluation())
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))
        self.assertTrue(first.endswith("\n"))

    def test_output_contains_no_private_path_or_credential_pattern(self) -> None:
        self.assertFalse(evaluation._unsafe(self.report))
        text = evaluation.canonical_json(self.report)
        self.assertNotIn("OPENAI_API_KEY", text)
        self.assertNotIn("source_revision", text)


class SubmissionEvaluationCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = evaluation.run_evaluation()

    def test_cli_exit_zero_and_json_output(self) -> None:
        stdout = io.StringIO()
        with patch.object(evaluation, "run_evaluation", return_value=copy.deepcopy(self.report)):
            with redirect_stdout(stdout):
                result = evaluation.main(["--json"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["final"]["percent"], 100.0)

    def test_cli_exit_one_when_final_oracle_is_missed(self) -> None:
        report = copy.deepcopy(self.report)
        report["final"]["correct_actionable_outcomes"] = 9
        with patch.object(evaluation, "run_evaluation", return_value=report):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(evaluation.main(["--json"]), 1)

    def test_cli_exit_two_for_operational_error(self) -> None:
        stderr = io.StringIO()
        with patch.object(evaluation, "run_evaluation", side_effect=evaluation.EvaluationError("safe category")):
            with redirect_stderr(stderr):
                result = evaluation.main(["--json"])
        self.assertEqual(result, 2)
        self.assertEqual(stderr.getvalue(), "ERROR: safe category\n")

    def test_atomic_output_refuses_collision_without_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            path.write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(evaluation.EvaluationError, "exists"):
                evaluation._atomic_write(path, "replacement\n", replace=False)
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
