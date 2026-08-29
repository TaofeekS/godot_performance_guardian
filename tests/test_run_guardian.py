from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import tools.run_guardian as guardian


RESULTS_DIRECTORY = "tests/fixtures/generic_results"
BUDGET_FILE = "examples/minimal_project/budgets/performance_budgets.json"
WORKFLOW_PATH = guardian.REPOSITORY_ROOT / ".github/workflows/performance-guardian.yml"


def budget_report(*, failed: bool = False) -> dict[str, object]:
    result = {
        "budget_id": "fixture-budget",
        "description": "Fixed unit-test budget.",
        "metric": "median_p95_process_time",
        "measured_value": 2.0 if failed else 0.5,
        "maximum_value": 1.0,
        "unit": "ms",
        "evidence_id": "GX",
        "status": "failed" if failed else "passed",
        "explanation": "Fixed deterministic result.",
        "profile": "main_scene",
    }
    return {
        "schema_version": 1,
        "budget_schema_version": 2,
        "status": "failed" if failed else "passed",
        "validator": {
            "status": "passed",
            "candidate_file_count": 1,
            "validated_file_count": 1,
            "results_directory": RESULTS_DIRECTORY,
        },
        "summary": {
            "total": 1,
            "passed": 0 if failed else 1,
            "failed": 1 if failed else 0,
        },
        "results": [result],
        "limitations": [{"id": "GL1", "statement": "A fixed limitation."}],
    }


def deterministic_report(*, exit_code: int = 0, mode: str = "never") -> dict[str, object]:
    failed = exit_code == 1
    report = {
        "schema_version": 1,
        "deterministic_status": "budget_failed" if failed else "passed",
        "validator": {
            "status": "passed",
            "candidate_file_count": 1,
            "validated_file_count": 1,
            "results_directory": RESULTS_DIRECTORY,
        },
        "budget": {
            "status": "failed" if failed else "passed",
            "summary": {"total": 1, "passed": 0 if failed else 1, "failed": 1 if failed else 0},
            "results": [],
            "limitations": [],
        },
        "investigation": guardian._empty_investigation(
            mode,
            "not_requested" if mode == "never" else "not_needed",
        ),
        "authoritative_exit_code": exit_code,
        "authoritative_exit_reason": "fixed reason",
    }
    return report


def investigator_report(disclosure: str) -> str:
    return f"""## Validation status
{disclosure}
Validated evidence.

## Verified facts
Verified facts.

## Possible explanations
No hypothesis.

## Recommended next investigation
- Compare evidence.

## Remaining uncertainty
Uncertainty remains.
"""


