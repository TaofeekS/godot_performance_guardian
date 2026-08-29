from __future__ import annotations

from contextlib import redirect_stderr
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

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
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="validated", stderr=""
            )
        )

        evidence = investigator.run_validator(
            self.relative_path, subprocess_runner=runner
        )

        self.assertEqual(evidence["validation_status"], "passed")
        self.assertTrue(evidence["validator_invoked"])
        self.assertEqual(evidence["json_file_count"], 1)
        command = runner.call_args.args[0]
        options = runner.call_args.kwargs
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(Path(command[1]), investigator.VALIDATOR_PATH)
        self.assertEqual(command[2], self.relative_path)
        self.assertEqual(options["cwd"], investigator.REPOSITORY_ROOT)
        self.assertTrue(options["capture_output"])
        self.assertTrue(options["text"])
        self.assertFalse(options["check"])
        self.assertEqual(options["timeout"], investigator.DEFAULT_TIMEOUT_SECONDS)
        self.assertNotIn("shell", options)

    def test_captures_nonzero_validator_output(self) -> None:
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout="summary", stderr="validation failed"
            )
        )

        evidence = investigator.run_validator(
            self.relative_path, subprocess_runner=runner
        )

        self.assertEqual(evidence["validation_status"], "failed")
        self.assertEqual(evidence["exit_code"], 1)
        self.assertEqual(evidence["stdout"], "summary")
        self.assertEqual(evidence["stderr"], "validation failed")

    def test_handles_timeout(self) -> None:
        runner = Mock(
            side_effect=subprocess.TimeoutExpired(
                cmd=["python"], timeout=30, output=b"partial", stderr=b"late"
            )
        )

        evidence = investigator.run_validator(
            self.relative_path, subprocess_runner=runner
        )

        self.assertEqual(evidence["validation_status"], "error")
        self.assertTrue(evidence["validator_invoked"])
        self.assertTrue(evidence["timed_out"])
        self.assertEqual(evidence["error_type"], "timeout")
        self.assertEqual(evidence["stdout"], "partial")

    def test_handles_operating_system_error(self) -> None:
        runner = Mock(side_effect=OSError("private implementation detail"))

        evidence = investigator.run_validator(
            self.relative_path, subprocess_runner=runner
        )

        self.assertEqual(evidence["validation_status"], "error")
        self.assertEqual(evidence["error_type"], "os_error")
        self.assertNotIn("private implementation detail", evidence["stderr"])

    def test_invalid_path_returns_consistent_structured_evidence(self) -> None:
        evidence = investigator.run_validator("../outside")

        self.assertEqual(
            set(evidence),
            {
                "validation_status",
                "validator_invoked",
                "results_directory",
                "json_file_count",
                "exit_code",
                "stdout",
                "stderr",
                "timed_out",
                "error_type",
            },
        )
        self.assertFalse(evidence["validator_invoked"])
        self.assertIsNone(evidence["results_directory"])

    def test_runs_existing_validator_against_stored_results(self) -> None:
        evidence = investigator.run_validator("demo_project/results")

        self.assertEqual(evidence["validation_status"], "passed", evidence)
        self.assertEqual(evidence["exit_code"], 0)
        self.assertIn("Validated", evidence["stdout"])


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
