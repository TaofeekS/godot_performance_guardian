#!/usr/bin/env python3
"""Generate and explicitly apply deterministic schema-v3 budget proposals."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Callable

if __package__:
    from .check_budgets import (
        BudgetConfigurationError,
        BudgetEvidenceError,
        GENERIC_METRIC_SPECS,
        ID_PATTERN,
        PROFILE_PATTERN,
        load_budget_configuration,
        run_validator_packet,
    )
    from .workspace_paths import WorkspacePathError, resolve_workspace_member, resolve_workspace_root
else:
    from check_budgets import (
        BudgetConfigurationError,
        BudgetEvidenceError,
        GENERIC_METRIC_SPECS,
        ID_PATTERN,
        PROFILE_PATTERN,
        load_budget_configuration,
        run_validator_packet,
    )
    from workspace_paths import WorkspacePathError, resolve_workspace_member, resolve_workspace_root


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MINIMUM_RUNS = 3
CALIBRATION_LIMITATIONS = (
    "Budget proposals are specific to the capture host and configuration and are not universal recommendations.",
    "Global object and node counts are engine-wide measurements and are not project-owned counts.",
    "Headless captures do not measure rendering or GPU performance.",
    "A proposal has no authority until a maintainer reviews and commits it as project policy.",
)
METRICS = {
    "median_p95_process_time": {
        "alias": "process-p95",
        "unit": "ms",
        "margin_percent": 50,
        "relative_percent": 20,
        "description": "Balanced process p95 limit calibrated from repeated captures.",
    },
    "median_peak_node_count": {
        "alias": "peak-nodes",
        "unit": "nodes",
        "margin_percent": 10,
        "relative_percent": 5,
        "description": "Balanced global peak-node limit calibrated from repeated captures.",
    },
    "median_peak_object_count": {
        "alias": "peak-objects",
        "unit": "objects",
        "margin_percent": 10,
        "relative_percent": 5,
        "description": "Balanced global peak-object limit calibrated from repeated captures.",
    },
}


class CalibrationError(ValueError):
    """Calibration configuration or validated evidence is unusable."""


def canonical_json(value: Any, *, pretty: bool = False) -> str:
    options = {"sort_keys": True, "ensure_ascii": False}
    if pretty:
        return json.dumps(value, indent=2, **options) + "\n"
    return json.dumps(value, separators=(",", ":"), **options) + "\n"


def _finite_nonnegative(value: Any, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise CalibrationError(f"{label} must be a finite nonnegative number")
    return value


def _rule_id(profile: str, alias: str) -> str:
    id_profile = profile if profile[0].isalpha() else f"profile-{profile}"
    direct = f"{id_profile}-{alias}"
    if len(direct) <= 64:
        return direct
    suffix = hashlib.sha256(profile.encode("utf-8")).hexdigest()[:8]
    available = 64 - len(alias) - len(suffix) - 2
    return f"{id_profile[:available]}-{suffix}-{alias}"


def _proposed_maximum(metric: str, observed: int | float) -> int | float:
    if metric == "median_p95_process_time":
        scaled = float(observed) * 1.5
        if not math.isfinite(scaled):
            raise CalibrationError("calibrated process threshold is not finite")
        return math.ceil((scaled - 1e-12) * 10) / 10
    scaled = float(observed) * 1.1
    if not math.isfinite(scaled):
        raise CalibrationError("calibrated count threshold is not finite")
    return math.ceil(scaled - 1e-12)


def _validate_packet(packet: Any) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]:
    if not isinstance(packet, dict) or packet.get("packet_type") != "godot_performance_evidence":
        raise CalibrationError("validator returned an unsupported evidence packet")
    if packet.get("schema_version") != 1 or packet.get("evidence_kind") != "generic":
        raise CalibrationError("calibration requires passed generic evidence")
    validation = packet.get("validation")
    if not isinstance(validation, dict) or validation.get("status") != "passed" or validation.get("exit_code") != 0:
        raise CalibrationError("deterministic result validation did not pass")
    for field in ("candidate_file_count", "validated_file_count"):
        value = validation.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < MINIMUM_RUNS:
            raise CalibrationError(f"calibration requires at least {MINIMUM_RUNS} validated captures")
    evidence = packet.get("evidence")
    if not isinstance(evidence, list) or not all(isinstance(item, dict) for item in evidence):
        raise CalibrationError("validator evidence is malformed")
    evidence_ids = [item.get("id") for item in evidence]
    if (
        any(not isinstance(value, str) or not ID_PATTERN.fullmatch(value) for value in evidence_ids)
        or len(evidence_ids) != len(set(evidence_ids))
    ):
        raise CalibrationError("validator evidence ids are invalid or duplicated")
    results_directory = packet.get("results_directory")
    if (
        not isinstance(results_directory, str)
        or not results_directory
        or Path(results_directory).is_absolute()
        or ".." in Path(results_directory).parts
    ):
        raise CalibrationError("validator results-directory metadata is unsafe")
    limitations = packet.get("limitations")
    if not isinstance(limitations, list):
        raise CalibrationError("validator limitations are malformed")
    normalized_limitations: list[dict[str, str]] = []
    for item in limitations:
        if not isinstance(item, dict) or set(item) != {"id", "statement"} or not all(isinstance(item[k], str) and item[k] for k in item):
            raise CalibrationError("validator limitation metadata is malformed")
        normalized_limitations.append({"id": item["id"], "statement": item["statement"]})
    return validation, evidence, normalized_limitations


def build_calibration(packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a schema-v3 policy and deterministic calibration report from one packet."""

    validation, evidence, validator_limitations = _validate_packet(packet)
    profiles = sorted({
        item.get("profile") for item in evidence
        if item.get("profile") != "all"
        and item.get("metric") in METRICS
        and item.get("source_type") == "validated_aggregate"
        and isinstance(item.get("profile"), str)
    })
    if not profiles:
        raise CalibrationError("no calibratable profiles were found")
    if any(not PROFILE_PATTERN.fullmatch(profile) for profile in profiles):
        raise CalibrationError("validator evidence contains an unsafe profile")

    rules: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    profile_run_counts: dict[str, int] = {}
    for profile in profiles:
        for metric, setting in METRICS.items():
            matches = [
                item for item in evidence
                if item.get("profile") == profile
                and item.get("metric") == metric
                and item.get("source_type") == GENERIC_METRIC_SPECS[metric]["source_type"]
                and item.get("unit") == setting["unit"]
            ]
            if len(matches) != 1:
                raise CalibrationError(f"profile {profile!r} has missing or ambiguous {metric!r} evidence")
            item = matches[0]
            run_count = item.get("run_count")
            if isinstance(run_count, bool) or not isinstance(run_count, int) or run_count < MINIMUM_RUNS:
                raise CalibrationError(f"profile {profile!r} has fewer than {MINIMUM_RUNS} contributing captures")
            if profile in profile_run_counts and profile_run_counts[profile] != run_count:
                raise CalibrationError(f"profile {profile!r} has inconsistent contributing run counts")
            profile_run_counts[profile] = run_count
            observed = _finite_nonnegative(item.get("value"), f"profile {profile!r} {metric!r} evidence")
            evidence_id = item.get("id")
            if not isinstance(evidence_id, str) or not evidence_id:
                raise CalibrationError("calibration evidence id is invalid")
            maximum = _proposed_maximum(metric, observed)
            rule_id = _rule_id(profile, setting["alias"])
            rule = {
                "description": setting["description"],
                "id": rule_id,
                "maximum": maximum,
                "maximum_increase_percent": setting["relative_percent"],
                "metric": metric,
                "profile": profile,
                "unit": setting["unit"],
            }
            rules.append(rule)
            recommendations.append({
                "budget_id": rule_id,
                "evidence_id": evidence_id,
                "margin_percent": setting["margin_percent"],
                "metric": metric,
                "observed_value": observed,
                "profile": profile,
                "proposed_maximum": maximum,
                "relative_allowance_percent": setting["relative_percent"],
                "run_count": run_count,
                "unit": setting["unit"],
            })
    if sum(profile_run_counts.values()) != validation["validated_file_count"]:
        raise CalibrationError("profile run counts disagree with validator totals")
    rules.sort(key=lambda item: item["id"])
    recommendations.sort(key=lambda item: item["budget_id"])
    policy = {"schema_version": 3, "budgets": rules}
    extra_limitations = [
        {"id": f"CL{index}", "statement": statement}
        for index, statement in enumerate(CALIBRATION_LIMITATIONS, 1)
    ]
    report = {
        "calibration": {
            "minimum_validated_runs": MINIMUM_RUNS,
            "preset": "balanced",
            "proposal_authoritative": False,
        },
        "limitations": validator_limitations + extra_limitations,
        "proposed_policy": policy,
        "recommendations": recommendations,
        "report_type": "performance_budget_calibration",
        "schema_version": 1,
        "status": "proposal_generated",
        "validator": {
            "candidate_file_count": validation["candidate_file_count"],
            "results_directory": packet.get("results_directory"),
            "status": "passed",
            "validated_file_count": validation["validated_file_count"],
        },
    }
    return policy, report