class PathContainmentTests(unittest.TestCase):
    def test_accepts_tracked_results_and_budget_paths(self) -> None:
        results, relative_results = guardian.resolve_repository_input(
            RESULTS_DIRECTORY, kind="results directory"
        )
        budget, relative_budget = guardian.resolve_repository_input(
            BUDGET_FILE, kind="budget file"
        )
        self.assertTrue(results.is_dir())
        self.assertTrue(budget.is_file())
        self.assertEqual(relative_results, RESULTS_DIRECTORY)
        self.assertEqual(relative_budget, BUDGET_FILE)

    def test_rejects_absolute_traversal_missing_and_wrong_types(self) -> None:
        cases = (
            (str(guardian.REPOSITORY_ROOT), "results directory"),
            ("../outside", "results directory"),
            ("missing-results", "results directory"),
            ("README.md", "results directory"),
            ("../budget.json", "budget file"),
            ("missing-budget.json", "budget file"),
            (RESULTS_DIRECTORY, "budget file"),
            ("README.md", "budget file"),
        )
        for value, kind in cases:
            with self.subTest(value=value, kind=kind):
                with self.assertRaises(guardian.GuardianConfigurationError):
                    guardian.resolve_repository_input(value, kind=kind)

    def test_rejects_empty_results_directory(self) -> None:
        with tempfile.TemporaryDirectory(dir=guardian.REPOSITORY_ROOT) as directory:
            relative = Path(directory).relative_to(guardian.REPOSITORY_ROOT).as_posix()
            with self.assertRaises(guardian.GuardianConfigurationError):
                guardian.resolve_repository_input(relative, kind="results directory")

    def test_external_workspace_generic_gate_passes_with_relative_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            results = root / "captures"
            results.mkdir()
            shutil.copy2(
                guardian.REPOSITORY_ROOT / RESULTS_DIRECTORY / "main_scene.json",
                results / "main_scene.json",
            )
            shutil.copy2(guardian.REPOSITORY_ROOT / BUDGET_FILE, root / "budgets.json")
            report = guardian.run_deterministic_pipeline(
                "captures",
                "budgets.json",
                mode="never",
                workspace_root=root,
                validator_runner=subprocess.run,
            )
            self.assertEqual(report["authoritative_exit_code"], 0, report)
            self.assertEqual(report["validator"]["results_directory"], "captures")
            self.assertNotIn(str(root), guardian.canonical_json(report))

    def test_rejects_a_resolved_symlink_escape(self) -> None:
        outside = guardian.REPOSITORY_ROOT.parent / "outside-results"
        with patch.object(Path, "resolve", return_value=outside):
            with self.assertRaisesRegex(
                guardian.GuardianConfigurationError, "remain inside"
            ):
                guardian.resolve_repository_input(
                    RESULTS_DIRECTORY, kind="results directory"
                )


class DeterministicPipelineTests(unittest.TestCase):
    def test_configuration_validator_budget_order_and_exit_zero(self) -> None:
        order: list[str] = []

        def load(_path: Path) -> list[object]:
            order.append("configuration")
            return [object()]

        def validate(_directory: str, **_kwargs: object) -> dict[str, object]:
            order.append("validator")
            return {"packet_type": "godot_performance_evidence"}

        def evaluate(_rules: list[object], _packet: dict[str, object]) -> dict[str, object]:
            order.append("budget")
            return budget_report()

        with patch.object(guardian.check_budgets, "load_budget_configuration", load):
            with patch.object(guardian.check_budgets, "run_validator_packet", validate):
                with patch.object(guardian.check_budgets, "evaluate_budgets", evaluate):
                    report = guardian.run_deterministic_pipeline(
                        RESULTS_DIRECTORY, BUDGET_FILE, mode="never"
                    )
        self.assertEqual(order, ["configuration", "validator", "budget"])
        self.assertEqual(report["authoritative_exit_code"], 0)
        self.assertEqual(report["deterministic_status"], "passed")

    def test_budget_failure_preserves_exit_one(self) -> None:
        with patch.object(
            guardian.check_budgets, "load_budget_configuration", return_value=[object()]
        ):
            with patch.object(guardian.check_budgets, "run_validator_packet", return_value={}):
                with patch.object(
                    guardian.check_budgets,
                    "evaluate_budgets",
                    return_value=budget_report(failed=True),
                ):
                    report = guardian.run_deterministic_pipeline(
                        RESULTS_DIRECTORY, BUDGET_FILE, mode="on-failure"
                    )
        self.assertEqual(report["authoritative_exit_code"], 1)
        self.assertEqual(report["deterministic_status"], "budget_failed")

    def test_configuration_failure_is_exit_two_without_validator(self) -> None:
        validator = Mock()
        with patch.object(
            guardian.check_budgets,
            "load_budget_configuration",
            side_effect=guardian.check_budgets.BudgetConfigurationError("invalid policy"),
        ):
            with patch.object(guardian.check_budgets, "run_validator_packet", validator):
                report = guardian.run_deterministic_pipeline(
                    RESULTS_DIRECTORY, BUDGET_FILE, mode="always"
                )
        self.assertEqual(report["authoritative_exit_code"], 2)
        self.assertEqual(report["validator"]["status"], "not_run")
        validator.assert_not_called()

    def test_validator_or_evidence_failure_is_exit_two(self) -> None:
        with patch.object(
            guardian.check_budgets, "load_budget_configuration", return_value=[object()]
        ):
            with patch.object(
                guardian.check_budgets,
                "run_validator_packet",
                side_effect=guardian.check_budgets.BudgetEvidenceError("validation failed"),
            ):
                report = guardian.run_deterministic_pipeline(
                    RESULTS_DIRECTORY, BUDGET_FILE, mode="always"
                )
        self.assertEqual(report["authoritative_exit_code"], 2)
        self.assertEqual(report["validator"]["status"], "failed")
        self.assertEqual(report["investigation"]["outcome"], "not_needed")

    def test_real_tracked_fixture_passes_without_ai(self) -> None:
        report = guardian.run_deterministic_pipeline(
            RESULTS_DIRECTORY, BUDGET_FILE, mode="never"
        )
        self.assertEqual(report["authoritative_exit_code"], 0)
        self.assertEqual(report["budget"]["summary"], {"total": 2, "passed": 2, "failed": 0})
        self.assertEqual(report["investigation"]["outcome"], "not_requested")


