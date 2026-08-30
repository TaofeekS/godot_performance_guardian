from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools import calibrate_budgets as calibration


def packet(*, profiles: dict[str, tuple[int | float, int | float, int | float]] | None = None, runs: int = 5) -> dict[str, object]:
    profiles = profiles or {"main_scene": (0.529, 3, 21)}
    evidence: list[dict[str, object]] = [
        {"id": "count", "metric": "validated_file_count", "profile": "all", "source_type": "validated_result", "unit": "files", "value": runs * len(profiles)}
    ]
    index = 0
    for profile, values in profiles.items():
        for metric, unit, value in (
            ("median_p95_process_time", "ms", values[0]),
            ("median_peak_node_count", "nodes", values[1]),
            ("median_peak_object_count", "objects", values[2]),
        ):
            index += 1
            evidence.append({
                "id": f"opaque-{index}", "metric": metric, "profile": profile,
                "run_count": runs, "source_type": "validated_aggregate", "unit": unit, "value": value,
            })
    return {
        "packet_type": "godot_performance_evidence",
        "schema_version": 1,
        "evidence_kind": "generic",
        "results_directory": "results",
        "validation": {
            "status": "passed", "exit_code": 0,
            "candidate_file_count": runs * len(profiles),
            "validated_file_count": runs * len(profiles),
        },
        "evidence": evidence,
        "limitations": [{"id": "GL1", "statement": "Validated limitation."}],
    }


