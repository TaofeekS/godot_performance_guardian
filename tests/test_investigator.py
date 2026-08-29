from __future__ import annotations

import asyncio
from contextlib import redirect_stderr, redirect_stdout
import copy
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

from openai import RateLimitError

import agent.investigator as investigator


FIXTURE_RESULTS_DIRECTORY = "tests/fixtures/generic_results"
EVIDENCE_PACKET_PATH = (
    investigator.REPOSITORY_ROOT / "tests/fixtures/investigator/evidence_packet.json"
)
GENERIC_EVIDENCE_PACKET_PATH = (
    investigator.REPOSITORY_ROOT
    / "tests/fixtures/investigator/generic_evidence_packet.json"
)


def load_evidence_packet() -> dict[str, object]:
    return json.loads(EVIDENCE_PACKET_PATH.read_text(encoding="utf-8"))


def load_generic_evidence_packet() -> dict[str, object]:
    return json.loads(GENERIC_EVIDENCE_PACKET_PATH.read_text(encoding="utf-8"))


class ResultsDirectoryTests(unittest.TestCase):
    def test_resolves_repository_relative_results_directory(self) -> None:
        resolved, relative, count = investigator.resolve_results_directory(
            FIXTURE_RESULTS_DIRECTORY
        )

        self.assertEqual(resolved, investigator.REPOSITORY_ROOT / FIXTURE_RESULTS_DIRECTORY)
        self.assertEqual(relative, FIXTURE_RESULTS_DIRECTORY)
        self.assertEqual(count, 1)

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
    def test_external_workspace_is_forwarded_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            results = root / "captures"
            results.mkdir()
            (results / "one.json").write_text("{}", encoding="utf-8")
            completed = subprocess.CompletedProcess(
                [], 0, json.dumps(load_generic_evidence_packet()), ""
            )
            runner = Mock(return_value=completed)
            investigator.run_validator(
                "captures", workspace_root=root, subprocess_runner=runner
            )
            command = runner.call_args.args[0]
            self.assertIn("--workspace-root", command)
            self.assertIn(str(root.resolve()), command)
            self.assertEqual(runner.call_args.kwargs["cwd"], root.resolve())
            self.assertNotIn("shell", runner.call_args.kwargs)

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
            "schema_version": 1,
            "evidence_kind": "synthetic",
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
            "schema_version": 1,
            "evidence_kind": "failed",
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

    def test_runs_existing_validator_against_tracked_fixture(self) -> None:
        evidence = investigator.run_validator(FIXTURE_RESULTS_DIRECTORY)

        self.assertEqual(evidence["validation"]["status"], "passed", evidence)
        self.assertEqual(evidence["validation"]["exit_code"], 0)
        self.assertEqual(evidence["results_directory"], FIXTURE_RESULTS_DIRECTORY)
        self.assertEqual(evidence["validation"]["validated_file_count"], 1)
        self.assertTrue(all(item.get("profile") == "main_scene" for item in evidence["evidence"][1:]))


class EvidencePacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = load_evidence_packet()
        cls.by_id = {item["id"]: item for item in cls.packet["evidence"]}

    def test_packet_is_deterministic_and_json_round_trippable(self) -> None:
        second = load_evidence_packet()
        canonical = json.dumps(self.packet, sort_keys=True, separators=(",", ":"))
        self.assertEqual(canonical, json.dumps(second, sort_keys=True, separators=(",", ":")))
        self.assertEqual(json.loads(canonical), self.packet)

    def test_packet_has_unique_opaque_evidence_ids(self) -> None:
        identifiers = [item["id"] for item in self.packet["evidence"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for item in self.packet["evidence"]:
            self.assertFalse(Path(item["source"]).is_absolute())

    def test_packet_aggregate_values_are_self_consistent(self) -> None:
        resolved = investigator._semantic_evidence(self.packet)
        healthy_workload = resolved["healthy_workload"]["value"]
        cpu_workload = resolved["cpu_workload"]["value"]
        healthy_duration = resolved["healthy_duration"]["value"]
        cpu_duration = resolved["cpu_duration"]["value"]
        self.assertEqual(resolved["validated_count"]["value"], 9)
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
        cls.packet = load_evidence_packet()

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
            results_directory=FIXTURE_RESULTS_DIRECTORY,
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
            results_directory=FIXTURE_RESULTS_DIRECTORY,
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
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])
        self.assertEqual(exit_code, 0)
        self.assertEqual(runner.call_count, 1)
        self.assertIn(investigator.REPORT_SOURCE_DISCLOSURE, stdout.getvalue())
        self.assertIn("WARNING: model contribution failed", stderr.getvalue())
        self.assertNotIn(invalid, stderr.getvalue())
        self.assertNotIn(invalid, stdout.getvalue())

    def test_cli_failure_fallback_remains_nonzero(self) -> None:
        packet = investigator._evidence_packet(
            validation_status="failed",
            validator_invoked=True,
            results_directory=FIXTURE_RESULTS_DIRECTORY,
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
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])

        self.assertEqual(exit_code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertIn(investigator.REPORT_SOURCE_DISCLOSURE, stdout.getvalue())
        self.assertNotIn(rejected, stdout.getvalue() + stderr.getvalue())

    def test_cli_grounded_validation_failure_remains_nonzero(self) -> None:
        packet = investigator._evidence_packet(
            validation_status="failed",
            validator_invoked=True,
            results_directory=FIXTURE_RESULTS_DIRECTORY,
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
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])

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
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])

        self.assertEqual(exit_code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("G00_EVIDENCE_PACKET", stderr.getvalue())


class GenericGroundingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = load_generic_evidence_packet()

    def fallback(self, packet: dict[str, object] | None = None) -> str:
        return investigator.render_deterministic_fallback(packet or self.packet)

    def test_dispatches_synthetic_generic_and_failed_packets(self) -> None:
        self.assertEqual(investigator._packet_evidence_kind(load_evidence_packet()), "synthetic")
        self.assertEqual(investigator._packet_evidence_kind(self.packet), "generic")
        failed = investigator._evidence_packet(
            validation_status="failed",
            validator_invoked=True,
            results_directory=FIXTURE_RESULTS_DIRECTORY,
            json_file_count=1,
            exit_code=1,
        )
        self.assertEqual(investigator._packet_evidence_kind(failed), "failed")

    def test_profile_discovery_excludes_reserved_all_and_unrelated_items(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["evidence"].append(
            {
                "id": "PX_IGNORED",
                "claim": "Unrelated profile note.",
                "metric": "unrelated_metric",
                "profile": "ignored_profile",
                "source": "tests/fixtures/investigator",
                "source_type": "validated_aggregate",
                "unit": None,
                "value": "ignored",
            }
        )
        semantic = investigator._generic_semantic_evidence(packet)
        self.assertEqual(list(semantic["profiles"]), ["battle_scene", "main_scene"])
        self.assertNotIn("all", semantic["profiles"])
        self.assertNotIn("ignored_profile", semantic["profiles"])

    def test_reserved_all_cannot_be_reported_as_a_profile(self) -> None:
        report = self.fallback().replace(
            "Profile battle_scene recorded",
            "Profile all is validation metadata [PX_COUNT].\nProfile battle_scene recorded",
            1,
        )
        self.assertIn(
            "G26_RESERVED_PROFILE",
            investigator.validate_grounded_report(report, self.packet),
        )

    def test_missing_unsupported_and_mixed_identity_packets_fail(self) -> None:
        missing_kind = copy.deepcopy(self.packet)
        missing_kind.pop("evidence_kind")
        unsupported = copy.deepcopy(self.packet)
        unsupported["evidence_kind"] = "portable"
        mixed_identity = copy.deepcopy(self.packet)
        mixed_identity["evidence"][1]["scenario"] = "generic"
        for packet in (missing_kind, unsupported, mixed_identity):
            with self.subTest(packet=packet.get("evidence_kind")):
                with self.assertRaises(investigator.EvidenceSchemaError):
                    investigator._packet_evidence_kind(packet)
                self.assertEqual(
                    investigator.validate_grounded_report(self.fallback(), packet),
                    ["G15_EVIDENCE_SCHEMA"],
                )

    def test_fully_grounded_generic_fallback_passes_and_covers_profiles(self) -> None:
        report = self.fallback()
        self.assertEqual(investigator.validate_grounded_report(report, self.packet), [])
        self.assertIn("battle_scene", report)
        self.assertIn("main_scene", report)
        self.assertNotIn("Profile all", report)
        self.assertIn("Static-memory evidence for battle_scene was unavailable", report)
        self.assertIn("Source-revision availability for main_scene was present", report)
        for heading in investigator.REPORT_HEADINGS:
            self.assertIn(heading, report)

    def test_fully_grounded_model_style_generic_report_passes(self) -> None:
        report = self.fallback().replace(
            investigator.REPORT_SOURCE_DISCLOSURE + "\n", ""
        )
        self.assertEqual(investigator.validate_grounded_report(report, self.packet), [])

    def test_fallback_is_deterministic_and_uses_renumbered_ids(self) -> None:
        first = self.fallback()
        self.assertEqual(first, self.fallback(copy.deepcopy(self.packet)))
        packet = copy.deepcopy(self.packet)
        replacements: dict[str, str] = {}
        for index, item in enumerate(packet["evidence"], 200):
            replacements[item["id"]] = f"Q{index}"
            item["id"] = replacements[item["id"]]
        for index, limitation in enumerate(packet["limitations"], 300):
            limitation["id"] = f"Q{index}"
        report = self.fallback(packet)
        self.assertEqual(investigator.validate_grounded_report(report, packet), [])
        self.assertIn("[Q200]", report)
        self.assertNotIn("[PX_COUNT]", report)

    def test_missing_or_duplicate_generic_semantics_fail_safely(self) -> None:
        missing = copy.deepcopy(self.packet)
        missing["evidence"] = [
            item for item in missing["evidence"] if item["id"] != "PX_BP"
        ]
        duplicate = copy.deepcopy(self.packet)
        repeated = copy.deepcopy(duplicate["evidence"][1])
        repeated["id"] = "PX_DUPLICATE"
        duplicate["evidence"].append(repeated)
        for packet in (missing, duplicate):
            with self.assertRaises(investigator.EvidenceSchemaError):
                investigator.render_deterministic_fallback(packet)
            self.assertEqual(
                investigator.validate_grounded_report(self.fallback(), packet),
                ["G15_EVIDENCE_SCHEMA"],
            )

    def test_unknown_citation_and_altered_number_fail(self) -> None:
        report = self.fallback().replace("[PX_BP]", "[UNKNOWN]", 1)
        self.assertIn("G02_UNKNOWN_EVIDENCE", investigator.validate_grounded_report(report, self.packet))
        altered = self.fallback().replace("1.250000 ms", "99.250000 ms", 1)
        self.assertIn("G07_UNSUPPORTED_NUMBER", investigator.validate_grounded_report(altered, self.packet))

    def test_missing_citation_and_profile_coverage_fail(self) -> None:
        missing_citation = self.fallback().replace(" [PX_MPH]", "")
        self.assertIn(
            "G03_REQUIRED_EVIDENCE_MISSING",
            investigator.validate_grounded_report(missing_citation, self.packet),
        )
        omitted_profile = self.fallback().replace("main_scene", "second profile")
        self.assertIn(
            "G17_PROFILE_COVERAGE",
            investigator.validate_grounded_report(omitted_profile, self.packet),
        )

    def test_mixed_availability_states_render_without_values(self) -> None:
        packet = copy.deepcopy(self.packet)
        for item in packet["evidence"]:
            if item["id"] == "PX_BMA":
                item["value"] = "mixed"
            if item["id"] == "PX_MRA":
                item["value"] = "mixed"
        report = self.fallback(packet)
        self.assertEqual(investigator.validate_grounded_report(report, packet), [])
        self.assertIn("Static-memory evidence for battle_scene was mixed", report)
        self.assertIn("Source-revision availability for main_scene was mixed", report)

    def test_unavailable_memory_value_is_rejected(self) -> None:
        report = self.fallback().replace(
            "Static-memory evidence for battle_scene was unavailable [PX_BMA].",
            "Static-memory evidence for battle_scene was unavailable at 999 bytes [PX_BMA].",
        )
        errors = investigator.validate_grounded_report(report, self.packet)
        self.assertIn("G20_INVENTED_MEMORY", errors)
        self.assertIn("G07_UNSUPPORTED_NUMBER", errors)

    def test_synthetic_claims_and_unsupported_causes_are_rejected(self) -> None:
        synthetic = self.fallback().replace(
            "Profile battle_scene recorded",
            "The healthy scenario retained nodes. Profile battle_scene recorded",
            1,
        )
        self.assertIn("G22_SYNTHETIC_CLAIM", investigator.validate_grounded_report(synthetic, self.packet))
        causal = self.fallback().replace(
            "do not establish a causal defect",
            "show a memory leak",
            1,
        )
        self.assertIn("G23_UNSUPPORTED_GENERIC_CAUSE", investigator.validate_grounded_report(causal, self.packet))

    def test_missing_limitations_and_uncertainty_are_rejected(self) -> None:
        limitation = self.packet["limitations"][0]
        report = self.fallback().replace(
            f"- {limitation['statement']} [{limitation['id']}]\n", ""
        ).replace(investigator.REQUIRED_UNCERTAINTY, "A cause was established.")
        errors = investigator.validate_grounded_report(report, self.packet)
        self.assertIn("G21_GENERIC_LIMITATION_MISSING", errors)
        self.assertIn("G08_REQUIRED_UNCERTAINTY", errors)

    def test_revision_equality_or_value_language_is_rejected(self) -> None:
        report = self.fallback().replace(
            "Source-revision availability for main_scene was present [PX_MRA].",
            "Source-revision availability for main_scene was present and revisions were equal [PX_MRA].",
        )
        self.assertIn("G24_REVISION_VALUE_OR_EQUALITY", investigator.validate_grounded_report(report, self.packet))

    def test_unsafe_and_untestable_recommendations_are_rejected(self) -> None:
        report = self.fallback().replace(
            "- Compare repeated battle_scene captures",
            "- Fix C:\\private\\project then admire repeated battle_scene captures",
            1,
        )
        errors = investigator.validate_grounded_report(report, self.packet)
        self.assertIn("G12_MUTATING_RECOMMENDATION", errors)
        self.assertIn("G13_UNTESTABLE_RECOMMENDATION", errors)
        self.assertIn("G25_SENSITIVE_OUTPUT", errors)

    def test_cli_uses_generic_fallback_once_without_rejected_text(self) -> None:
        rejected = "REJECTED GENERIC MODEL OUTPUT"
        result = SimpleNamespace(
            final_output=rejected,
            new_items=[SimpleNamespace(output=json.dumps(self.packet))],
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        runner = Mock(return_value=result)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-credential"}):
            with patch.object(investigator.Runner, "run_sync", runner):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])
        self.assertEqual(exit_code, 0)
        self.assertEqual(runner.call_count, 1)
        self.assertIn(investigator.REPORT_SOURCE_DISCLOSURE, stdout.getvalue())
        self.assertNotIn(rejected, stdout.getvalue() + stderr.getvalue())


class TypedContributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = load_generic_evidence_packet()

    def contribution(
        self,
        *,
        hypotheses: list[dict[str, object]] | None = None,
        recommendations: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {
            "hypotheses": [] if hypotheses is None else hypotheses,
            "recommendations": (
                [{"action": "compare", "evidence_ids": ["PX_BP", "PX_BPH"]}]
                if recommendations is None
                else recommendations
            ),
        }

    def test_accepts_enum_recommendation_and_optional_hypotheses(self) -> None:
        accepted, errors = investigator.accepted_model_contribution(
            self.contribution(), self.packet
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(accepted)
        assert accepted is not None
        self.assertEqual(accepted.hypotheses, [])
        self.assertEqual(accepted.recommendations[0].action.value, "compare")
        report = investigator.render_model_contribution(self.packet, accepted)
        self.assertIn(investigator.MODEL_REPORT_SOURCE_DISCLOSURE, report)
        self.assertNotIn(investigator.REPORT_SOURCE_DISCLOSURE, report)
        self.assertEqual(investigator.validate_grounded_report(report, self.packet), [])

    def test_filters_invalid_hypothesis_but_keeps_real_recommendation(self) -> None:
        accepted, errors = investigator.accepted_model_contribution(
            self.contribution(
                hypotheses=[
                    {
                        "explanation": "This proves a memory leak",
                        "evidence_ids": ["PX_MM"],
                    }
                ]
            ),
            self.packet,
        )

        self.assertIn("C03_HYPOTHESIS_TEXT", errors)
        self.assertIsNotNone(accepted)
        assert accepted is not None
        self.assertEqual(accepted.hypotheses, [])
        self.assertEqual(len(accepted.recommendations), 1)

    def test_rejects_duplicate_unknown_and_missing_recommendation_evidence(self) -> None:
        for evidence_ids in ([], ["PX_BP", "PX_BP"], ["UNKNOWN"]):
            accepted, errors = investigator.accepted_model_contribution(
                self.contribution(
                    recommendations=[
                        {"action": "inspect", "evidence_ids": evidence_ids}
                    ]
                ),
                self.packet,
            )
            self.assertIsNone(accepted)
            self.assertIn(
                "C01_TYPED_CONTRIBUTION"
                if not evidence_ids
                else "C05_RECOMMENDATION_REQUIRED",
                errors,
            )

    def test_rejects_markdown_newlines_measurements_paths_and_citations(self) -> None:
        invalid_texts = (
            "Use **careful** comparison",
            "Compare one line\nwith another",
            "Timing was 5 ms",
            "Inspect C:\\private\\capture",
            "Compare the result [PX_BP]",
            "This is a bottleneck",
        )
        for explanation in invalid_texts:
            accepted, errors = investigator.accepted_model_contribution(
                self.contribution(
                    hypotheses=[
                        {"explanation": explanation, "evidence_ids": ["PX_BP"]}
                    ]
                ),
                self.packet,
            )
            self.assertIsNotNone(accepted)
            self.assertIn("C03_HYPOTHESIS_TEXT", errors)

    def test_typed_schema_bounds_items_and_text(self) -> None:
        with self.assertRaises(Exception):
            investigator.InvestigatorContribution.model_validate(
                {"hypotheses": [], "recommendations": []}
            )
        with self.assertRaises(Exception):
            investigator.InvestigatorContribution.model_validate(
                self.contribution(
                    hypotheses=[
                        {"explanation": "x" * 241, "evidence_ids": ["PX_BP"]}
                    ]
                )
            )
        with self.assertRaises(Exception):
            investigator.InvestigatorContribution.model_validate(
                self.contribution(
                    recommendations=[
                        {"action": "compare", "evidence_ids": ["PX_BP"]}
                        for _ in range(4)
                    ]
                )
            )

    def test_cli_prints_locally_rendered_model_contribution(self) -> None:
        contribution = investigator.InvestigatorContribution.model_validate(
            self.contribution()
        )
        result = SimpleNamespace(
            final_output=contribution,
            new_items=[SimpleNamespace(output=json.dumps(self.packet))],
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        runner = Mock(return_value=result)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-credential"}):
            with patch.object(investigator.Runner, "run_sync", runner):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])

        self.assertEqual(exit_code, 0)
        self.assertEqual(runner.call_count, 1)
        self.assertIn(investigator.MODEL_REPORT_SOURCE_DISCLOSURE, stdout.getvalue())
        self.assertNotIn("fallback", stderr.getvalue().lower())

    def test_typed_output_failure_recovers_hook_packet_without_retry(self) -> None:
        async def record_packet(hooks: investigator.EvidenceCaptureHooks) -> None:
            await hooks.on_tool_end(
                None,
                None,
                SimpleNamespace(name="validate_benchmark_results"),
                json.dumps(self.packet),
            )

        def fail_after_tool(*args: object, **kwargs: object) -> object:
            asyncio.run(record_packet(kwargs["hooks"]))
            raise investigator.ModelBehaviorError("untrusted typed output")

        stdout = io.StringIO()
        stderr = io.StringIO()
        runner = Mock(side_effect=fail_after_tool)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-credential"}):
            with patch.object(investigator.Runner, "run_sync", runner):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])

        self.assertEqual(exit_code, 0)
        self.assertEqual(runner.call_count, 1)
        self.assertIn(investigator.REPORT_SOURCE_DISCLOSURE, stdout.getvalue())
        self.assertNotIn("untrusted typed output", stdout.getvalue() + stderr.getvalue())

    def test_typed_output_failure_without_packet_is_hard_failure(self) -> None:
        stderr = io.StringIO()
        runner = Mock(side_effect=investigator.ModelBehaviorError("hidden"))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-credential"}):
            with patch.object(investigator.Runner, "run_sync", runner):
                with redirect_stderr(stderr):
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])

        self.assertEqual(exit_code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("G00_EVIDENCE_PACKET", stderr.getvalue())
        self.assertNotIn("hidden", stderr.getvalue())


class InvestigatorConfigurationTests(unittest.TestCase):
    def test_agent_has_exact_name_and_single_required_tool(self) -> None:
        built = investigator.build_investigator()

        self.assertEqual(built.name, "Godot Performance Investigator")
        self.assertEqual([tool.name for tool in built.tools], ["validate_benchmark_results"])
        self.assertEqual(built.model_settings.tool_choice, "required")
        self.assertFalse(built.model_settings.parallel_tool_calls)
        self.assertEqual(built.tool_use_behavior, "run_llm_again")
        self.assertTrue(built.reset_tool_choice)
        self.assertIs(built.output_type, investigator.InvestigatorContribution)

    def test_model_default_override_and_required_report_sections(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_MODEL", None)
            default_agent = investigator.build_investigator()
        with patch.dict(os.environ, {"OPENAI_MODEL": "test-model"}):
            configured_agent = investigator.build_investigator()

        self.assertEqual(default_agent.model, "gpt-4.1-mini")
        self.assertEqual(configured_agent.model, "test-model")
        for requirement in (
            "opaque evidence ID",
            "typed contribution",
            "three recommendations",
            "three hypotheses",
            "schema enum",
            "memory leak",
            "read-only controlled",
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
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])

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
        headers: dict[str, str] = {"authorization": "hidden-response-header"}
        if request_id is not None:
            headers["x-request-id"] = request_id
        if retry_after is not None:
            headers["retry-after"] = retry_after
        response = SimpleNamespace(
            status_code=429,
            headers=headers,
            request=SimpleNamespace(
                method="POST",
                url="https://api.openai.com/v1/responses",
                headers={"authorization": "Bearer hidden-authorization-value"},
            ),
        )
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
                    exit_code = investigator.main([FIXTURE_RESULTS_DIRECTORY])
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