class InvestigationPolicyTests(unittest.TestCase):
    class ExplodingEnvironment(dict[str, str]):
        def get(self, key: str, default: str | None = None) -> str | None:
            raise AssertionError(f"environment accessed unexpectedly: {key}")

    def test_never_mode_does_not_check_key_or_launch_investigator(self) -> None:
        report = deterministic_report(mode="never")
        process = Mock()
        guardian.run_optional_investigation(
            report,
            environment=self.ExplodingEnvironment(),
            subprocess_runner=process,
        )
        self.assertEqual(report["investigation"]["outcome"], "not_requested")
        process.assert_not_called()

    def test_on_failure_does_not_run_when_budgets_pass(self) -> None:
        report = deterministic_report(mode="on-failure")
        process = Mock()
        guardian.run_optional_investigation(
            report,
            environment=self.ExplodingEnvironment(),
            subprocess_runner=process,
        )
        self.assertEqual(report["investigation"]["outcome"], "not_needed")
        process.assert_not_called()

    def test_on_failure_runs_once_for_budget_failure_and_accepts_report(self) -> None:
        report = deterministic_report(exit_code=1, mode="on-failure")
        process = Mock(
            return_value=subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=investigator_report(guardian.MODEL_REPORT_SOURCE_DISCLOSURE),
                stderr="WARNING: discarded model items (C03_HYPOTHESIS_TEXT).",
            )
        )
        guardian.run_optional_investigation(
            report,
            environment={"OPENAI_API_KEY": "fixture-only-value"},
            subprocess_runner=process,
        )
        self.assertEqual(report["authoritative_exit_code"], 1)
        self.assertEqual(report["investigation"]["outcome"], "accepted")
        self.assertEqual(report["investigation"]["rule_ids"], ["C03_HYPOTHESIS_TEXT"])
        self.assertEqual(process.call_count, 1)
        command = process.call_args.args[0]
        options = process.call_args.kwargs
        self.assertEqual(command[0], guardian.sys.executable)
        self.assertEqual(Path(command[1]), guardian.INVESTIGATOR_PATH)
        self.assertEqual(command[2], RESULTS_DIRECTORY)
        self.assertEqual(options["cwd"], guardian.REPOSITORY_ROOT)
        self.assertTrue(options["capture_output"])
        self.assertTrue(options["text"])
        self.assertFalse(options["check"])
        self.assertEqual(options["timeout"], guardian.INVESTIGATOR_TIMEOUT_SECONDS)
        self.assertNotIn("shell", options)

    def test_always_runs_once_and_recognizes_fallback(self) -> None:
        report = deterministic_report(mode="always")
        process = Mock(
            return_value=subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=investigator_report(guardian.FALLBACK_REPORT_SOURCE_DISCLOSURE),
                stderr="WARNING: model contribution failed (G03_REQUIRED_EVIDENCE_MISSING).",
            )
        )
        guardian.run_optional_investigation(
            report,
            environment={"OPENAI_API_KEY": "fixture-only-value"},
            subprocess_runner=process,
        )
        self.assertEqual(report["authoritative_exit_code"], 0)
        self.assertEqual(report["investigation"]["outcome"], "fallback")
        self.assertEqual(process.call_count, 1)

    def test_deterministic_failure_never_runs_investigator(self) -> None:
        report = guardian._error_report("always", "invalid evidence", configuration_error=False)
        process = Mock()
        guardian.run_optional_investigation(
            report,
            environment={"OPENAI_API_KEY": "fixture-only-value"},
            subprocess_runner=process,
        )
        self.assertEqual(report["authoritative_exit_code"], 2)
        process.assert_not_called()

    def test_missing_key_skips_and_preserves_zero_or_one(self) -> None:
        for exit_code, mode in ((0, "always"), (1, "on-failure")):
            with self.subTest(exit_code=exit_code):
                report = deterministic_report(exit_code=exit_code, mode=mode)
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    guardian.run_optional_investigation(
                        report, environment={}, subprocess_runner=Mock()
                    )
                self.assertEqual(report["authoritative_exit_code"], exit_code)
                self.assertEqual(report["investigation"]["outcome"], "skipped_no_key")
                self.assertFalse(report["investigation"]["api_request_attempted"])
                self.assertIn("skipped", stderr.getvalue())

    def test_api_error_is_safe_and_preserves_deterministic_exit(self) -> None:
        secret = "REJECTED PRIVATE RESPONSE"
        report = deterministic_report(exit_code=1, mode="always")
        process = Mock(
            return_value=subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout=secret,
                stderr="ERROR: investigator run failed (AuthenticationError). " + secret,
            )
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            guardian.run_optional_investigation(
                report,
                environment={"OPENAI_API_KEY": "fixture-only-value"},
                subprocess_runner=process,
            )
        self.assertEqual(report["authoritative_exit_code"], 1)
        self.assertEqual(report["investigation"]["outcome"], "api_error")
        self.assertEqual(report["investigation"]["error_category"], "authentication_error")
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue() + guardian.canonical_json(report))
        self.assertEqual(process.call_count, 1)

    def test_timeout_and_os_errors_are_safe(self) -> None:
        errors = (
            (subprocess.TimeoutExpired(cmd=["fixed"], timeout=120), "timeout", True),
            (OSError("private path"), "os_error", False),
        )
        for error, category, attempted in errors:
            with self.subTest(category=category):
                report = deterministic_report(mode="always")
                with redirect_stderr(io.StringIO()):
                    guardian.run_optional_investigation(
                        report,
                        environment={"OPENAI_API_KEY": "fixture-only-value"},
                        subprocess_runner=Mock(side_effect=error),
                    )
                self.assertEqual(report["authoritative_exit_code"], 0)
                self.assertEqual(report["investigation"]["error_category"], category)
                self.assertEqual(report["investigation"]["api_request_attempted"], attempted)

    def test_unrecognized_or_sensitive_success_output_is_rejected(self) -> None:
        rejected = "REJECTED MODEL OUTPUT"
        for stdout in (
            rejected,
            investigator_report(guardian.MODEL_REPORT_SOURCE_DISCLOSURE)
            + "C:\\Users\\private\\file",
        ):
            report = deterministic_report(mode="always")
            with redirect_stderr(io.StringIO()):
                guardian.run_optional_investigation(
                    report,
                    environment={"OPENAI_API_KEY": "fixture-only-value"},
                    subprocess_runner=Mock(
                        return_value=subprocess.CompletedProcess(
                            args=[], returncode=0, stdout=stdout, stderr=""
                        )
                    ),
                )
            self.assertEqual(report["investigation"]["outcome"], "api_error")
            self.assertEqual(
                report["investigation"]["error_category"], "invalid_investigator_output"
            )
            self.assertNotIn(rejected, guardian.canonical_json(report))


