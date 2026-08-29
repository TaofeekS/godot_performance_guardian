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
RELATIVE_RULE_FIELD = "maximum_increase_percent"
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
    maximum_increase_percent: int | float | None
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
    if isinstance(schema_version, bool) or schema_version not in {1, 2, 3}:
        raise BudgetConfigurationError("schema_version must be the integer 1, 2, or 3")
    budgets = data["budgets"]
    if not isinstance(budgets, list) or not budgets:
        raise BudgetConfigurationError("budgets must be a nonempty array")

    parsed: list[BudgetRule] = []
    identifiers: set[str] = set()
    required_rule_fields = COMMON_RULE_FIELDS | ({"scenario"} if schema_version == 1 else {"profile"})
    if schema_version == 3:
        required_rule_fields.add(RELATIVE_RULE_FIELD)
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
        if schema_version in {2, 3} and (not isinstance(scenario, str) or not PROFILE_PATTERN.fullmatch(scenario)):
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
        maximum_increase_percent = raw_rule.get(RELATIVE_RULE_FIELD)
        if schema_version == 3:
            if not _is_finite_number(maximum_increase_percent):
                raise BudgetConfigurationError(
                    f"{source} maximum_increase_percent must be a finite number"
                )
            if maximum_increase_percent < 0:
                raise BudgetConfigurationError(
                    f"{source} maximum_increase_percent must not be negative"
                )
        else:
            maximum_increase_percent = None

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
                maximum_increase_percent=maximum_increase_percent,
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


def evaluate_comparison_budgets(
    rules: list[BudgetRule],
    baseline_packet: dict[str, Any],
    candidate_packet: dict[str, Any],
) -> dict[str, Any]:
    """Compare two independently validated generic result packets under v3 rules."""

    if not rules or any(rule.schema_version != 3 for rule in rules):
        raise BudgetConfigurationError("baseline comparison requires budget schema version 3")
    baseline_validation, baseline_evidence, baseline_limitations = _validated_packet_parts(
        baseline_packet
    )
    candidate_validation, candidate_evidence, candidate_limitations = _validated_packet_parts(
        candidate_packet
    )
    if baseline_packet.get("evidence_kind") != "generic" or candidate_packet.get("evidence_kind") != "generic":
        raise BudgetEvidenceError("baseline comparison requires generic capture evidence")

    results: list[dict[str, Any]] = []
    for rule in sorted(rules, key=lambda candidate: candidate.budget_id):
        specification = GENERIC_METRIC_SPECS[rule.metric]

        def match(evidence: list[dict[str, Any]], side: str) -> dict[str, Any]:
            matches = [
                item for item in evidence
                if item.get("metric") == rule.metric
                and item.get("profile") == rule.scenario
                and item.get("source_type") == specification["source_type"]
                and item.get("unit") == rule.unit
            ]
            if len(matches) != 1:
                raise BudgetEvidenceError(
                    f"budget {rule.budget_id!r} has missing or ambiguous {side} evidence"
                )
            value = matches[0].get("value")
            if not _is_finite_number(value) or value < 0:
                raise BudgetEvidenceError(
                    f"budget {rule.budget_id!r} {side} evidence value is invalid"
                )
            return matches[0]

        baseline_item = match(baseline_evidence, "baseline")
        candidate_item = match(candidate_evidence, "candidate")
        baseline_value = baseline_item["value"]
        candidate_value = candidate_item["value"]
        delta = round(candidate_value - baseline_value, 12)
        if baseline_value == 0:
            increase_percent: float | int | None = 0 if candidate_value == 0 else None
        else:
            increase_percent = round((delta / baseline_value) * 100.0, 12)
        absolute_passed = candidate_value <= rule.maximum
        relative_passed = (
            increase_percent is not None
            and increase_percent <= rule.maximum_increase_percent
        )
        results.append({
            "budget_id": rule.budget_id,
            "description": rule.description,
            "profile": rule.scenario,
            "metric": rule.metric,
            "unit": rule.unit,
            "baseline_value": baseline_value,
            "candidate_value": candidate_value,
            "delta": delta,
            "increase_percent": increase_percent,
            "baseline_evidence_id": baseline_item["id"],
            "candidate_evidence_id": candidate_item["id"],
            "absolute": {
                "maximum": rule.maximum,
                "status": "passed" if absolute_passed else "failed",
            },
            "relative": {
                "maximum_increase_percent": rule.maximum_increase_percent,
                "status": "passed" if relative_passed else "failed",
            },
            "status": "passed" if absolute_passed and relative_passed else "failed",
        })

    passed_count = sum(item["status"] == "passed" for item in results)
    limitations: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in baseline_limitations + candidate_limitations + [{
        "id": "CL1",
        "statement": (
            "Sequential captures on one runner reduce host variation but do not prove "
            "identical thermal, scheduling, or system-load conditions."
        ),
    }]:
        key = (item["id"], item["statement"])
        if key not in seen:
            limitations.append(item)
            seen.add(key)
    return {
        "status": "passed" if passed_count == len(results) else "failed",
        "baseline_validator": {
            "status": "passed",
            "candidate_file_count": baseline_validation["candidate_file_count"],
            "validated_file_count": baseline_validation["validated_file_count"],
            "results_directory": baseline_packet["results_directory"],
        },
        "candidate_validator": {
            "status": "passed",
            "candidate_file_count": candidate_validation["candidate_file_count"],
            "validated_file_count": candidate_validation["validated_file_count"],
            "results_directory": candidate_packet["results_directory"],
        },
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
        },
        "results": results,
        "limitations": limitations,
    }


