from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import tools.check_budgets as checker


FIXED_PACKET = {
    "packet_type": "godot_performance_evidence",
    "schema_version": 1,
    "validation": {
        "status": "passed",
        "candidate_file_count": 6,
        "validated_file_count": 6,
        "errors": [],
        "timed_out": False,
        "error_type": None,
        "exit_code": 0,
    },
    "results_directory": "fixtures/results",
    "evidence": [
        {"id": "H-WORK", "metric": "median_p95_workload_time", "scenario": "healthy", "source_type": "validated_aggregate", "unit": "usec", "value": 100.0},
        {"id": "C-WORK", "metric": "median_p95_workload_time", "scenario": "cpu_spike", "source_type": "validated_aggregate", "unit": "usec", "value": 5000.0},
        {"id": "H-PROC", "metric": "median_p95_process_time", "scenario": "healthy", "source_type": "validated_aggregate", "unit": "ms", "value": 1.0},
        {"id": "C-PROC", "metric": "median_p95_process_time", "scenario": "cpu_spike", "source_type": "validated_aggregate", "unit": "ms", "value": 10.0},
        {"id": "H-DURATION", "metric": "median_scenario_duration", "scenario": "healthy", "source_type": "validated_aggregate", "unit": "ms", "value": 5000.0},
        {"id": "C-DURATION", "metric": "median_scenario_duration", "scenario": "cpu_spike", "source_type": "validated_aggregate", "unit": "ms", "value": 7000.0},
        {"id": "H-RETAIN", "metric": "post_cleanup_retained_nodes", "scenario": "healthy", "source_type": "validated_result", "unit": "nodes", "value": 0},
        {"id": "L-RETAIN", "metric": "post_cleanup_retained_nodes", "scenario": "node_leak", "source_type": "validated_result", "unit": "nodes", "value": 120},
        {"id": "C-RETAIN", "metric": "post_cleanup_retained_nodes", "scenario": "cpu_spike", "source_type": "validated_result", "unit": "nodes", "value": 0},
    ],
    "limitations": [
        {
            "id": "L1",
            "statement": "Validator success proves only that configured checks passed.",
        },
        {
            "id": "L2",
            "statement": "The stored result set mixes historical CPU-workload configurations.",
        },
    ],
}


def rule(
    budget_id: str,
    scenario: str,
    metric: str,
    maximum: int | float,
    unit: str,
    description: str = "Test budget.",
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": budget_id,
        "scenario": scenario,
        "metric": metric,
        "maximum": maximum,
        "unit": unit,
    }
    result["description"] = description
    return result


def configuration(*rules: dict[str, object]) -> dict[str, object]:
    return {"schema_version": 1, "budgets": list(rules)}


