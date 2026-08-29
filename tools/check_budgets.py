#!/usr/bin/env python3
"""Evaluate configurable budgets against deterministic validator evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
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


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = (REPOSITORY_ROOT / "tools" / "validate_results.py").resolve()
VALIDATOR_TIMEOUT_SECONDS = 30.0
ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
TOP_LEVEL_FIELDS = {"schema_version", "budgets"}
COMMON_RULE_FIELDS = {"id", "metric", "maximum", "unit", "description"}
REQUIRED_RULE_FIELDS = COMMON_RULE_FIELDS | {"scenario"}
METRIC_SPECS = {
    "median_p95_workload_time": {
        "scenarios": {"healthy", "cpu_spike"},
        "unit": "usec",
        "source_type": "validated_aggregate",
    },
    "median_p95_process_time": {
        "scenarios": {"healthy", "cpu_spike"},
        "unit": "ms",
        "source_type": "validated_aggregate",
    },
    "median_scenario_duration": {
        "scenarios": {"healthy", "cpu_spike"},
        "unit": "ms",
        "source_type": "validated_aggregate",
    },
    "post_cleanup_retained_nodes": {
        "scenarios": {"healthy", "node_leak", "cpu_spike"},
        "unit": "nodes",
        "source_type": "validated_result",
    },
}
GENERIC_METRIC_SPECS = {
    "median_p95_process_time": {"unit": "ms", "source_type": "validated_aggregate"},
    "median_p95_physics_process_time": {"unit": "ms", "source_type": "validated_aggregate"},
    "median_measurement_duration": {"unit": "ms", "source_type": "validated_aggregate"},
    "median_peak_memory_static_bytes": {"unit": "bytes", "source_type": "validated_aggregate"},
    "median_peak_object_count": {"unit": "objects", "source_type": "validated_aggregate"},
    "median_peak_node_count": {"unit": "nodes", "source_type": "validated_aggregate"},
    "median_peak_orphan_node_count": {"unit": "nodes", "source_type": "validated_aggregate"},
}


class BudgetConfigurationError(ValueError):
    """The budget configuration is invalid."""


class BudgetEvidenceError(ValueError):
    """Validated evidence is unavailable or incompatible."""


@dataclass(frozen=True)
class BudgetRule:
    schema_version: int
    target_key: str
    budget_id: str
    scenario: str
    metric: str
    maximum: int | float
    unit: str
    description: str


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def parse_budget_configuration(data: Any) -> list[BudgetRule]:
    if not isinstance(data, dict):
        raise BudgetConfigurationError("top-level budget configuration must be an object")
    fields = set(data)
    if fields != TOP_LEVEL_FIELDS:
        missing = sorted(TOP_LEVEL_FIELDS - fields)
        unknown = sorted(fields - TOP_LEVEL_FIELDS)
        detail = []
        if missing:
            detail.append(f"missing fields {missing}")
        if unknown:
            detail.append(f"unknown fields {unknown}")
        raise BudgetConfigurationError("top-level configuration has " + " and ".join(detail))
    schema_version = data["schema_version"]
    if isinstance(schema_version, bool) or schema_version not in {1, 2}:
        raise BudgetConfigurationError("schema_version must be the integer 1 or 2")
    budgets = data["budgets"]
    if not isinstance(budgets, list) or not budgets:
        raise BudgetConfigurationError("budgets must be a nonempty array")

    parsed: list[BudgetRule] = []
    identifiers: set[str] = set()
    required_rule_fields = COMMON_RULE_FIELDS | ({"scenario"} if schema_version == 1 else {"profile"})
    for index, raw_rule in enumerate(budgets, 1):
        source = f"budget rule {index}"
        if not isinstance(raw_rule, dict):
            raise BudgetConfigurationError(f"{source} must be an object")
        fields = set(raw_rule)
        missing = sorted(required_rule_fields - fields)
        unknown = sorted(fields - required_rule_fields)
        if missing:
            raise BudgetConfigurationError(f"{source} is missing fields {missing}")
        if unknown:
            raise BudgetConfigurationError(f"{source} has unknown fields {unknown}")

        budget_id = raw_rule["id"]
        if not isinstance(budget_id, str) or not ID_PATTERN.fullmatch(budget_id):
            raise BudgetConfigurationError(f"{source} has an invalid id")
        if budget_id in identifiers:
            raise BudgetConfigurationError(f"duplicate budget id {budget_id!r}")
        identifiers.add(budget_id)

        target_key = "scenario" if schema_version == 1 else "profile"
        scenario = raw_rule[target_key]
        if schema_version == 1 and scenario not in {"healthy", "node_leak", "cpu_spike"}:
            raise BudgetConfigurationError(f"{source} has an unsupported scenario")
        if schema_version == 2 and (not isinstance(scenario, str) or not PROFILE_PATTERN.fullmatch(scenario)):
            raise BudgetConfigurationError(f"{source} has an unsafe or invalid profile")
        metric = raw_rule["metric"]
        metric_specs = METRIC_SPECS if schema_version == 1 else GENERIC_METRIC_SPECS
        if not isinstance(metric, str) or metric not in metric_specs:
            raise BudgetConfigurationError(f"{source} has an unsupported metric")
        specification = metric_specs[metric]
        if schema_version == 1 and scenario not in specification["scenarios"]:
            raise BudgetConfigurationError(
                f"{source} metric {metric!r} is unsupported for scenario {scenario!r}"
            )
        unit = raw_rule["unit"]
        if unit != specification["unit"]:
            raise BudgetConfigurationError(
                f"{source} metric {metric!r} requires unit {specification['unit']!r}"
            )
        maximum = raw_rule["maximum"]
        if not _is_finite_number(maximum):
            raise BudgetConfigurationError(f"{source} maximum must be a finite number")
        if maximum < 0:
            raise BudgetConfigurationError(f"{source} maximum must not be negative")

        description = raw_rule["description"]
        if (
            not isinstance(description, str)
            or not description.strip()
            or len(description) > 200
            or "\n" in description
            or "\r" in description
        ):
            raise BudgetConfigurationError(
                f"{source} description must be a short single-line string"
            )
        parsed.append(
            BudgetRule(
                schema_version=schema_version,
                target_key=target_key,
                budget_id=budget_id,
                scenario=scenario,
                metric=metric,
                maximum=maximum,
                unit=unit,
                description=description,
            )
        )
    return sorted(parsed, key=lambda rule: rule.budget_id)


def load_budget_configuration(path: Path) -> list[BudgetRule]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as error:
        raise BudgetConfigurationError("budget configuration could not be read") from error
    except json.JSONDecodeError as error:
        raise BudgetConfigurationError("budget configuration is not valid JSON") from error
    return parse_budget_configuration(data)


def run_validator_packet(
    results_directory: str,
    *,
    workspace_root: Path = REPOSITORY_ROOT,
    subprocess_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    resolved_root = workspace_root.resolve()
    command = [
        sys.executable,
        str(VALIDATOR_PATH),
        "--evidence-json",
    ]
    if resolved_root != REPOSITORY_ROOT.resolve():
        command.extend(["--workspace-root", str(resolved_root)])
    command.append(results_directory)
    try:
        completed = subprocess_runner(
            command,
            cwd=resolved_root,
            capture_output=True,
            text=True,
            timeout=VALIDATOR_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise BudgetEvidenceError("deterministic validation timed out") from error
    except OSError as error:
        raise BudgetEvidenceError("deterministic validator could not be started") from error

    try:
        packet = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError) as error:
        raise BudgetEvidenceError("validator did not return a valid evidence packet") from error
    if not isinstance(packet, dict) or packet.get("packet_type") != "godot_performance_evidence":
        raise BudgetEvidenceError("validator returned an unsupported evidence packet")
    validation = packet.get("validation")
    if not isinstance(validation, dict) or validation.get("exit_code") != completed.returncode:
        raise BudgetEvidenceError("validator evidence disagrees with its process exit status")
    if completed.returncode != 0 or validation.get("status") != "passed":
        raise BudgetEvidenceError("deterministic result validation failed")
    return packet


def _validated_packet_parts(
    packet: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]:
    if packet.get("packet_type") != "godot_performance_evidence" or (
        isinstance(packet.get("schema_version"), bool)
        or packet.get("schema_version") != 1
    ):
        raise BudgetEvidenceError("validator evidence packet schema is unsupported")
    validation = packet.get("validation")
    if (
        not isinstance(validation, dict)
        or validation.get("status") != "passed"
        or validation.get("exit_code") != 0
    ):
        raise BudgetEvidenceError("deterministic result validation did not pass")
    for key in ("candidate_file_count", "validated_file_count"):
        value = validation.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise BudgetEvidenceError("validator count metadata is invalid")
    results_directory = packet.get("results_directory")
    if (
        not isinstance(results_directory, str)
        or not results_directory
        or Path(results_directory).is_absolute()
        or ".." in Path(results_directory).parts
    ):
        raise BudgetEvidenceError("validator results-directory metadata is unsafe")

    evidence = packet.get("evidence")
    if not isinstance(evidence, list):
        raise BudgetEvidenceError("validator evidence must be an array")
    evidence_ids: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise BudgetEvidenceError("validator evidence items must be objects")
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not ID_PATTERN.fullmatch(evidence_id):
            raise BudgetEvidenceError("validator evidence contains an invalid id")
        evidence_ids.append(evidence_id)
    if len(evidence_ids) != len(set(evidence_ids)):
        raise BudgetEvidenceError("validator evidence ids are not unique")

    raw_limitations = packet.get("limitations")
    if not isinstance(raw_limitations, list):
        raise BudgetEvidenceError("validator limitations must be an array")
    limitations: list[dict[str, str]] = []
    for limitation in raw_limitations:
        if (
            not isinstance(limitation, dict)
            or set(limitation) != {"id", "statement"}
            or not isinstance(limitation["id"], str)
            or not limitation["id"]
            or not isinstance(limitation["statement"], str)
            or not limitation["statement"]
        ):
            raise BudgetEvidenceError("validator limitation metadata is invalid")
        limitations.append(
            {"id": limitation["id"], "statement": limitation["statement"]}
        )
    return validation, evidence, limitations


def _display_number(value: int | float) -> str:
    return format(value, ".12g")


def evaluate_budgets(
    rules: list[BudgetRule], packet: dict[str, Any]
) -> dict[str, Any]:
    validation, evidence, limitations = _validated_packet_parts(packet)
    results: list[dict[str, Any]] = []
    for rule in sorted(rules, key=lambda candidate: candidate.budget_id):
        specification = METRIC_SPECS[rule.metric] if rule.schema_version == 1 else GENERIC_METRIC_SPECS[rule.metric]
        matches = [
            item
            for item in evidence
            if item.get("metric") == rule.metric
            and item.get(rule.target_key) == rule.scenario
            and item.get("source_type") == specification["source_type"]
            and item.get("unit") == rule.unit
        ]
        if len(matches) != 1:
            raise BudgetEvidenceError(
                f"budget {rule.budget_id!r} has missing or ambiguous evidence"
            )
        item = matches[0]
        measured = item.get("value")
        if not _is_finite_number(measured) or measured < 0:
            raise BudgetEvidenceError(
                f"budget {rule.budget_id!r} evidence value is invalid"
            )
        passed = measured <= rule.maximum
        relation = "within" if passed else "exceeds"
        explanation = (
            f"Measured {_display_number(measured)} {rule.unit} {relation} maximum "
            f"{_display_number(rule.maximum)} {rule.unit}."
        )
        result = {
                "budget_id": rule.budget_id,
                "description": rule.description,
                "metric": rule.metric,
                "measured_value": measured,
                "maximum_value": rule.maximum,
                "unit": rule.unit,
                "evidence_id": item["id"],
                "status": "passed" if passed else "failed",
                "explanation": explanation,
            }
        result[rule.target_key] = rule.scenario
        results.append(result)

    passed_count = sum(result["status"] == "passed" for result in results)
    failed_count = len(results) - passed_count
    return {
        "schema_version": 1,
        "budget_schema_version": rules[0].schema_version,
        "status": "passed" if failed_count == 0 else "failed",
        "validator": {
            "status": "passed",
            "candidate_file_count": validation["candidate_file_count"],
            "validated_file_count": validation["validated_file_count"],
            "results_directory": packet["results_directory"],
        },
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "failed": failed_count,
        },
        "results": results,
        "limitations": limitations,
    }


def canonical_json(report: dict[str, Any]) -> str:
    return json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"


def human_report(report: dict[str, Any]) -> str:
    validator = report["validator"]
    summary = report["summary"]
    lines = [
        f"Validation: passed ({validator['validated_file_count']} files)",
        (
            f"Budgets: {report['status'].upper()} "
            f"({summary['passed']} passed, {summary['failed']} failed, "
            f"{summary['total']} total)"
        ),
    ]
    for result in report["results"]:
        label = "PASS" if result["status"] == "passed" else "FAIL"
        lines.append(
            f"{label}: {result['budget_id']} - "
            f"{result['explanation']} Evidence [{result['evidence_id']}]"
        )
    lines.append("Validator limitations:")
    for limitation in report["limitations"]:
        lines.append(f"- {limitation['id']}: {limitation['statement']}")
    return "\n".join(lines) + "\n"


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit canonical machine-readable JSON",
    )
    parser.add_argument(
        "--workspace-root",
        help="explicit workspace root for repository-relative generic captures",
    )
    parser.add_argument("results_directory", help="benchmark result directory")
    parser.add_argument("budget_file", help="versioned JSON budget configuration")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    try:
        if args.workspace_root is None:
            rules = load_budget_configuration(Path(args.budget_file))
            packet = run_validator_packet(args.results_directory)
        else:
            workspace_root = resolve_workspace_root(args.workspace_root, REPOSITORY_ROOT)
            _results_path, relative_results = resolve_workspace_member(
                workspace_root,
                args.results_directory,
                label="results directory",
                expected="directory",
            )
            budget_path, _relative_budget = resolve_workspace_member(
                workspace_root,
                args.budget_file,
                label="budget file",
                expected="file",
                require_json=True,
            )
            rules = load_budget_configuration(budget_path)
            packet = run_validator_packet(
                relative_results,
                workspace_root=workspace_root,
            )
        report = evaluate_budgets(rules, packet)
    except (WorkspacePathError, BudgetConfigurationError, BudgetEvidenceError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    output = canonical_json(report) if args.json_output else human_report(report)
    print(output, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
