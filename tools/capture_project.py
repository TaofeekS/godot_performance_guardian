#!/usr/bin/env python3
"""Capture isolated generic Godot performance runs for a consumer workspace."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable

if __package__:
    from .workspace_paths import (
        WorkspacePathError,
        resolve_workspace_member,
        resolve_workspace_root,
    )
else:
    from workspace_paths import (
        WorkspacePathError,
        resolve_workspace_member,
        resolve_workspace_root,
    )


DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_OUTPUT_BASE = ".performance-guardian"
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SOURCE_REVISION = re.compile(r"^[A-Za-z0-9._/-]{1,128}$")
MAIN_SCENE = re.compile(r'^run/main_scene="([^"]+)"$', re.MULTILINE)
PROBE_SCRIPT_REFERENCE = "res://addons/performance_budget_guardian/performance_probe.gd"
SCRIPT_ERROR_PATTERNS = (
    re.compile(r"(?im)^\s*SCRIPT ERROR:"),
    re.compile(r"(?im)^\s*ERROR:\s+Failed to load script\b"),
    re.compile(r"(?im)^\s*ERROR:\s+Cannot load source code from file\b"),
    re.compile(r"(?im)^\s*ERROR:\s+Failed loading resource:.*\.(?:gd|cs)\b"),
)


class CaptureConfigurationError(ValueError):
    """The consumer capture configuration is invalid."""


def _safe_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise CaptureConfigurationError(
            f"{label} must use 1-64 letters, digits, dot, underscore, or hyphen"
        )
    return value


def _bounded_integer(value: int, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise CaptureConfigurationError(
            f"{label} must be an integer from {minimum} to {maximum}"
        )
    return value


def _safe_source_revision(value: str) -> str:
    if not value:
        return ""
    if not SOURCE_REVISION.fullmatch(value) or any(
        part in {"", ".", ".."} for part in value.split("/")
    ):
        raise CaptureConfigurationError("source revision contains unsafe characters")
    return value


def _safe_output_base(value: str) -> str:
    supplied = Path(value)
    if (
        not value
        or supplied.is_absolute()
        or supplied.drive
        or supplied.anchor
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise CaptureConfigurationError("output base must be a safe project-relative path")
    return value.strip("/")


def _resource_scene(project: Path, requested: str) -> tuple[str, Path]:
    project_config = project / "project.godot"
    if requested:
        resource = requested
    else:
        text = project_config.read_text(encoding="utf-8")
        match = MAIN_SCENE.search(text)
        if match is None:
            raise CaptureConfigurationError(
                "project main scene is unavailable; provide scene-path explicitly"
            )
        resource = match.group(1)
    if not resource.startswith("res://") or "\\" in resource:
        raise CaptureConfigurationError("scene path must be a safe res:// path")
    relative = resource.removeprefix("res://")
    if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise CaptureConfigurationError("scene path must be a safe res:// path")
    scene = (project / relative).resolve()
    try:
        scene.relative_to(project)
    except ValueError as error:
        raise CaptureConfigurationError("scene path must remain inside the project") from error
    if not scene.is_file():
        raise CaptureConfigurationError("configured scene does not exist")
    scene_text = scene.read_text(encoding="utf-8")
    if PROBE_SCRIPT_REFERENCE not in scene_text:
        raise CaptureConfigurationError(
            "configured scene does not reference PerformanceBudgetProbe"
        )
    if re.search(r"(?m)^auto_start\s*=\s*false\s*$", scene_text):
        raise CaptureConfigurationError("configured probe must start automatically")
    return resource, scene


def _godot_executable(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise CaptureConfigurationError("Godot executable is required")
    candidate = Path(value)
    resolved_value = shutil.which(value) if candidate.name == value else None
    resolved = Path(resolved_value).resolve() if resolved_value else candidate.resolve()
    if not resolved.is_file():
        raise CaptureConfigurationError("Godot executable was not found")
    return resolved


def _sanitize_log(value: str | bytes | None, workspace_root: Path, executable: Path) -> str:
    if value is None:
        return ""
    text = value.decode(errors="replace") if isinstance(value, bytes) else str(value)
    replacements = {
        str(workspace_root): "<workspace>",
        str(workspace_root).replace("\\", "/"): "<workspace>",
        str(executable): "<godot>",
        str(executable).replace("\\", "/"): "<godot>",
    }
    for original, replacement in sorted(
        replacements.items(), key=lambda item: len(item[0]), reverse=True
    ):
        text = text.replace(original, replacement)
    return text


def _contains_script_error(*streams: str | bytes | None) -> bool:
    """Return whether Godot reported a script parse or load failure."""

    combined = "\n".join(
        value.decode(errors="replace") if isinstance(value, bytes) else str(value or "")
        for value in streams
    )
    return any(pattern.search(combined) for pattern in SCRIPT_ERROR_PATTERNS)


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def _write_new_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    if path.exists() or temporary.exists():
        raise CaptureConfigurationError("capture manifest already exists")
    _write_new_text(temporary, canonical_json(manifest))
    temporary.replace(path)


def _base_manifest(
    *,
    profile: str,
    project_relative: str,
    scene_path: str,
    output_relative: str,
    run_prefix: str,
    runs: int,
    warmup_frames: int,
    measured_frames: int,
    sampling_interval: int,
    source_revision: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "running",
        "profile": profile,
        "project_path": project_relative,
        "scene_path": scene_path,
        "results_directory": output_relative,
        "run_prefix": run_prefix,
        "requested_runs": runs,
        "completed_runs": 0,
        "configuration": {
            "warmup_frames": warmup_frames,
            "measured_frames": measured_frames,
            "sampling_interval": sampling_interval,
            "source_revision_supplied": bool(source_revision),
        },
        "captures": [],
        "logs": [],
        "error_category": None,
    }


def capture_project(
    *,
    workspace_root: Path,
    godot_executable: Path,
    project_path: str,
    profile: str,
    scene_path: str = "",
    output_base: str = DEFAULT_OUTPUT_BASE,
    run_prefix: str,
    runs: int = 3,
    warmup_frames: int = 120,
    measured_frames: int = 600,
    sampling_interval: int = 1,
    source_revision: str = "",
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    subprocess_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[dict[str, Any], int]:
    """Run isolated captures and return a safe manifest plus process exit code."""

    root = resolve_workspace_root(workspace_root, workspace_root)
    project, project_relative = resolve_workspace_member(
        root,
        project_path,
        label="project path",
        expected="directory",
    )
    if not (project / "project.godot").is_file():
        raise CaptureConfigurationError("project path does not contain project.godot")
    addon = project / "addons/performance_budget_guardian/performance_probe.gd"
    if not addon.is_file():
        raise CaptureConfigurationError("consumer project does not contain the committed addon")

    profile = _safe_identifier(profile, "profile")
    run_prefix = _safe_identifier(run_prefix, "run prefix")
    runs = _bounded_integer(runs, "capture runs", 1, 100)
    warmup_frames = _bounded_integer(warmup_frames, "warmup frames", 0, 1_000_000)
    measured_frames = _bounded_integer(measured_frames, "measured frames", 1, 1_000_000)
    sampling_interval = _bounded_integer(
        sampling_interval, "sampling interval", 1, 1_000_000
    )
    if sampling_interval > measured_frames:
        raise CaptureConfigurationError("sampling interval cannot exceed measured frames")
    if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
        raise CaptureConfigurationError("capture timeout must be numeric")
    if timeout_seconds <= 0 or timeout_seconds > 3600:
        raise CaptureConfigurationError("capture timeout must be from 1 to 3600 seconds")
    source_revision = _safe_source_revision(source_revision)
    output_base = _safe_output_base(output_base)
    selected_scene, _scene = _resource_scene(project, scene_path)

    run_ids = [f"{run_prefix}-{index:02d}" for index in range(1, runs + 1)]
    if any(not IDENTIFIER.fullmatch(run_id) for run_id in run_ids):
        raise CaptureConfigurationError("generated run ID exceeds the safe identifier contract")

    relative_run_root = f"{output_base}/{profile}/{run_prefix}"
    relative_capture_directory = f"{relative_run_root}/captures"
    run_root = (project / relative_run_root).resolve()
    try:
        run_root.relative_to(project)
    except ValueError as error:
        raise CaptureConfigurationError("capture output must remain inside the project") from error
    if run_root.exists():
        raise CaptureConfigurationError("capture output already exists; use a new run prefix")

    captures = run_root / "captures"
    logs = run_root / "logs"
    captures.mkdir(parents=True)
    logs.mkdir()
    output_relative = captures.relative_to(root).as_posix()
    manifest_path = run_root / "capture-manifest.json"
    manifest = _base_manifest(
        profile=profile,
        project_relative=project_relative,
        scene_path=selected_scene,
        output_relative=output_relative,
        run_prefix=run_prefix,
        runs=runs,
        warmup_frames=warmup_frames,
        measured_frames=measured_frames,
        sampling_interval=sampling_interval,
        source_revision=source_revision,
    )

    for run_id in run_ids:
        log_path = logs / f"{run_id}.log"
        command = [
            str(godot_executable),
            "--headless",
            "--path",
            str(project),
            "--scene",
            selected_scene,
            "--",
            f"--pbg-profile={profile}",
            f"--pbg-warmup-frames={warmup_frames}",
            f"--pbg-measured-frames={measured_frames}",
            f"--pbg-sampling-interval={sampling_interval}",
            f"--pbg-output=res://{relative_capture_directory}",
            f"--pbg-run-id={run_id}",
            "--pbg-auto-quit",
        ]
        if source_revision:
            command.insert(-1, f"--pbg-source-revision={source_revision}")
        try:
            completed = subprocess_runner(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=float(timeout_seconds),
                check=False,
            )
            log_text = _sanitize_log(completed.stdout, root, godot_executable)
            error_text = _sanitize_log(completed.stderr, root, godot_executable)
            _write_new_text(log_path, log_text + error_text)
        except subprocess.TimeoutExpired as error:
            _write_new_text(
                log_path,
                _sanitize_log(error.stdout, root, godot_executable)
                + _sanitize_log(error.stderr, root, godot_executable),
            )
            manifest["status"] = "failed"
            manifest["error_category"] = "timeout"
            manifest["logs"].append(log_path.relative_to(root).as_posix())
            _write_manifest(manifest_path, manifest)
            return manifest, 2
        except OSError:
            manifest["status"] = "failed"
            manifest["error_category"] = "launch_error"
            _write_manifest(manifest_path, manifest)
            return manifest, 2

        manifest["logs"].append(log_path.relative_to(root).as_posix())
        result_path = captures / f"{run_id}.json"
        if _contains_script_error(completed.stdout, completed.stderr):
            manifest["status"] = "failed"
            manifest["error_category"] = "godot_script_error"
            _write_manifest(manifest_path, manifest)
            return manifest, 2
        if completed.returncode != 0:
            manifest["status"] = "failed"
            manifest["error_category"] = "godot_exit"
            _write_manifest(manifest_path, manifest)
            return manifest, 2
        if not result_path.is_file():
            manifest["status"] = "failed"
            manifest["error_category"] = "missing_capture"
            _write_manifest(manifest_path, manifest)
            return manifest, 2
        if any(captures.glob("*.tmp.*")):
            manifest["status"] = "failed"
            manifest["error_category"] = "temporary_output"
            _write_manifest(manifest_path, manifest)
            return manifest, 2
        manifest["captures"].append(result_path.relative_to(root).as_posix())
        manifest["completed_runs"] += 1

    manifest["status"] = "passed"
    _write_manifest(manifest_path, manifest)
    return manifest, 0


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--godot-executable", required=True)
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--scene-path", default="")
    parser.add_argument("--output-base", default=DEFAULT_OUTPUT_BASE)
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmup-frames", type=int, default=120)
    parser.add_argument("--measured-frames", type=int, default=600)
    parser.add_argument("--sampling-interval", type=int, default=1)
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    try:
        root = resolve_workspace_root(args.workspace_root, Path.cwd())
        executable = _godot_executable(args.godot_executable)
        manifest, exit_code = capture_project(
            workspace_root=root,
            godot_executable=executable,
            project_path=args.project_path,
            profile=args.profile,
            scene_path=args.scene_path,
            output_base=args.output_base,
            run_prefix=args.run_prefix,
            runs=args.runs,
            warmup_frames=args.warmup_frames,
            measured_frames=args.measured_frames,
            sampling_interval=args.sampling_interval,
            source_revision=args.source_revision,
            timeout_seconds=args.timeout_seconds,
        )
    except (WorkspacePathError, CaptureConfigurationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(canonical_json(manifest), end="")
    if exit_code != 0:
        print(
            f"ERROR: performance capture failed safely ({manifest['error_category']})",
            file=sys.stderr,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