class ConfigurationTests(unittest.TestCase):
    def test_parses_valid_configuration_in_budget_id_order(self) -> None:
        parsed = checker.parse_budget_configuration(
            configuration(
                rule("z-budget", "healthy", "post_cleanup_retained_nodes", 0, "nodes"),
                rule("a-budget", "healthy", "median_p95_process_time", 2.0, "ms", "Short description."),
            )
        )

        self.assertEqual([item.budget_id for item in parsed], ["a-budget", "z-budget"])
        self.assertEqual(parsed[0].description, "Short description.")

    def test_rejects_invalid_top_level_configuration(self) -> None:
        cases = {
            "not an object": [],
            "unsupported schema": {"schema_version": 3, "budgets": [{}]},
            "boolean schema": {"schema_version": True, "budgets": [{}]},
            "missing field": {"schema_version": 1},
            "unknown field": {"schema_version": 1, "budgets": [{}], "extra": 1},
            "empty budgets": {"schema_version": 1, "budgets": []},
            "non-array budgets": {"schema_version": 1, "budgets": {}},
        }
        for name, data in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(checker.BudgetConfigurationError):
                    checker.parse_budget_configuration(data)

    def test_rejects_invalid_rule_fields(self) -> None:
        base = rule("valid-id", "healthy", "median_p95_process_time", 2.0, "ms")
        cases: dict[str, object] = {}
        missing = copy.deepcopy(base)
        missing.pop("metric")
        cases["missing required"] = missing
        missing_description = copy.deepcopy(base)
        missing_description.pop("description")
        cases["missing description"] = missing_description
        unknown = copy.deepcopy(base)
        unknown["extra"] = True
        cases["unknown field"] = unknown
        invalid_id = copy.deepcopy(base)
        invalid_id["id"] = "bad id"
        cases["invalid id"] = invalid_id
        scenario = copy.deepcopy(base)
        scenario["scenario"] = "unknown"
        cases["unsupported scenario"] = scenario
        metric = copy.deepcopy(base)
        metric["metric"] = "unknown_metric"
        cases["unsupported metric"] = metric
        mismatch = copy.deepcopy(base)
        mismatch["scenario"] = "node_leak"
        cases["scenario mismatch"] = mismatch
        unit = copy.deepcopy(base)
        unit["unit"] = "usec"
        cases["unit mismatch"] = unit
        boolean = copy.deepcopy(base)
        boolean["maximum"] = True
        cases["boolean maximum"] = boolean
        text = copy.deepcopy(base)
        text["maximum"] = "2"
        cases["nonnumeric maximum"] = text
        negative = copy.deepcopy(base)
        negative["maximum"] = -1
        cases["negative maximum"] = negative
        nan = copy.deepcopy(base)
        nan["maximum"] = float("nan")
        cases["nan maximum"] = nan
        infinity = copy.deepcopy(base)
        infinity["maximum"] = float("inf")
        cases["infinite maximum"] = infinity
        empty_description = copy.deepcopy(base)
        empty_description["description"] = " "
        cases["empty description"] = empty_description
        multiline = copy.deepcopy(base)
        multiline["description"] = "line one\nline two"
        cases["multiline description"] = multiline
        long_description = copy.deepcopy(base)
        long_description["description"] = "x" * 201
        cases["long description"] = long_description

        for name, invalid_rule in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(checker.BudgetConfigurationError):
                    checker.parse_budget_configuration(configuration(invalid_rule))

    def test_rejects_duplicate_budget_ids(self) -> None:
        duplicate = rule("duplicate", "healthy", "post_cleanup_retained_nodes", 0, "nodes")
        with self.assertRaisesRegex(checker.BudgetConfigurationError, "duplicate budget id"):
            checker.parse_budget_configuration(configuration(duplicate, duplicate))

    def test_load_rejects_missing_and_invalid_json_without_private_paths(self) -> None:
        with self.assertRaisesRegex(checker.BudgetConfigurationError, "could not be read") as missing:
            checker.load_budget_configuration(Path("missing-private-budget.json"))
        self.assertNotIn(str(checker.REPOSITORY_ROOT), str(missing.exception))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaisesRegex(checker.BudgetConfigurationError, "not valid JSON"):
                checker.load_budget_configuration(path)

    def test_example_budget_matches_the_approved_schema(self) -> None:
        example = json.loads(
            (checker.REPOSITORY_ROOT / "budgets/example_budgets.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            example,
            configuration(
                rule("healthy-process-p95", "healthy", "median_p95_process_time", 2.0, "ms", "Healthy process p95 should remain below two milliseconds."),
                rule("healthy-retained-nodes", "healthy", "post_cleanup_retained_nodes", 0, "nodes", "Healthy cleanup must retain no scenario-owned nodes."),
                rule("cpu-spike-workload-p95", "cpu_spike", "median_p95_workload_time", 1000, "usec", "Demonstrates detection of excessive CPU workload time."),
                rule("node-leak-retained-nodes", "node_leak", "post_cleanup_retained_nodes", 0, "nodes", "Demonstrates detection of retained scenario-owned nodes."),
            ),
        )


class ValidatorBoundaryTests(unittest.TestCase):
    def test_invokes_fixed_structured_validator_without_shell(self) -> None:
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=json.dumps(FIXED_PACKET), stderr=""
            )
        )

        packet = checker.run_validator_packet("fixtures/results", subprocess_runner=runner)

        self.assertEqual(packet, FIXED_PACKET)
        command = runner.call_args.args[0]
        options = runner.call_args.kwargs
        self.assertEqual(command, [sys.executable, str(checker.VALIDATOR_PATH), "--evidence-json", "fixtures/results"])
        self.assertEqual(options["cwd"], checker.REPOSITORY_ROOT)
        self.assertTrue(options["capture_output"])
        self.assertTrue(options["text"])
        self.assertFalse(options["check"])
        self.assertEqual(options["timeout"], checker.VALIDATOR_TIMEOUT_SECONDS)
        self.assertNotIn("shell", options)

    def test_rejects_validator_failure(self) -> None:
        packet = copy.deepcopy(FIXED_PACKET)
        packet["validation"]["status"] = "failed"
        packet["validation"]["exit_code"] = 1
        packet["evidence"] = []
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout=json.dumps(packet), stderr="private"
            )
        )
        with self.assertRaisesRegex(checker.BudgetEvidenceError, "validation failed"):
            checker.run_validator_packet("fixtures/results", subprocess_runner=runner)

    def test_rejects_timeout_os_error_and_malformed_output(self) -> None:
        cases = (
            subprocess.TimeoutExpired(cmd=["python"], timeout=30),
            OSError("private detail"),
        )
        for error in cases:
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(checker.BudgetEvidenceError) as raised:
                    checker.run_validator_packet(
                        "fixtures/results", subprocess_runner=Mock(side_effect=error)
                    )
                self.assertNotIn("private detail", str(raised.exception))
        malformed = Mock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="not-json", stderr="private"
            )
        )
        with self.assertRaisesRegex(checker.BudgetEvidenceError, "valid evidence packet"):
            checker.run_validator_packet("fixtures/results", subprocess_runner=malformed)