def comparison_budget_report(
    rules: list[BudgetRule],
    candidate_packet: dict[str, Any],
    baseline_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return schema-v2 policy output for v3 absolute or paired evaluation."""

    absolute = evaluate_budgets(rules, candidate_packet)
    comparison = (
        {"status": "not_requested", "summary": {}, "results": [], "limitations": []}
        if baseline_packet is None
        else evaluate_comparison_budgets(rules, baseline_packet, candidate_packet)
    )
    failed = absolute["status"] == "failed" or comparison["status"] == "failed"
    return {
        "schema_version": 2,
        "budget_schema_version": 3,
        "status": "failed" if failed else "passed",
        "validator": absolute["validator"],
        "absolute": {
            "status": absolute["status"],
            "summary": absolute["summary"],
            "results": absolute["results"],
            "limitations": absolute["limitations"],
        },
        "comparison": comparison,
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


def human_comparison_report(report: dict[str, Any]) -> str:
    absolute = report["absolute"]
    comparison = report["comparison"]
    lines = [
        f"Validation: passed ({report['validator']['validated_file_count']} candidate files)",
        f"Absolute budgets: {absolute['status'].upper()}",
        f"Comparison: {comparison['status'].upper()}",
    ]
    for result in absolute["results"]:
        lines.append(
            f"{'PASS' if result['status'] == 'passed' else 'FAIL'} absolute: "
            f"{result['budget_id']} - {result['explanation']} "
            f"Evidence [{result['evidence_id']}]"
        )
    for result in comparison["results"]:
        percent = (
            "undefined from zero baseline"
            if result["increase_percent"] is None
            else f"{_display_number(result['increase_percent'])}%"
        )
        lines.append(
            f"{'PASS' if result['status'] == 'passed' else 'FAIL'} comparison: "
            f"{result['budget_id']} - baseline {_display_number(result['baseline_value'])} "
            f"{result['unit']}, candidate {_display_number(result['candidate_value'])} "
            f"{result['unit']}, increase {percent}; evidence "
            f"[{result['baseline_evidence_id']}] and [{result['candidate_evidence_id']}]."
        )
    limitations = comparison["limitations"] or absolute["limitations"]
    lines.append("Validator limitations:")
    for limitation in limitations:
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
    parser.add_argument(
        "--baseline-results",
        help="optional repository-relative baseline results directory; requires schema v3",
    )
    parser.add_argument("results_directory", help="benchmark result directory")
    parser.add_argument("budget_file", help="versioned JSON budget configuration")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    try:
        if args.workspace_root is None:
            rules = load_budget_configuration(Path(args.budget_file))
            if args.baseline_results is not None and rules[0].schema_version != 3:
                raise BudgetConfigurationError(
                    "--baseline-results requires budget schema version 3"
                )
            baseline_packet = (
                run_validator_packet(args.baseline_results)
                if args.baseline_results is not None
                else None
            )
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
            if args.baseline_results is not None and rules[0].schema_version != 3:
                raise BudgetConfigurationError(
                    "--baseline-results requires budget schema version 3"
                )
            baseline_packet = None
            if args.baseline_results is not None:
                _baseline_path, relative_baseline = resolve_workspace_member(
                    workspace_root,
                    args.baseline_results,
                    label="baseline results directory",
                    expected="directory",
                )
                baseline_packet = run_validator_packet(
                    relative_baseline,
                    workspace_root=workspace_root,
                )
            packet = run_validator_packet(
                relative_results,
                workspace_root=workspace_root,
            )
        report = (
            comparison_budget_report(rules, packet, baseline_packet)
            if rules[0].schema_version == 3
            else evaluate_budgets(rules, packet)
        )
    except (WorkspacePathError, BudgetConfigurationError, BudgetEvidenceError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if report.get("schema_version") == 2:
        output = canonical_json(report) if args.json_output else human_comparison_report(report)
    else:
        output = canonical_json(report) if args.json_output else human_report(report)
    print(output, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
