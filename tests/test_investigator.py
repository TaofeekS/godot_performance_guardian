from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import importlib
import io
import json
import os
from pathlib import Path
import statistics
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
        self.assertEqual(
            set(investigator._semantic_evidence(evidence)),
            set(investigator.REQUIRED_EVIDENCE),
        )


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

    def test_packet_has_unique_opaque_evidence_ids(self) -> None:
        identifiers = [item["id"] for item in self.packet["evidence"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for item in self.packet["evidence"]:
            self.assertFalse(Path(item["source"]).is_absolute())

    def test_packet_recalculates_current_aggregate_values(self) -> None:
        resolved = investigator._semantic_evidence(self.packet)
        result_files = sorted((investigator.REPOSITORY_ROOT / "demo_project/results").glob("*.json"))
        results = [json.loads(path.read_text(encoding="utf-8")) for path in result_files]
        grouped = {
            scenario: [result for result in results if result["scenario"] == scenario]
            for scenario in ("healthy", "node_leak", "cpu_spike")
        }
        healthy_workload = statistics.median(
            result["summary"]["timing"]["workload_time_usec"]["p95"]
            for result in grouped["healthy"]
        )
        cpu_workload = statistics.median(
            result["summary"]["timing"]["workload_time_usec"]["p95"]
            for result in grouped["cpu_spike"]
        )
        healthy_duration = statistics.median(
            result["summary"]["scenario_duration_ms"] for result in grouped["healthy"]
        )
        cpu_duration = statistics.median(
            result["summary"]["scenario_duration_ms"] for result in grouped["cpu_spike"]
        )
        self.assertEqual(resolved["validated_count"]["value"], len(results))
        self.assertEqual(resolved["healthy_workload"]["value"], healthy_workload)
        self.assertEqual(resolved["cpu_workload"]["value"], cpu_workload)
        self.assertAlmostEqual(resolved["workload_ratio"]["value"], cpu_workload / healthy_workload)
        self.assertAlmostEqual(
            resolved["duration_increase"]["value"],
            (cpu_duration / healthy_duration - 1.0) * 100.0,
        )

    def test_packet_covers_retention_configuration_and_source_behavior(self) -> None:
        resolved = investigator._semantic_evidence(self.packet)
        self.assertEqual(resolved["leak_retained"]["value"], 120)
        self.assertEqual(resolved["healthy_retained"]["value"], 0)
        self.assertEqual(resolved["cpu_retained"]["value"], 0)
        self.assertGreaterEqual(len(resolved["cpu_configurations"]["value"]), 1)
        self.assertEqual(
            {
                resolved[name]["source_type"]
                for name in ("healthy_behavior", "leak_behavior", "cpu_behavior")
            },
            {"allowlisted_source"},
        )
        controller = (investigator.REPOSITORY_ROOT / "demo_project/scripts/benchmark_controller.gd").read_text(encoding="utf-8")
        for fragment in ("_run_cpu_spike(frame_index)", "leak_container.add_child(temporary_node)", "actor.simulate_step(frame_index)"):
            self.assertIn(fragment, controller)


class GroundingGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = investigator.run_validator("demo_project/results")

    def grounded_report(self) -> str:
        return investigator.render_deterministic_fallback(self.packet)

    def renumbered_packet(self) -> dict[str, object]:
        packet = copy.deepcopy(self.packet)
        for index, item in enumerate(packet["evidence"], 100):
            item["id"] = f"R{index}"
        return packet

    def test_grounded_report_passes(self) -> None:
        self.assertEqual(investigator.validate_grounded_report(self.grounded_report(), self.packet), [])

    def test_renumbered_evidence_passes_and_fallback_uses_new_ids(self) -> None:
        packet = self.renumbered_packet()
        report = investigator.render_deterministic_fallback(packet)

        self.assertEqual(investigator.validate_grounded_report(report, packet), [])
        self.assertIn("[R100]", report)
        self.assertNotIn("[E1]", report)

    def test_unrelated_evidence_does_not_change_fallback(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["evidence"].append(
            {
                "id": "EXTRA",
                "claim": "Unrelated diagnostic note.",
                "metric": "unrelated_metric",
                "value": "ignored",
                "unit": None,
                "scenario": "all",
                "source_type": "validated_result",
                "source": "validated result aggregate",
            }
        )

        self.assertEqual(
            investigator.render_deterministic_fallback(packet),
            self.grounded_report(),
        )

    def test_missing_or_duplicate_semantic_evidence_fails_safely(self) -> None:
        missing = copy.deepcopy(self.packet)
        missing["evidence"] = [
            item
            for item in missing["evidence"]
            if item["metric"] != "cpu_workload_configurations"
        ]
        duplicate = copy.deepcopy(self.packet)
        duplicate_item = copy.deepcopy(
            investigator._semantic_evidence(duplicate)["cpu_workload"]
        )
        duplicate_item["id"] = "DUPLICATE"
        duplicate["evidence"].append(duplicate_item)

        with self.assertRaises(investigator.EvidenceSchemaError):
            investigator.render_deterministic_fallback(missing)
        with self.assertRaises(investigator.EvidenceSchemaError):
            investigator.render_deterministic_fallback(duplicate)
        self.assertIn(
            "G15_EVIDENCE_SCHEMA",
            investigator.validate_grounded_report(self.grounded_report(), missing),
        )

    def test_fallback_is_deterministic_and_discloses_its_source(self) -> None:
        first = investigator.render_deterministic_fallback(self.packet)
        second = investigator.render_deterministic_fallback(copy.deepcopy(self.packet))

        self.assertEqual(first, second)
        self.assertIn(investigator.REPORT_SOURCE_DISCLOSURE, first)
        for scenario in ("healthy", "node_leak", "cpu_spike"):
            self.assertIn(scenario, first)
        self.assertIn(investigator.REQUIRED_UNCERTAINTY, first)

    def test_before_like_wrong_percentage_and_speculation_are_blocked(self) -> None:
        resolved = investigator._semantic_evidence(self.packet)
        correct_percentage = investigator._formatted_number(
            resolved["duration_increase"]["value"], 1
        )
        report = self.grounded_report().replace(f"{correct_percentage} percent", "25 percent").replace(
            "The observed cpu_spike timing",
            "Thermal throttling may explain the observed cpu_spike timing",
        )
        errors = investigator.validate_grounded_report(report, self.packet)
        self.assertIn("G07_UNSUPPORTED_NUMBER", errors)
        self.assertIn("G09_UNSUPPORTED_CAUSE", errors)

    def test_missing_scenario_citations_and_uncertainty_are_blocked(self) -> None:
        leak_id = investigator._semantic_evidence(self.packet)["leak_retained"]["id"]
        report = self.grounded_report().replace("node_leak", "leak case").replace(f"[{leak_id}]", "[missing-evidence]").replace(
            investigator.REQUIRED_UNCERTAINTY, "A cause is proven."
        )
        errors = investigator.validate_grounded_report(report, self.packet)
        self.assertIn("G02_UNKNOWN_EVIDENCE", errors)
        self.assertIn("G03_REQUIRED_EVIDENCE_MISSING", errors)
        self.assertIn("G04_SCENARIO_COVERAGE", errors)
        self.assertIn("G08_REQUIRED_UNCERTAINTY", errors)

    def test_uncited_verified_fact_is_blocked(self) -> None:
        report = self.grounded_report().replace(
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
        report = self.grounded_report().replace("The validator passed", "The validator passed")
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

    def test_cli_uses_fallback_without_retrying_or_printing_rejected_text(self) -> None:
        invalid = "REJECTED MODEL TEXT WITH 25 PERCENT"
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
        self.assertEqual(exit_code, 0)
        self.assertEqual(runner.call_count, 1)
        self.assertIn(investigator.REPORT_SOURCE_DISCLOSURE, stdout.getvalue())
        self.assertIn("WARNING: model output failed grounding", stderr.getvalue())
        self.assertNotIn(invalid, stderr.getvalue())
        self.assertNotIn(invalid, stdout.getvalue())

    def test_cli_failure_fallback_remains_nonzero(self) -> None:
        packet = investigator._evidence_packet(
            validation_status="failed",
            validator_invoked=True,
            results_directory="demo_project/results",
            json_file_count=1,
            exit_code=1,
            stderr="validation failed",
        )
        rejected = "REJECTED FAILURE REPORT"
        result = SimpleNamespace(
            final_output=rejected,
            new_items=[SimpleNamespace(output=json.dumps(packet))],
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
        self.assertIn(investigator.REPORT_SOURCE_DISCLOSURE, stdout.getvalue())
        self.assertNotIn(rejected, stdout.getvalue() + stderr.getvalue())

    def test_cli_grounded_validation_failure_remains_nonzero(self) -> None:
        packet = investigator._evidence_packet(
            validation_status="failed",
            validator_invoked=True,
            results_directory="demo_project/results",
            json_file_count=1,
            exit_code=1,
            stderr="validation failed",
        )
        grounded_failure = investigator.render_deterministic_fallback(packet).replace(
            investigator.REPORT_SOURCE_DISCLOSURE + "\n", ""
        )
        result = SimpleNamespace(
            final_output=grounded_failure,
            new_items=[SimpleNamespace(output=json.dumps(packet))],
        )
        stdout = io.StringIO()
        runner = Mock(return_value=result)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-credential"}):
            with patch.object(investigator.Runner, "run_sync", runner):
                with redirect_stdout(stdout):
                    exit_code = investigator.main(["demo_project/results"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("Deterministic validation failed", stdout.getvalue())

    def test_cli_missing_tool_packet_still_fails_safely(self) -> None:
        result = SimpleNamespace(final_output="untrusted", new_items=[])
        stderr = io.StringIO()
        runner = Mock(return_value=result)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-credential"}):
            with patch.object(investigator.Runner, "run_sync", runner):
                with redirect_stderr(stderr):
                    exit_code = investigator.main(["demo_project/results"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("G00_EVIDENCE_PACKET", stderr.getvalue())


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
            "opaque evidence ID",
            "healthy, node_leak, and cpu_spike",
            investigator.REQUIRED_UNCERTAINTY,
            "thermal throttling",
            "read-only, testable",
            "Use this content skeleton",
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
