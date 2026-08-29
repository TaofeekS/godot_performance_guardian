from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

from tools import check_budgets, comparison_evidence, run_guardian


ROOT = Path(__file__).resolve().parents[1]
RESULTS = "tests/fixtures/generic_results"
POLICY = "examples/minimal_project/budgets/comparison_budgets.json"
TRACKED_BASELINE = "tests/fixtures/comparison/baseline"
TRACKED_CANDIDATE = "tests/fixtures/comparison/candidate"
TRACKED_REGRESSION = "tests/fixtures/comparison/regression"
TRACKED_POLICY = "tests/fixtures/comparison/performance_budgets.json"


def packet() -> dict[str, object]:
    return check_budgets.run_validator_packet(RESULTS)


class SchemaV3Tests(unittest.TestCase):
    def test_exact_v3_schema_and_relative_fields(self) -> None:
        rules = check_budgets.load_budget_configuration(ROOT / POLICY)
        self.assertTrue(all(rule.schema_version == 3 for rule in rules))
        self.assertEqual(
            {rule.budget_id: rule.maximum_increase_percent for rule in rules},
            {"main-scene-peak-nodes": 0, "main-scene-process-p95": 20},
        )
        malformed = json.loads((ROOT / POLICY).read_text(encoding="utf-8"))
        malformed["budgets"][0]["unexpected"] = True
        with self.assertRaises(check_budgets.BudgetConfigurationError):
            check_budgets.parse_budget_configuration(malformed)

    def test_unchanged_candidate_passes_absolute_and_relative(self) -> None:
        rules = check_budgets.load_budget_configuration(ROOT / POLICY)
        report = check_budgets.comparison_budget_report(rules, packet(), packet())
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["comparison"]["summary"], {"total": 2, "passed": 2, "failed": 0})
        self.assertTrue(all(item["increase_percent"] == 0 for item in report["comparison"]["results"]))

    def test_absolute_pass_relative_failure_and_improvement(self) -> None:
        rules = check_budgets.load_budget_configuration(ROOT / POLICY)
        baseline = packet()
        candidate = copy.deepcopy(baseline)
        process = next(item for item in candidate["evidence"] if item.get("metric") == "median_p95_process_time")
        process["value"] = 0.61
        report = check_budgets.evaluate_comparison_budgets(rules, baseline, candidate)
        process_result = next(item for item in report["results"] if item["metric"] == "median_p95_process_time")
        self.assertEqual(process_result["absolute"]["status"], "passed")
        self.assertEqual(process_result["relative"]["status"], "failed")
        self.assertAlmostEqual(process_result["increase_percent"], 22.0)
        process["value"] = 0.4
        improved = check_budgets.evaluate_comparison_budgets(rules, baseline, candidate)
        self.assertLess(next(item for item in improved["results"] if item["metric"] == "median_p95_process_time")["increase_percent"], 0)

    def test_zero_baseline_rules(self) -> None:
        rules = check_budgets.load_budget_configuration(ROOT / POLICY)
        baseline = packet()
        candidate = copy.deepcopy(baseline)
        for source in (baseline, candidate):
            next(item for item in source["evidence"] if item.get("metric") == "median_p95_process_time")["value"] = 0
        result = check_budgets.evaluate_comparison_budgets(rules, baseline, candidate)
        self.assertEqual(next(item for item in result["results"] if item["metric"] == "median_p95_process_time")["increase_percent"], 0)
        next(item for item in candidate["evidence"] if item.get("metric") == "median_p95_process_time")["value"] = 0.1
        result = check_budgets.evaluate_comparison_budgets(rules, baseline, candidate)
        process = next(item for item in result["results"] if item["metric"] == "median_p95_process_time")
        self.assertIsNone(process["increase_percent"])
        self.assertEqual(process["relative"]["status"], "failed")

    def test_missing_or_duplicate_semantic_evidence_fails(self) -> None:
        rules = check_budgets.load_budget_configuration(ROOT / POLICY)
        for mutate in ("missing", "duplicate"):
            candidate = packet()
            match = next(item for item in candidate["evidence"] if item.get("metric") == "median_p95_process_time")
            if mutate == "missing":
                candidate["evidence"].remove(match)
            else:
                candidate["evidence"].append(copy.deepcopy(match))
            with self.subTest(mutate=mutate), self.assertRaises(check_budgets.BudgetEvidenceError):
                check_budgets.evaluate_comparison_budgets(rules, packet(), candidate)

    def test_v1_v2_reject_baseline_and_v3_no_baseline_records_not_requested(self) -> None:
        legacy = check_budgets.load_budget_configuration(ROOT / "examples/minimal_project/budgets/performance_budgets.json")
        with self.assertRaises(check_budgets.BudgetConfigurationError):
            check_budgets.evaluate_comparison_budgets(legacy, packet(), packet())
        v3 = check_budgets.comparison_budget_report(
            check_budgets.load_budget_configuration(ROOT / POLICY), packet(), None
        )
        self.assertEqual(v3["comparison"]["status"], "not_requested")