class EvaluationTests(unittest.TestCase):
    def parsed(self, *raw_rules: dict[str, object]) -> list[checker.BudgetRule]:
        return checker.parse_budget_configuration(configuration(*raw_rules))

    def test_pass_fail_boundary_order_ids_and_limitations(self) -> None:
        rules = self.parsed(
            rule("z-fail", "node_leak", "post_cleanup_retained_nodes", 0, "nodes"),
            rule("a-boundary", "healthy", "median_p95_process_time", 1.0, "ms"),
            rule("m-pass", "healthy", "post_cleanup_retained_nodes", 0, "nodes"),
        )

        report = checker.evaluate_budgets(rules, copy.deepcopy(FIXED_PACKET))

        self.assertEqual([item["budget_id"] for item in report["results"]], ["a-boundary", "m-pass", "z-fail"])
        self.assertEqual([item["status"] for item in report["results"]], ["passed", "passed", "failed"])
        self.assertEqual([item["evidence_id"] for item in report["results"]], ["H-PROC", "H-RETAIN", "L-RETAIN"])
        self.assertEqual(report["summary"], {"total": 3, "passed": 2, "failed": 1})
        self.assertEqual(report["limitations"], FIXED_PACKET["limitations"])

    def test_missing_duplicate_wrong_unit_and_invalid_values_never_pass(self) -> None:
        rules = self.parsed(
            rule("target", "healthy", "median_p95_process_time", 2.0, "ms")
        )
        variants: dict[str, dict[str, object]] = {}
        missing = copy.deepcopy(FIXED_PACKET)
        missing["evidence"] = [item for item in missing["evidence"] if item["id"] != "H-PROC"]
        variants["missing"] = missing
        duplicate = copy.deepcopy(FIXED_PACKET)
        duplicate_item = next(item for item in duplicate["evidence"] if item["id"] == "H-PROC").copy()
        duplicate_item["id"] = "H-PROC-OTHER"
        duplicate["evidence"].append(duplicate_item)
        variants["duplicate"] = duplicate
        wrong_unit = copy.deepcopy(FIXED_PACKET)
        next(item for item in wrong_unit["evidence"] if item["id"] == "H-PROC")["unit"] = "usec"
        variants["wrong unit"] = wrong_unit
        boolean = copy.deepcopy(FIXED_PACKET)
        next(item for item in boolean["evidence"] if item["id"] == "H-PROC")["value"] = True
        variants["boolean"] = boolean
        negative = copy.deepcopy(FIXED_PACKET)
        next(item for item in negative["evidence"] if item["id"] == "H-PROC")["value"] = -1
        variants["negative"] = negative

        for name, packet in variants.items():
            with self.subTest(name=name):
                with self.assertRaises(checker.BudgetEvidenceError):
                    checker.evaluate_budgets(rules, packet)

    def test_rejects_invalid_packet_metadata(self) -> None:
        rules = self.parsed(
            rule("target", "healthy", "median_p95_process_time", 2.0, "ms")
        )
        cases = []
        failed = copy.deepcopy(FIXED_PACKET)
        failed["validation"]["status"] = "failed"
        cases.append(failed)
        wrong_schema = copy.deepcopy(FIXED_PACKET)
        wrong_schema["schema_version"] = 2
        cases.append(wrong_schema)
        unsafe_path = copy.deepcopy(FIXED_PACKET)
        unsafe_path["results_directory"] = "../private"
        cases.append(unsafe_path)
        duplicate_id = copy.deepcopy(FIXED_PACKET)
        duplicate_id["evidence"][1]["id"] = duplicate_id["evidence"][0]["id"]
        cases.append(duplicate_id)
        no_limitations = copy.deepcopy(FIXED_PACKET)
        no_limitations.pop("limitations")
        cases.append(no_limitations)
        for packet in cases:
            with self.assertRaises(checker.BudgetEvidenceError):
                checker.evaluate_budgets(rules, packet)

    def test_human_and_json_output_are_deterministic(self) -> None:
        rules = self.parsed(
            rule("pass", "healthy", "median_p95_process_time", 2.0, "ms"),
            rule("fail", "cpu_spike", "median_p95_workload_time", 1000, "usec"),
        )
        report = checker.evaluate_budgets(rules, copy.deepcopy(FIXED_PACKET))

        human = checker.human_report(report)
        first_json = checker.canonical_json(report)
        second_json = checker.canonical_json(copy.deepcopy(report))

        self.assertIn("Validation: passed (6 files)", human)
        self.assertIn("PASS: pass", human)
        self.assertIn("FAIL: fail", human)
        self.assertIn("Validator limitations:", human)
        self.assertEqual(first_json, second_json)
        self.assertTrue(first_json.endswith("\n"))
        self.assertEqual(json.loads(first_json), report)

    def test_checker_has_no_api_or_investigator_dependency(self) -> None:
        source = inspect.getsource(checker).lower()
        self.assertNotIn("openai", source)
        self.assertNotIn("agent.investigator", source)