class CalibrationFormulaTests(unittest.TestCase):
    def test_balanced_formulas_policy_and_report(self) -> None:
        policy, report = calibration.build_calibration(packet())
        rules = {item["metric"]: item for item in policy["budgets"]}
        self.assertEqual(rules["median_p95_process_time"]["maximum"], 0.8)
        self.assertEqual(rules["median_p95_process_time"]["maximum_increase_percent"], 20)
        self.assertEqual(rules["median_peak_node_count"]["maximum"], 4)
        self.assertEqual(rules["median_peak_object_count"]["maximum"], 24)
        self.assertEqual(rules["median_peak_node_count"]["maximum_increase_percent"], 5)
        self.assertFalse(report["calibration"]["proposal_authoritative"])
        self.assertEqual(report["validator"]["validated_file_count"], 5)
        self.assertEqual(report["proposed_policy"], policy)
        self.assertTrue(any("GPU" in item["statement"] for item in report["limitations"]))

    def test_zero_counts_and_upward_tenth_rounding(self) -> None:
        policy, _ = calibration.build_calibration(packet(profiles={"zero": (0.01, 0, 0)}))
        rules = {item["metric"]: item for item in policy["budgets"]}
        self.assertEqual(rules["median_p95_process_time"]["maximum"], 0.1)
        self.assertEqual(rules["median_peak_node_count"]["maximum"], 0)
        self.assertEqual(rules["median_peak_object_count"]["maximum"], 0)

    def test_multiple_profiles_sort_deterministically_and_long_ids_are_safe(self) -> None:
        long_profile = "p" * 64
        policy, report = calibration.build_calibration(
            packet(profiles={long_profile: (1, 2, 3), "alpha": (1, 2, 3), "9scene": (1, 2, 3)})
        )
        ids = [item["id"] for item in policy["budgets"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(len(item) <= 64 for item in ids))
        self.assertTrue(any("-" + calibration.hashlib.sha256(long_profile.encode()).hexdigest()[:8] + "-" in item for item in ids))
        self.assertTrue(any(item.startswith("profile-9scene-") for item in ids))
        self.assertEqual(
            [item["budget_id"] for item in report["recommendations"]], ids
        )

    def test_packet_failures_are_rejected(self) -> None:
        cases = []
        too_few = packet(runs=2)
        cases.append(too_few)
        synthetic = packet()
        synthetic["evidence_kind"] = "synthetic"
        cases.append(synthetic)
        missing = packet()
        missing["evidence"] = missing["evidence"][:-1]
        cases.append(missing)
        duplicate = packet()
        duplicate["evidence"].append(dict(duplicate["evidence"][1]))
        cases.append(duplicate)
        malformed = packet()
        malformed["evidence"][1]["value"] = float("nan")
        cases.append(malformed)
        for value in cases:
            with self.subTest(kind=value.get("evidence_kind")):
                with self.assertRaises(calibration.CalibrationError):
                    calibration.build_calibration(value)  # type: ignore[arg-type]


class CalibrationFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "results").mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_generation_calls_validator_once_and_writes_canonical_outputs(self) -> None:
        runner = Mock(return_value=packet())
        policy, report = calibration.generate(
            workspace_root=self.root,
            results_directory="results",
            policy_output="out/proposal.json",
            report_output="out/report.json",
            validator_runner=runner,
        )
        runner.assert_called_once_with("results", workspace_root=self.root)
        self.assertEqual(json.loads((self.root / "out/proposal.json").read_text()), policy)
        report_bytes = (self.root / "out/report.json").read_text(encoding="utf-8")
        self.assertEqual(report_bytes, calibration.canonical_json(report))
        self.assertEqual(list((self.root / "out").glob("*.tmp")), [])

    def test_output_path_trusts_shared_identity_containment_for_windows_aliases(self) -> None:
        short_root = Path("C:/Users/RUNNER~1/AppData/Local/Temp/workspace")
        long_target = Path(
            "C:/Users/runneradmin/AppData/Local/Temp/workspace/out/proposal.json"
        )
        with patch.object(
            calibration,
            "resolve_workspace_member",
            return_value=(long_target, "out/proposal.json"),
        ) as resolver:
            target, relative = calibration._output_path(
                short_root, "out/proposal.json", "policy output"
            )

        resolver.assert_called_once_with(
            short_root,
            "out/proposal.json",
            label="policy output",
            require_json=True,
        )
        self.assertEqual(target, long_target)
        self.assertEqual(relative, "out/proposal.json")

    def test_generation_refuses_collisions_and_unsafe_paths(self) -> None:
        (self.root / "existing.json").write_text("keep", encoding="utf-8")
        for policy_path in ("existing.json", "../escape.json"):
            with self.subTest(policy_path=policy_path):
                with self.assertRaises(calibration.CalibrationError):
                    calibration.generate(
                        workspace_root=self.root,
                        results_directory="results",
                        policy_output=policy_path,
                        report_output="report.json",
                        validator_runner=Mock(return_value=packet()),
                    )
        self.assertEqual((self.root / "existing.json").read_text(), "keep")

    def test_generation_rejects_a_resolved_symlink_escape(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir(exist_ok=True)
        link = self.root / "linked-output"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks are unavailable")
        try:
            with self.assertRaises(calibration.CalibrationError):
                calibration.generate(
                    workspace_root=self.root,
                    results_directory="results",
                    policy_output="linked-output/proposal.json",
                    report_output="report.json",
                    validator_runner=Mock(return_value=packet()),
                )
        finally:
            outside.rmdir()

    def test_apply_requires_explicit_replace_and_revalidates_schema(self) -> None:
        policy, _ = calibration.build_calibration(packet())
        proposal = self.root / "proposal.json"
        proposal.write_text(calibration.canonical_json(policy, pretty=True), encoding="utf-8")
        result = calibration.apply_proposal(
            workspace_root=self.root, proposal="proposal.json", budget_file="budgets/policy.json", replace=False
        )
        self.assertEqual(result["budget_file"], "budgets/policy.json")
        target = self.root / "budgets/policy.json"
        original = target.read_text()
        with self.assertRaises(calibration.CalibrationError):
            calibration.apply_proposal(
                workspace_root=self.root, proposal="proposal.json", budget_file="budgets/policy.json", replace=False
            )
        self.assertEqual(target.read_text(), original)
        calibration.apply_proposal(
            workspace_root=self.root, proposal="proposal.json", budget_file="budgets/policy.json", replace=True
        )
        self.assertEqual(json.loads(target.read_text()), policy)
        with self.assertRaises(calibration.CalibrationError):
            calibration.apply_proposal(
                workspace_root=self.root, proposal="proposal.json", budget_file="proposal.json", replace=True
            )
        self.assertEqual(list(self.root.rglob("*.tmp")), [])

    def test_invalid_proposal_and_cli_errors_return_two(self) -> None:
        (self.root / "bad.json").write_text('{"schema_version":2,"budgets":[]}', encoding="utf-8")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = calibration.main([
                "--workspace-root", str(self.root), "--apply-proposal", "bad.json",
                "--budget-file", "new.json",
            ])
        self.assertEqual(code, 2)
        self.assertIn("ERROR:", stderr.getvalue())
        self.assertNotIn(str(self.root), stderr.getvalue())

    def test_cli_generation_json_matches_written_report(self) -> None:
        original = calibration.run_validator_packet
        calibration.run_validator_packet = Mock(return_value=packet())
        try:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = calibration.main([
                    "--workspace-root", str(self.root), "--json",
                    "--policy-output", "out/policy.json", "--report-output", "out/report.json", "results",
                ])
        finally:
            calibration.run_validator_packet = original
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), (self.root / "out/report.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
