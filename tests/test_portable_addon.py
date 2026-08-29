from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools import check_budgets
from tools import validate_results


ROOT = Path(__file__).resolve().parents[1]


def generic_capture(source_revision: str | None = None) -> dict[str, object]:
    samples = [
        {
            "sample_index": 1,
            "measured_frame": 2,
            "elapsed_measurement_usec": 2000,
            "process_time_ms": 1.0,
            "physics_process_time_ms": 0.2,
            "memory_static_bytes": 1000,
            "object_count": 20,
            "node_count": 8,
            "orphan_node_count": 0,
        },
        {
            "sample_index": 2,
            "measured_frame": 3,
            "elapsed_measurement_usec": 3000,
            "process_time_ms": 1.5,
            "physics_process_time_ms": 0.3,
            "memory_static_bytes": 1100,
            "object_count": 21,
            "node_count": 9,
            "orphan_node_count": 0,
        },
    ]
    limitation = [
        "Global monitors are not profile owned.",
        validate_results.GENERIC_MEMORY_STORAGE_LIMITATION,
        "Headless capture does not establish rendering or GPU performance.",
    ]
    if source_revision is None:
        limitation.append("No source revision was supplied; the exact source revision is unknown.")
    return {
        "result_type": "performance_budget_guardian_capture",
        "schema_version": 1,
        "addon": {"name": "Performance Budget Guardian", "version": "1.0.1"},
        "profile": "main_scene",
        "project_name": "Independent Fixture",
        "run_id": "fixture-run-001",
        "godot_version": "4.5.1.stable.official.f62fdbde1",
        "warmup_frames": 1,
        "measured_frames": 3,
        "sampling_interval_frames": 2,
        "percentile_definition": validate_results.EXPECTED_PERCENTILE_DEFINITION,
        "started_at_utc": "2026-08-29T00:00:00Z",
        "ended_at_utc": "2026-08-29T00:00:01Z",
        "source_revision": source_revision,
        "headless": True,
        "measurement_configuration": {
            "auto_start": True,
            "auto_quit": True,
            "output_path": "res://results",
        },
        "environment": {
            "debug_build": True,
            "os_name": "FixtureOS",
            "os_version": "1",
            "display_driver": "headless",
        },
        "metric_availability": {
            "memory_static_bytes": {
                "available": True,
                "debug_only": True,
                "reason": "fixture memory is available",
            }
        },
        "samples": samples,
        "summary": {
            "timing": {
                "process_time_ms": validate_results.timing_stats([1.0, 1.5]),
                "physics_process_time_ms": validate_results.timing_stats([0.2, 0.3]),
            },
            "counts": {
                "memory_static_bytes": validate_results.series_stats([1000, 1100]),
                "object_count": validate_results.series_stats([20, 21]),
                "node_count": validate_results.series_stats([8, 9]),
                "orphan_node_count": validate_results.series_stats([0, 0]),
            },
            "measurement_duration_ms": 3.0,
            "capture_duration_ms": 4.0,
        },
        "known_limitations": limitation,
    }


class AddonStructureTests(unittest.TestCase):
    def test_manifest_scripts_and_example_references_exist(self) -> None:
        paths = (
            "addons/performance_budget_guardian/plugin.cfg",
            "addons/performance_budget_guardian/plugin.gd",
            "addons/performance_budget_guardian/performance_probe.gd",
            "addons/performance_budget_guardian/README.md",
            "examples/minimal_project/project.godot",
            "examples/minimal_project/main.tscn",
            "examples/minimal_project/main.gd",
            "examples/minimal_project/test_probe.gd",
        )
        for relative in paths:
            self.assertTrue((ROOT / relative).is_file(), relative)
        scene = (ROOT / "examples/minimal_project/main.tscn").read_text(encoding="utf-8")
        self.assertIn("res://addons/performance_budget_guardian/performance_probe.gd", scene)

    def test_probe_contract_has_no_ai_or_private_absolute_path(self) -> None:
        source = (ROOT / "addons/performance_budget_guardian/performance_probe.gd").read_text(encoding="utf-8")
        lowered = source.lower()
        self.assertNotIn("openai", lowered)
        self.assertNotIn("workload_time_usec", source)
        self.assertNotIn("retained_node", source)
        self.assertNotIn("owned_actor", source)
        self.assertNotIn("c:\\users\\", lowered)
        for argument in (
            "--pbg-profile=",
            "--pbg-warmup-frames=",
            "--pbg-measured-frames=",
            "--pbg-sampling-interval=",
            "--pbg-output=",
            "--pbg-run-id=",
            "--pbg-source-revision=",
            "--pbg-auto-quit",
        ):
            self.assertIn(argument, source)
        self.assertIn("Result already exists; provide a new run ID", source)
        self.assertIn("_run_id_explicitly_supplied", source)
        self.assertIn(validate_results.GENERIC_MEMORY_STORAGE_LIMITATION, source)