class CliTests(unittest.TestCase):
    def run_cli(
        self, config: dict[str, object], packet: dict[str, object] = FIXED_PACKET, *extra: str
    ) -> tuple[int, str, str, Mock]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        validator = Mock(return_value=copy.deepcopy(packet))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "budgets.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with patch.object(checker, "run_validator_packet", validator):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = checker.main([*extra, "fixtures/results", str(path)])
        return exit_code, stdout.getvalue(), stderr.getvalue(), validator

    def test_exit_zero_when_all_budgets_pass(self) -> None:
        exit_code, output, errors, validator = self.run_cli(
            configuration(
                rule("healthy", "healthy", "median_p95_process_time", 2.0, "ms")
            )
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("Budgets: PASSED", output)
        self.assertEqual(errors, "")
        validator.assert_called_once_with("fixtures/results")

    def test_exit_one_when_any_budget_fails(self) -> None:
        exit_code, output, errors, _validator = self.run_cli(
            configuration(
                rule("cpu", "cpu_spike", "median_p95_workload_time", 1000, "usec")
            )
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("Budgets: FAILED", output)
        self.assertEqual(errors, "")

    def test_exit_two_for_configuration_evidence_and_operational_errors(self) -> None:
        invalid_code, _output, invalid_error, validator = self.run_cli(
            {"schema_version": 1, "budgets": []}
        )
        self.assertEqual(invalid_code, 2)
        self.assertIn("ERROR:", invalid_error)
        validator.assert_not_called()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "budgets.json"
            path.write_text(
                json.dumps(
                    configuration(
                        rule("healthy", "healthy", "median_p95_process_time", 2.0, "ms")
                    )
                ),
                encoding="utf-8",
            )
            for error in (
                checker.BudgetEvidenceError("deterministic result validation failed"),
                checker.BudgetEvidenceError("deterministic validation timed out"),
            ):
                stderr = io.StringIO()
                with patch.object(checker, "run_validator_packet", side_effect=error):
                    with redirect_stderr(stderr):
                        exit_code = checker.main(["fixtures/results", str(path)])
                self.assertEqual(exit_code, 2)
                self.assertIn("ERROR:", stderr.getvalue())

    def test_json_mode_is_canonical(self) -> None:
        config = configuration(
            rule("healthy", "healthy", "median_p95_process_time", 2.0, "ms")
        )
        first = self.run_cli(config, FIXED_PACKET, "--json")
        second = self.run_cli(config, FIXED_PACKET, "--json")

        self.assertEqual(first[0], 0)
        self.assertEqual(first[1], second[1])
        self.assertEqual(first[1], checker.canonical_json(json.loads(first[1])))
        self.assertEqual(first[2], "")


if __name__ == "__main__":
    unittest.main()