class OutputAndCliTests(unittest.TestCase):
    def test_canonical_json_is_byte_identical_and_has_one_newline(self) -> None:
        report = deterministic_report(mode="never")
        first = guardian.canonical_json(copy.deepcopy(report))
        second = guardian.canonical_json(copy.deepcopy(report))
        self.assertEqual(first.encode(), second.encode())
        self.assertTrue(first.endswith("\n"))
        self.assertFalse(first.endswith("\n\n"))
        self.assertEqual(json.loads(first)["authoritative_exit_code"], 0)

    def test_human_output_has_four_explicit_sections(self) -> None:
        output = guardian.human_report(deterministic_report(mode="never"))
        for heading in (
            "Validation result",
            "Budget result",
            "Optional investigator explanation",
            "Final authoritative exit reason",
        ):
            self.assertEqual(output.count(heading), 1)

    def test_main_returns_authoritative_code_and_json_only(self) -> None:
        report = deterministic_report(exit_code=1, mode="never")
        stdout = io.StringIO()
        with patch.object(guardian, "run_deterministic_pipeline", return_value=report):
            with patch.object(guardian, "run_optional_investigation") as optional:
                with redirect_stdout(stdout):
                    exit_code = guardian.main(
                        ["--json", "--investigate", "never", RESULTS_DIRECTORY, BUDGET_FILE]
                    )
        self.assertEqual(exit_code, 1)
        optional.assert_called_once_with(report)
        self.assertEqual(json.loads(stdout.getvalue())["authoritative_exit_code"], 1)

    def test_import_does_not_execute_runner_or_api(self) -> None:
        with patch.object(subprocess, "run") as run:
            importlib.reload(guardian)
        run.assert_not_called()


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_workflow_triggers_and_supported_actions(self) -> None:
        self.assertIn("pull_request:", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("- main", self.workflow)
        self.assertIn("runs-on: windows-latest", self.workflow)
        self.assertIn("actions/checkout@v7", self.workflow)
        self.assertIn("actions/setup-python@v7", self.workflow)
        self.assertIn("actions/upload-artifact@v7", self.workflow)
        self.assertIn('python-version: "3.14"', self.workflow)
        self.assertIn("contents: read", self.workflow)

    def test_workflow_uses_only_tracked_stable_inputs(self) -> None:
        self.assertIn(RESULTS_DIRECTORY.replace("/", "\\"), self.workflow)
        self.assertIn(BUDGET_FILE.replace("/", "\\"), self.workflow)
        ignored_results = "\\".join(("demo_project", "results"))
        self.assertNotIn(ignored_results, self.workflow)
        self.assertIn("python -m unittest discover -s tests -v", self.workflow)
        self.assertIn("python -m pip install -r requirements-agent.txt", self.workflow)
        self.assertIn("python -m pip check", self.workflow)

    def test_workflow_ai_is_manual_optional_and_secret_safe(self) -> None:
        self.assertIn("--investigate never", self.workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", self.workflow)
        self.assertIn("${{ secrets.OPENAI_API_KEY }}", self.workflow)
        self.assertIn("${{ vars.OPENAI_MODEL || 'gpt-4.1-mini' }}", self.workflow)
        self.assertNotRegex(self.workflow, r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")
        self.assertIn("if: always()", self.workflow)
        self.assertIn("%GUARDIAN_EXIT%", self.workflow)

    def test_runner_source_has_no_openai_import_or_shell_execution(self) -> None:
        source = (guardian.REPOSITORY_ROOT / "tools/run_guardian.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("import openai", source)
        self.assertNotIn("from openai", source)
        self.assertNotIn("import agents", source)
        self.assertNotIn("from agents", source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