def _output_path(root: Path, value: str, label: str) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationError(f"{label} path is required")
    supplied = Path(value)
    if supplied.is_absolute() or supplied.drive or supplied.anchor or ".." in supplied.parts:
        raise CalibrationError(f"{label} path must be workspace-relative")
    if supplied.suffix.lower() != ".json":
        raise CalibrationError(f"{label} must use the .json extension")
    parent = (root / supplied.parent).resolve()
    try:
        parent.relative_to(root)
    except ValueError as error:
        raise CalibrationError(f"{label} path must remain inside the workspace") from error
    if parent.exists() and not parent.is_dir():
        raise CalibrationError(f"{label} parent is not a directory")
    target = parent / supplied.name
    if target.exists() and target.is_symlink():
        raise CalibrationError(f"{label} must not be a symlink")
    return target, target.relative_to(root).as_posix()


def _atomic_write_new(path: Path, content: str, *, replace: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        raise CalibrationError("output already exists; choose a new path")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise CalibrationError("temporary output collision")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            temporary.rename(path)
    except OSError as error:
        raise CalibrationError("output could not be written atomically") from error
    finally:
        if temporary.exists():
            temporary.unlink()


def generate(
    *,
    workspace_root: Path,
    results_directory: str,
    policy_output: str,
    report_output: str,
    validator_runner: Callable[..., dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _results, relative_results = resolve_workspace_member(
        workspace_root, results_directory, label="results directory", expected="directory"
    )
    policy_path, _ = _output_path(workspace_root, policy_output, "policy output")
    report_path, _ = _output_path(workspace_root, report_output, "report output")
    if policy_path == report_path:
        raise CalibrationError("policy and report outputs must be different files")
    if policy_path.exists() or report_path.exists():
        raise CalibrationError("calibration output already exists; choose new output paths")
    runner = run_validator_packet if validator_runner is None else validator_runner
    packet = runner(relative_results, workspace_root=workspace_root)
    policy, report = build_calibration(packet)
    _atomic_write_new(policy_path, canonical_json(policy, pretty=True))
    try:
        _atomic_write_new(report_path, canonical_json(report))
    except CalibrationError:
        policy_path.unlink(missing_ok=True)
        raise
    return policy, report


def apply_proposal(*, workspace_root: Path, proposal: str, budget_file: str, replace: bool) -> dict[str, Any]:
    proposal_path, _ = resolve_workspace_member(
        workspace_root, proposal, label="proposal", expected="file", require_json=True
    )
    target_path, relative_target = _output_path(workspace_root, budget_file, "budget file")
    if proposal_path == target_path:
        raise CalibrationError("a proposal cannot be applied onto itself")
    if target_path.exists() and not replace:
        raise CalibrationError("budget file exists; pass --replace to replace it explicitly")
    rules = load_budget_configuration(proposal_path)
    if not rules or any(rule.schema_version != 3 for rule in rules):
        raise CalibrationError("applied proposals must use budget schema version 3")
    try:
        raw_policy = json.loads(proposal_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CalibrationError("proposal could not be read") from error
    _atomic_write_new(target_path, canonical_json(raw_policy, pretty=True), replace=replace)
    return {"applied": True, "budget_file": relative_target, "schema_version": 3}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--policy-output")
    parser.add_argument("--report-output")
    parser.add_argument("--apply-proposal")
    parser.add_argument("--budget-file")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("results_directory", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = resolve_workspace_root(args.workspace_root, REPOSITORY_ROOT)
        if args.apply_proposal is not None:
            if args.results_directory or args.policy_output or args.report_output or not args.budget_file:
                raise CalibrationError("apply mode requires --apply-proposal and --budget-file only")
            result = apply_proposal(
                workspace_root=root,
                proposal=args.apply_proposal,
                budget_file=args.budget_file,
                replace=args.replace,
            )
            print(canonical_json(result) if args.json_output else f"Applied reviewed schema-v3 proposal to {result['budget_file']}.\n", end="")
            return 0
        if args.replace or args.budget_file or not args.results_directory or not args.policy_output or not args.report_output:
            raise CalibrationError("generation requires results, --policy-output, and --report-output")
        _policy, report = generate(
            workspace_root=root,
            results_directory=args.results_directory,
            policy_output=args.policy_output,
            report_output=args.report_output,
        )
        if args.json_output:
            print(canonical_json(report), end="")
        else:
            print("Calibration proposal generated; it is not an enforced verdict.")
            for item in report["recommendations"]:
                print(
                    f"- {item['budget_id']}: observed {item['observed_value']} {item['unit']}; "
                    f"proposed maximum {item['proposed_maximum']} {item['unit']}; "
                    f"relative allowance {item['relative_allowance_percent']}%"
                )
        return 0
    except (WorkspacePathError, BudgetConfigurationError, BudgetEvidenceError, CalibrationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
