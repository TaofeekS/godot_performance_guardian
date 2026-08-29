from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

from tools import capture_project


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/reusable-performance-guardian.yml"


class CaptureProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "game"
        (self.project / "addons/performance_budget_guardian").mkdir(parents=True)
        (self.project / "project.godot").write_text(
            '[application]\nrun/main_scene="res://main.tscn"\n', encoding="utf-8"
        )
        (self.project / "main.tscn").write_text(
            '[ext_resource path="res://addons/performance_budget_guardian/performance_probe.gd" type="Script" id="1"]\n',
            encoding="utf-8",
        )
        (self.project / "addons/performance_budget_guardian/performance_probe.gd").write_text(
            "extends Node\n", encoding="utf-8"
        )
        self.godot = self.root / "godot.exe"
        self.godot.write_bytes(b"fixture")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _successful_runner(self) -> Mock:
        def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            output_arg = next(value for value in command if value.startswith("--pbg-output="))
            run_id_arg = next(value for value in command if value.startswith("--pbg-run-id="))
            output = output_arg.split("=", 1)[1].removeprefix("res://")
            run_id = run_id_arg.split("=", 1)[1]
            destination = self.project / output / f"{run_id}.json"
            destination.write_text("{}\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "capture ok", "")

        return Mock(side_effect=run)

    def test_three_isolated_processes_and_relative_manifest(self) -> None:
        runner = self._successful_runner()
        manifest, exit_code = capture_project.capture_project(
            workspace_root=self.root,
            godot_executable=self.godot,
            project_path="game",
            profile="main_scene",
            scene_path="res://main.tscn",
            run_prefix="ci-100-1",
            source_revision="abc123",
            subprocess_runner=runner,
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(runner.call_count, 3)
        self.assertEqual(manifest["status"], "passed")
        self.assertEqual(manifest["completed_runs"], 3)
        self.assertEqual(len(manifest["captures"]), 3)
        serialized = capture_project.canonical_json(manifest)
        self.assertNotIn(str(self.root), serialized)
        for index, call in enumerate(runner.call_args_list, 1):
            command = call.args[0]
            self.assertEqual(command[:5], [str(self.godot), "--headless", "--path", str(self.project), "--scene"])
            self.assertIn("res://main.tscn", command)
            self.assertIn(f"--pbg-run-id=ci-100-1-{index:02d}", command)
            self.assertIn("--pbg-source-revision=abc123", command)
            self.assertEqual(call.kwargs["cwd"], self.root)
            self.assertEqual(call.kwargs["timeout"], 300.0)
            self.assertNotIn("shell", call.kwargs)

    def test_collision_preserves_existing_output(self) -> None:
        existing = self.project / ".performance-guardian/main_scene/existing"
        existing.mkdir(parents=True)
        marker = existing / "marker.txt"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(capture_project.CaptureConfigurationError):
            capture_project.capture_project(
                workspace_root=self.root,
                godot_executable=self.godot,
                project_path="game",
                profile="main_scene",
                run_prefix="existing",
            )
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")

    def test_missing_capture_stops_and_writes_safe_manifest(self) -> None:
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, str(self.root), ""))
        manifest, exit_code = capture_project.capture_project(
            workspace_root=self.root,
            godot_executable=self.godot,
            project_path="game",
            profile="main_scene",
            run_prefix="missing-output",
            subprocess_runner=runner,
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(manifest["error_category"], "missing_capture")
        disk = self.project / ".performance-guardian/main_scene/missing-output/capture-manifest.json"
        self.assertNotIn(str(self.root), disk.read_text(encoding="utf-8"))

    def test_timeout_stops_and_sanitizes_log(self) -> None:
        runner = Mock(side_effect=subprocess.TimeoutExpired([], 300, output=str(self.root)))
        manifest, exit_code = capture_project.capture_project(
            workspace_root=self.root,
            godot_executable=self.godot,
            project_path="game",
            profile="main_scene",
            run_prefix="timeout-run",
            subprocess_runner=runner,
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(manifest["error_category"], "timeout")
        log = self.project / ".performance-guardian/main_scene/timeout-run/logs/timeout-run-01.log"
        self.assertIn("<workspace>", log.read_text(encoding="utf-8"))

    def test_invalid_configuration_is_rejected_before_launch(self) -> None:
        cases = [
            {"project_path": "../game"},
            {"profile": "bad profile"},
            {"scene_path": "C:/main.tscn"},
            {"sampling_interval": 601},
            {"runs": 0},
            {"output_base": "../results"},
            {"source_revision": "unsafe value"},
        ]
        for index, override in enumerate(cases):
            with self.subTest(override=override):
                options = {
                    "workspace_root": self.root,
                    "godot_executable": self.godot,
                    "project_path": "game",
                    "profile": "main_scene",
                    "run_prefix": f"invalid-{index}",
                }
                options.update(override)
                with self.assertRaises((capture_project.CaptureConfigurationError, ValueError)):
                    capture_project.capture_project(**options)


class ReusableWorkflowTests(unittest.TestCase):
    def test_public_contract_and_security_boundaries(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for name in (
            "project-path", "profile", "budget-file", "scene-path", "godot-version",
            "use-dotnet", "warmup-frames", "measured-frames", "sampling-interval",
            "capture-runs", "compare-with-base", "investigate", "openai-model", "openai-api-key",
        ):
            self.assertIn(name, workflow)
        self.assertIn("windows-latest", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("chickensoft-games/setup-godot@f166999204a4f2722c6fe042fbaa3b3ea0d9c789", workflow)
        self.assertIn("repository: ${{ job.workflow_repository }}", workflow)
        self.assertIn("ref: ${{ job.workflow_sha }}", workflow)
        self.assertIn("Test-Path -LiteralPath $env:GODOT -PathType Leaf", workflow)
        self.assertIn('"--godot-executable", "$env:GODOT"', workflow)
        self.assertNotIn('"--godot-executable", "godot"', workflow)
        self.assertIn("if: inputs.investigate != 'never'", workflow)
        self.assertIn("continue-on-error: true", workflow)
        self.assertIn("CAPTURE_OUTCOME: ${{ steps.capture.outcome }}", workflow)
        self.assertIn("incomplete-capture", workflow)
        stage_step = workflow.split("- name: Stage performance evidence", maxsplit=1)[1].split(
            "- name: Upload performance evidence", maxsplit=1
        )[0]
        self.assertIn("if: always()", stage_step)
        self.assertIn('$artifactRoot = Join-Path $env:RUNNER_TEMP "performance-guardian-artifact"', stage_step)
        self.assertIn('$candidateEvidence = Join-Path $projectRoot ".performance-guardian"', stage_step)
        self.assertIn('if ($env:COMPARE_WITH_BASE -eq "true")', stage_step)
        self.assertIn('$baselineEvidence = Join-Path $baseProjectRoot ".performance-guardian"', stage_step)
        self.assertIn('Join-Path $artifactRoot "candidate"', stage_step)
        self.assertIn('Join-Path $artifactRoot "baseline"', stage_step)
        self.assertIn('Join-Path $artifactRoot "reports"', stage_step)
        self.assertIn("GetFullPath", stage_step)
        self.assertNotIn(".performance-guardian-base-source/${{ inputs['project-path'] }}", stage_step)
        upload_step = workflow.split("- name: Upload performance evidence", maxsplit=1)[1]
        self.assertIn("if: always()", upload_step)
        self.assertIn("include-hidden-files: true", upload_step)
        self.assertIn("path: ${{ runner.temp }}/performance-guardian-artifact", upload_step)
        self.assertIn("retention-days: 14", upload_step)
        self.assertNotIn("${{ inputs['project-path'] }}", upload_step)
        self.assertNotIn("/./", upload_step)
        self.assertNotIn("/../", upload_step)
        self.assertNotIn(".performance-guardian-tooling", upload_step)
        self.assertNotIn("${{ github.workspace }}", upload_step)
        self.assertNotIn("OPENAI_API_KEY", upload_step)
        self.assertNotRegex(workflow, r"(?m)^  push:\s*$")
        self.assertIn(
            'description: "Optional AI mode: never, on-failure, or always."',
            workflow,
        )
        self.assertNotRegex(workflow, r"(?m)^\s+description: [^\"'].*: .*$")
        self.assertNotRegex(workflow, r"sk-[A-Za-z0-9_-]{12,}")

    def test_comparison_is_opt_in_pr_only_and_base_controlled(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(workflow, r"compare-with-base:\s+description:[\s\S]+?default: false")
        self.assertIn("github.event.pull_request.base.sha", workflow)
        self.assertIn("github.event.pull_request.head.sha", workflow)
        self.assertIn("compare-with-base requires a pull_request event", workflow)
        self.assertIn("Check out protected base revision", workflow)
        self.assertIn(".performance-guardian-base-source/$env:BUDGET_FILE", workflow)
        self.assertIn('"--baseline-results", "$baseline"', workflow)
        self.assertIn("$env:RUN_PREFIX-base", workflow)
        self.assertIn("$env:RUN_PREFIX-candidate", workflow)
        self.assertNotIn("secrets: inherit", workflow)

    def test_external_workspace_rejects_synthetic_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            results = root / "results"
            results.mkdir()
            (results / "synthetic.json").write_text(
                json.dumps({"schema_version": 1, "scenario": "healthy", "run_id": "x"}),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    capture_project.sys.executable,
                    str(ROOT / "tools/validate_results.py"),
                    "--workspace-root",
                    str(root),
                    "results",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("external workspaces support generic", completed.stderr)


if __name__ == "__main__":
    unittest.main()