class GenericValidationTests(unittest.TestCase):
    def validate(self, capture: dict[str, object]) -> validate_results.Validation:
        validation = validate_results.Validation()
        validate_results.validate_generic_result(capture, Path("capture.json"), validation)
        return validation

    def test_valid_generic_profile_and_null_revision(self) -> None:
        validation = self.validate(generic_capture())
        self.assertEqual(validation.errors, [])

    def test_supplied_revision_is_recorded_without_interpretation(self) -> None:
        capture = generic_capture("feature/probe-v1")
        self.assertEqual(capture["source_revision"], "feature/probe-v1")
        self.assertEqual(self.validate(capture).errors, [])

    def test_probe_storage_memory_limitation_is_required(self) -> None:
        capture = generic_capture()
        capture["known_limitations"].remove(validate_results.GENERIC_MEMORY_STORAGE_LIMITATION)
        errors = self.validate(capture).errors
        self.assertTrue(any("probe-storage memory limitation" in error for error in errors))

    def test_old_addon_version_requires_actionable_recapture(self) -> None:
        capture = generic_capture()
        capture["addon"]["version"] = "1.0.0"
        errors = self.validate(capture).errors
        self.assertIn(
            "capture.json: addon version '1.0.0' is unsupported; expected '1.0.1'; "
            "recapture with the current addon and a new run ID",
            errors,
        )

    def test_invalid_profile_numeric_path_samples_and_summary_fail(self) -> None:
        variants = []
        profile = generic_capture()
        profile["profile"] = "../escape"
        variants.append(profile)
        numbers = generic_capture()
        numbers["sampling_interval_frames"] = 4
        variants.append(numbers)
        path = generic_capture()
        path["measurement_configuration"]["output_path"] = "C:/private"
        variants.append(path)
        sequence = generic_capture()
        sequence["samples"][1]["sample_index"] = 3
        variants.append(sequence)
        summary = generic_capture()
        summary["summary"]["timing"]["process_time_ms"]["p95"] = 99
        variants.append(summary)
        limitation = generic_capture()
        limitation["known_limitations"] = ["Headless only."]
        variants.append(limitation)
        for capture in variants:
            with self.subTest(profile=capture.get("profile")):
                self.assertTrue(self.validate(capture).errors)

    def test_generic_evidence_is_profile_based_and_budget_compatible(self) -> None:
        capture = generic_capture()
        validation = self.validate(capture)
        packet = validate_results.generic_evidence_packet(
            ["examples/fixtures"],
            [Path("examples/fixtures/capture.json")],
            [(Path("examples/fixtures/capture.json"), capture)],
            validation,
        )
        self.assertEqual(packet["validation"]["status"], "passed")
        self.assertTrue(all(not Path(item["source"]).is_absolute() for item in packet["evidence"]))
        profile_items = [item for item in packet["evidence"] if "profile" in item]
        self.assertTrue(profile_items)
        self.assertTrue(all(item["profile"] == "main_scene" for item in profile_items))
        self.assertIn(
            validate_results.GENERIC_MEMORY_STORAGE_LIMITATION,
            [item["statement"] for item in packet["limitations"]],
        )
        config = {
            "schema_version": 2,
            "budgets": [
                {
                    "id": "process",
                    "profile": "main_scene",
                    "metric": "median_p95_process_time",
                    "maximum": 1.5,
                    "unit": "ms",
                    "description": "Equality passes.",
                },
                {
                    "id": "nodes",
                    "profile": "main_scene",
                    "metric": "median_peak_node_count",
                    "maximum": 9,
                    "unit": "nodes",
                    "description": "Peak node policy.",
                },
            ],
        }
        rules = check_budgets.parse_budget_configuration(config)
        report = check_budgets.evaluate_budgets(rules, packet)
        self.assertEqual(report["budget_schema_version"], 2)
        self.assertEqual(report["summary"], {"total": 2, "passed": 2, "failed": 0})
        self.assertTrue(all("profile" in result and "scenario" not in result for result in report["results"]))

    def test_v2_rejects_unsafe_profiles_and_synthetic_metrics(self) -> None:
        base = {
            "schema_version": 2,
            "budgets": [{
                "id": "bad",
                "profile": "../escape",
                "metric": "median_p95_process_time",
                "maximum": 1,
                "unit": "ms",
                "description": "Invalid profile.",
            }],
        }
        with self.assertRaises(check_budgets.BudgetConfigurationError):
            check_budgets.parse_budget_configuration(base)
        synthetic = copy.deepcopy(base)
        synthetic["budgets"][0].update(profile="main_scene", metric="post_cleanup_retained_nodes", unit="nodes")
        with self.assertRaises(check_budgets.BudgetConfigurationError):
            check_budgets.parse_budget_configuration(synthetic)

    def test_canonical_live_fixture_validates_and_passes_its_budget(self) -> None:
        fixture_path = ROOT / "examples/fixtures/main_scene-godot-4.5.1.json"
        capture = json.loads(fixture_path.read_text(encoding="utf-8"))
        validation = self.validate(capture)
        self.assertEqual(validation.errors, [])
        packet = validate_results.generic_evidence_packet(
            ["examples/fixtures/main_scene-godot-4.5.1.json"],
            [fixture_path],
            [(fixture_path, capture)],
            validation,
        )
        rules = check_budgets.load_budget_configuration(
            ROOT / "examples/minimal_project/budgets/performance_budgets.json"
        )
        report = check_budgets.evaluate_budgets(rules, packet)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["summary"], {"total": 2, "passed": 2, "failed": 0})
        serialized = fixture_path.read_text(encoding="utf-8").lower()
        self.assertNotIn("c:\\users\\", serialized)
        self.assertNotIn("openai", serialized)

    def test_mixed_result_types_fail_at_cli_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "generic.json").write_text(json.dumps(generic_capture()), encoding="utf-8")
            synthetic = {"schema_version": 1, "scenario": "healthy", "run_id": "synthetic"}
            (root / "synthetic.json").write_text(json.dumps(synthetic), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "tools/validate_results.py"), str(root)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("mixed synthetic and generic result types", completed.stderr)


if __name__ == "__main__":
    unittest.main()