class ComparisonPacketAndRunnerTests(unittest.TestCase):
    def test_unified_runner_validates_baseline_then_candidate_exactly_once(self) -> None:
        validator = Mock(side_effect=[packet(), packet()])
        with patch.object(check_budgets, "run_validator_packet", validator):
            report = run_guardian.run_deterministic_pipeline(
                TRACKED_CANDIDATE,
                TRACKED_POLICY,
                mode="never",
                baseline_results=TRACKED_BASELINE,
            )
        self.assertEqual(report["authoritative_exit_code"], 0)
        self.assertEqual(validator.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in validator.call_args_list],
            [TRACKED_BASELINE, TRACKED_CANDIDATE],
        )

    def test_packet_is_deterministic_semantic_and_hides_revisions(self) -> None:
        first = comparison_evidence.generate_packet(RESULTS, RESULTS, POLICY)
        second = comparison_evidence.generate_packet(RESULTS, RESULTS, POLICY)
        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )
        self.assertEqual(first["schema_version"], 2)
        self.assertEqual(first["evidence_kind"], "comparison")
        self.assertTrue(all(item["source_type"] == "validated_comparison" for item in first["evidence"]))
        self.assertNotIn("source_revision", json.dumps(first))

    def test_unified_runner_passes_and_uses_schema_two(self) -> None:
        report = run_guardian.run_deterministic_pipeline(
            RESULTS, POLICY, mode="never", baseline_results=RESULTS
        )
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["comparison"]["status"], "passed")
        self.assertEqual(report["authoritative_exit_code"], 0)

    def test_tracked_pair_passes_and_regression_is_relative_only_failure(self) -> None:
        passed = run_guardian.run_deterministic_pipeline(
            TRACKED_CANDIDATE,
            TRACKED_POLICY,
            mode="never",
            baseline_results=TRACKED_BASELINE,
        )
        self.assertEqual(passed["authoritative_exit_code"], 0)
        failed = run_guardian.run_deterministic_pipeline(
            TRACKED_REGRESSION,
            TRACKED_POLICY,
            mode="never",
            baseline_results=TRACKED_BASELINE,
        )
        self.assertEqual(failed["authoritative_exit_code"], 1)
        process = next(
            item for item in failed["comparison"]["results"]
            if item["metric"] == "median_p95_process_time"
        )
        self.assertEqual(process["absolute"]["status"], "passed")
        self.assertEqual(process["relative"]["status"], "failed")

    def test_cli_baseline_with_v2_is_configuration_exit_two(self) -> None:
        completed = subprocess.run(
            [
                check_budgets.sys.executable,
                str(ROOT / "tools/check_budgets.py"),
                "--baseline-results", RESULTS,
                RESULTS,
                "examples/minimal_project/budgets/performance_budgets.json",
            ],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
