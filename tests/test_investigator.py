from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import httpx2
from openai import RateLimitError

import agent.investigator as investigator


class ResultsDirectoryTests(unittest.TestCase):
    def test_resolves_repository_relative_results_directory(self) -> None:
        resolved, relative, count = investigator.resolve_results_directory(
            "demo_project/results"
        )

        self.assertEqual(resolved, investigator.REPOSITORY_ROOT / "demo_project/results")
        self.assertEqual(relative, "demo_project/results")
        self.assertGreaterEqual(count, 9)

    def test_rejects_absolute_path(self) -> None:
        with self.assertRaises(ValueError):
            investigator.resolve_results_directory(str(investigator.REPOSITORY_ROOT))

    def test_rejects_path_outside_repository(self) -> None:
        with self.assertRaises(ValueError):
            investigator.resolve_results_directory("../outside")

    def test_rejects_nonexistent_directory(self) -> None:
        with self.assertRaises(FileNotFoundError):
            investigator.resolve_results_directory("missing-results-directory")

    def test_rejects_file_instead_of_directory(self) -> None:
        with self.assertRaises(NotADirectoryError):
            investigator.resolve_results_directory("README.md")

    def test_rejects_directory_without_json_results(self) -> None:
        with tempfile.TemporaryDirectory(dir=investigator.REPOSITORY_ROOT) as directory:
            relative = Path(directory).relative_to(investigator.REPOSITORY_ROOT)
            with self.assertRaises(FileNotFoundError):
                investigator.resolve_results_directory(str(relative))


class ValidatorRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            dir=investigator.REPOSITORY_ROOT
        )
        self.results_path = Path(self.temporary_directory.name)
        (self.results_path / "sample.json").write_text("{}", encoding="utf-8")
        self.relative_path = self.results_path.relative_to(
            investigator.REPOSITORY_ROOT
        ).as_posix()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_invokes_validator_with_restricted_subprocess_arguments(self) -> None:
        packet = {
            "packet_type": "godot_performance_evidence",
            "validation": {"status": "passed", "exit_code": 0},
        }
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(packet), stderr=""
            )
        )

        evidence = investigator.run_validator(
            self.relative_path, subprocess_runner=runner
        )

        self.assertEqual(evidence["validation"]["status"], "passed")
        command = runner.call_args.args[0]
        options = runner.call_args.kwargs
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(Path(command[1]), investigator.VALIDATOR_PATH)
        self.assertEqual(command[2], "--evidence-json")
        self.assertEqual(command[3], self.relative_path)
        self.assertEqual(options["cwd"], investigator.REPOSITORY_ROOT)
        self.assertTrue(options["capture_output"])
        self.assertTrue(options["text"])
        self.assertFalse(options["check"])
        self.assertEqual(options["timeout"], investigator.DEFAULT_TIMEOUT_SECONDS)
        self.assertNotIn("shell", options)

    def test_captures_nonzero_validator_output(self) -> None:
        packet = {
            "packet_type": "godot_performance_evidence",
            "validation": {"status": "failed", "exit_code": 1},
            "evidence": [],
        }
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout=json.dumps(packet), stderr="validation failed"
            )
        )

        evidence = investigator.run_validator(
            self.relative_path, subprocess_runner=runner
        )

        self.assertEqual(evidence["validation"]["status"], "failed")
        self.assertEqual(evidence["validation"]["exit_code"], 1)
        self.assertEqual(evidence["evidence"], [])

    def test_handles_timeout(self) -> None:
        runner = Mock(
            side_effect=subprocess.TimeoutExpired(
                cmd=["python"], timeout=30, output=b"partial", stderr=b"late"
            )
        )

        evidence = investigator.run_validator(
            self.relative_path, subprocess_runner=runner
        )

        self.assertEqual(evidence["validation"]["status"], "error")
        self.assertTrue(evidence["validation"]["validator_invoked"])
        self.assertTrue(evidence["validation"]["timed_out"])
        self.assertEqual(evidence["validation"]["error_type"], "timeout")
        self.assertEqual(evidence["evidence"], [])

    def test_handles_operating_system_error(self) -> None:
        runner = Mock(side_effect=OSError("private implementation detail"))

        evidence = investigator.run_validator(
            self.relative_path, subprocess_runner=runner
        )

        self.assertEqual(evidence["validation"]["status"], "error")
        self.assertEqual(evidence["validation"]["error_type"], "os_error")
        self.assertNotIn("private implementation detail", json.dumps(evidence))

    def test_rejects_invalid_validator_packet(self) -> None:
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="not-json", stderr="private stderr"
            )
        )

        evidence = investigator.run_validator(self.relative_path, subprocess_runner=runner)

        self.assertEqual(evidence["validation"]["status"], "error")
        self.assertEqual(evidence["validation"]["error_type"], "invalid_evidence_packet")
        self.assertEqual(evidence["evidence"], [])
        self.assertNotIn("private stderr", json.dumps(evidence))

    def test_invalid_path_returns_consistent_structured_evidence(self) -> None:
        evidence = investigator.run_validator("../outside")

        self.assertEqual(evidence["packet_type"], "godot_performance_evidence")
        self.assertFalse(evidence["validation"]["validator_invoked"])
        self.assertIsNone(evidence["results_directory"])
        self.assertEqual(evidence["evidence"], [])

    def test_runs_existing_validator_against_stored_results(self) -> None:
        evidence = investigator.run_validator("demo_project/results")

        self.assertEqual(evidence["validation"]["status"], "passed", evidence)
        self.assertEqual(evidence["validation"]["exit_code"], 0)
        self.assertEqual(len(evidence["evidence"]), 22)


class EvidencePacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = investigator.run_validator("demo_project/results")
        cls.by_id = {item["id"]: item for item in cls.packet["evidence"]}

    def test_packet_is_deterministic_and_json_round_trippable(self) -> None:
        second = investigator.run_validator("demo_project/results")
        canonical = json.dumps(self.packet, sort_keys=True, separators=(",", ":"))
        self.assertEqual(canonical, json.dumps(second, sort_keys=True, separators=(",", ":")))
        self.assertEqual(json.loads(canonical), self.packet)

    def test_packet_has_stable_unique_evidence_ids(self) -> None:
        self.assertEqual(list(self.by_id), [f"E{index}" for index in range(1, 23)])
        for item in self.packet["evidence"]:
            self.assertFalse(Path(item["source"]).is_absolute())

    def test_packet_recalculates_current_aggregate_values(self) -> None:
        self.assertEqual(self.by_id["E1"]["value"], 21)
        self.assertEqual(self.by_id["E2"]["value"], 148.0)
        self.assertEqual(self.by_id["E3"]["value"], 8549.0)
        self.assertAlmostEqual(self.by_id["E4"]["value"], 57.7635135135)
        self.assertEqual(self.by_id["E6"]["value"], 0.408)
        self.assertEqual(self.by_id["E7"]["value"], 12.5885)
        self.assertEqual(self.by_id["E10"]["value"], 4976.01)
        self.assertEqual(self.by_id["E11"]["value"], 6406.27)
        self.assertAlmostEqual(self.by_id["E13"]["value"], 28.7431094391)

    def test_packet_covers_retention_configuration_and_source_behavior(self) -> None:
        self.assertEqual((self.by_id["E14"]["value"], self.by_id["E14"]["run_count"]), (120, 6))
        self.assertEqual((self.by_id["E15"]["value"], self.by_id["E15"]["run_count"]), (0, 9))
        self.assertEqual((self.by_id["E16"]["value"], self.by_id["E16"]["run_count"]), (0, 6))
        self.assertEqual(self.by_id["E19"]["value"], {"160x160": 3, "240x240": 3})
        self.assertEqual(
            {self.by_id[evidence_id]["source_type"] for evidence_id in ("E20", "E21", "E22")},
            {"allowlisted_source"},
        )
        controller = (investigator.REPOSITORY_ROOT / "demo_project/scripts/benchmark_controller.gd").read_text(encoding="utf-8")
        for fragment in ("_run_cpu_spike(frame_index)", "leak_container.add_child(temporary_node)", "actor.simulate_step(frame_index)"):
            self.assertIn(fragment, controller)


GOOD_REPORT = """## Validation status
The validator passed all 21 files under its configured checks [E1].

## Verified facts
The healthy median p95 workload was 148 usec and the cpu_spike value was 8,549 usec, a 57.76x ratio [E2] [E3] [E4].
The corresponding process medians were 0.408 ms and 12.5885 ms [E6] [E7].
Median duration increased from 4,976.010 ms to 6,406.270 ms, an increase of 28.7 percent [E10] [E11] [E13].
Every node_leak run retained 120 nodes across 6 runs [E14]. Healthy retained zero across 9 runs [E15], and cpu_spike retained zero across 6 runs [E16].
Stored CPU configurations include 160x160 across 3 runs and 240x240 across 3 runs [E19].
The current controller gives healthy the actor workload only [E22], routes cpu_spike through the nested numerical workload [E20], and periodically retains node_leak nodes [E21].

## Possible explanations
The observed cpu_spike timing is consistent with its intentional nested numerical workload [E3] [E20].
The node_leak retention is consistent with the controller's intentional periodic retention branch [E14] [E21].

## Recommended next investigation
- Compare each CPU configuration separately to avoid mixing the stored configurations [E19].
- Inspect repeated healthy and cpu_spike runs under one fixed configuration [E2] [E3].
- Measure node growth over the node_leak samples against its retention behavior [E14] [E21].

## Remaining uncertainty
The available evidence does not establish the root cause.
"""


class GroundingGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = investigator.run_validator("demo_project/results")

    def test_grounded_report_passes(self) -> None:
        self.assertEqual(investigator.validate_grounded_report(GOOD_REPORT, self.packet), [])

    def test_before_like_wrong_percentage_and_speculation_are_blocked(self) -> None:
        report = GOOD_REPORT.replace("28.7 percent", "25 percent").replace(
            "The observed cpu_spike timing",
            "Thermal throttling may explain the observed cpu_spike timing",
        )
        errors = investigator.validate_grounded_report(report, self.packet)
        self.assertIn("G07_UNSUPPORTED_NUMBER", errors)
        self.assertIn("G09_UNSUPPORTED_CAUSE", errors)

    def test_missing_scenario_citations_and_uncertainty_are_blocked(self) -> None:
        report = GOOD_REPORT.replace("node_leak", "leak case").replace("[E14]", "[E404]").replace(
            investigator.REQUIRED_UNCERTAINTY, "A cause is proven."
        )
        errors = investigator.validate_grounded_report(report, self.packet)
        self.assertIn("G02_UNKNOWN_EVIDENCE", errors)
        self.assertIn("G03_REQUIRED_EVIDENCE_MISSING", errors)
        self.assertIn("G04_SCENARIO_COVERAGE", errors)
        self.assertIn("G08_REQUIRED_UNCERTAINTY", errors)

    def test_uncited_verified_fact_is_blocked(self) -> None:
        report = GOOD_REPORT.replace(
            "The corresponding process medians",
            "The result set is suitable for comparison.\nThe corresponding process medians",
        )
        self.assertIn(
            "G14_UNCITED_VERIFIED_FACT",
            investigator.validate_grounded_report(report, self.packet),
        )

    def test_failed_packet_cannot_be_reported_as_passed(self) -> None:
        packet = investigator._evidence_packet(
            validation_status="failed",
            validator_invoked=True,
            results_directory="demo_project/results",
            json_file_count=1,
            exit_code=1,
            stderr="validation failed",
        )
        report = GOOD_REPORT.replace("21 files", "1 file")
        self.assertIn("G05_FALSE_VALIDATION_SUCCESS", investigator.validate_grounded_report(report, packet))

    def test_failed_packet_allows_safe_failure_report_without_evidence_claims(self) -> None:
        packet = investigator._evidence_packet(
            validation_status="failed",
            validator_invoked=True,
            results_directory="demo_project/results",
            json_file_count=1,
            exit_code=1,
            stderr="validation failed",
        )
        report = """## Validation status
Validation failed, so no benchmark fact is treated as verified.

## Verified facts
No benchmark facts are available.

## Possible explanations
The validation failure must be resolved before interpreting performance.

## Recommended next investigation
- Resolve the validator failure and run validation again.

## Remaining uncertainty
The available evidence does not establish the root cause.
"""
        self.assertEqual(investigator.validate_grounded_report(report, packet), [])

    def test_cli_blocks_invalid_report_without_retrying_or_printing_it(self) -> None:
        invalid = GOOD_REPORT.replace("28.7 percent", "25 percent")
        result = SimpleNamespace(
            final_output=invalid,
            new_items=[SimpleNamespace(output=json.dumps(self.packet))],
        )
        stderr = io.StringIO()
        stdout = io.StringIO()
        runner = Mock(return_value=result)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-credential"}):
            with patch.object(investigator.Runner, "run_sync", runner):
                with redirect_stderr(stderr), redirect_stdout(stdout):
                    exit_code = investigator.main(["demo_project/results"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("G07_UNSUPPORTED_NUMBER", stderr.getvalue())
        self.assertNotIn(invalid, stderr.getvalue())


class InvestigatorConfigurationTests(unittest.TestCase):
    def test_agent_has_exact_name_and_single_required_tool(self) -> None:
        built = investigator.build_investigator()

        self.assertEqual(built.name, "Godot Performance Investigator")
        self.assertEqual([tool.name for tool in built.tools], ["validate_benchmark_results"])
        self.assertEqual(built.model_settings.tool_choice, "required")
        self.assertFalse(built.model_settings.parallel_tool_calls)
        self.assertEqual(built.tool_use_behavior, "run_llm_again")
        self.assertTrue(built.reset_tool_choice)

    def test_model_default_override_and_required_report_sections(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_MODEL", None)
            default_agent = investigator.build_investigator()
        with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}):
            configured_agent = investigator.build_investigator()

        self.assertEqual(default_agent.model, "gpt-4.1-mini")
        self.assertEqual(configured_agent.model, "test-model")
        for heading in (
            "## Validation status",
            "## Verified facts",
            "## Possible explanations",
            "## Recommended next investigation",
            "## Remaining uncertainty",
        ):
            self.assertIn(heading, default_agent.instructions)
        for requirement in (
            "[E1]",
            "healthy, node_leak,\nand cpu_spike",
            investigator.REQUIRED_UNCERTAINTY,
            "thermal throttling",
            "read-only, testable",
        ):
            self.assertIn(requirement, default_agent.instructions)

    def test_import_does_not_run_agent(self) -> None:
        with patch.object(investigator.Runner, "run_sync") as run_sync:
            importlib.reload(investigator)

        run_sync.assert_not_called()

    def test_missing_api_key_prevents_agent_run(self) -> None:
        stderr = io.StringIO()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with patch.object(investigator.Runner, "run_sync") as run_sync:
                with redirect_stderr(stderr):
                    exit_code = investigator.main(["demo_project/results"])

        self.assertEqual(exit_code, 2)
        self.assertIn("OPENAI_API_KEY is not configured", stderr.getvalue())
        run_sync.assert_not_called()


class ApiErrorHandlingTests(unittest.TestCase):
    @staticmethod
    def rate_limit_error(
        *,
        code: str | None = None,
        error_type: str | None = None,
        request_id: str | None = None,
        retry_after: str | None = None,
    ) -> RateLimitError:
        request = httpx2.Request(
            "POST",
            "https://api.openai.com/v1/responses",
            headers={"authorization": "Bearer hidden-authorization-value"},
        )
        headers: dict[str, str] = {"authorization": "hidden-response-header"}
        if request_id is not None:
            headers["x-request-id"] = request_id
        if retry_after is not None:
            headers["retry-after"] = retry_after
        response = httpx2.Response(429, request=request, headers=headers)
        return RateLimitError(
            "raw exception contains sensitive-exception-value",
            response=response,
            body={
                "code": code,
                "type": error_type,
                "message": "sensitive-body-value",
                "authorization": "sensitive-body-authorization",
            },
        )

    def run_cli_with_error(self, error: RateLimitError) -> tuple[int, str, Mock]:
        stderr = io.StringIO()
        runner = Mock(side_effect=error)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-credential"}):
            with patch.object(investigator.Runner, "run_sync", runner):
                with redirect_stderr(stderr):
                    exit_code = investigator.main(["demo_project/results"])
        return exit_code, stderr.getvalue(), runner

    def test_insufficient_quota_is_actionable_and_not_retried(self) -> None:
        error = self.rate_limit_error(
            code="insufficient_quota",
            error_type="insufficient_quota",
            request_id="req_test_quota",
        )

        exit_code, output, runner = self.run_cli_with_error(error)

        self.assertEqual(exit_code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("HTTP 429", output)
        self.assertIn("code=insufficient_quota", output)
        self.assertIn("request_id=req_test_quota", output)
        self.assertIn("billing, credits, and project usage limits", output)
        self.assertIn("retrying will not resolve", output)

    def test_transient_rate_limit_reports_numeric_retry_after(self) -> None:
        error = self.rate_limit_error(
            code="rate_limit_exceeded",
            error_type="requests",
            request_id="req_test_transient",
            retry_after="2.5",
        )

        exit_code, output, runner = self.run_cli_with_error(error)

        self.assertEqual(exit_code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("retry_after=2.5s", output)
        self.assertIn("wait at least 2.5 seconds", output)
        self.assertIn("built-in retries", output)

    def test_rate_limit_without_optional_metadata_stays_actionable(self) -> None:
        error = self.rate_limit_error()

        exit_code, output, _runner = self.run_cli_with_error(error)

        self.assertEqual(exit_code, 1)
        self.assertIn("OpenAI API rate limit (HTTP 429)", output)
        self.assertIn("Check the API project's rate limits", output)
        self.assertNotIn("request_id=", output)
        self.assertNotIn("retry_after=", output)

    def test_rate_limit_output_never_contains_raw_sensitive_content(self) -> None:
        error = self.rate_limit_error(
            code="rate_limit_exceeded",
            error_type="tokens",
            request_id="req_test_safe",
            retry_after="1",
        )

        _exit_code, output, _runner = self.run_cli_with_error(error)

        for forbidden in (
            "test-credential",
            "hidden-authorization-value",
            "hidden-response-header",
            "sensitive-exception-value",
            "sensitive-body-value",
            "sensitive-body-authorization",
            "Bearer",
        ):
            self.assertNotIn(forbidden, output)


if __name__ == "__main__":
    unittest.main()
