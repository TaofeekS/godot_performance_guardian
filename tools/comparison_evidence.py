#!/usr/bin/env python3
"""Build deterministic schema-v2 evidence for baseline/candidate comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from . import check_budgets
    from .workspace_paths import resolve_workspace_member, resolve_workspace_root, WorkspacePathError
else:
    import check_budgets
    from workspace_paths import resolve_workspace_member, resolve_workspace_root, WorkspacePathError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def build_packet(
    rules: list[check_budgets.BudgetRule],
    baseline_packet: dict[str, Any],
    candidate_packet: dict[str, Any],
) -> dict[str, Any]:
    comparison = check_budgets.evaluate_comparison_budgets(
        rules, baseline_packet, candidate_packet
    )
    evidence: list[dict[str, Any]] = []
    for index, result in enumerate(comparison["results"], 1):
        evidence.append({
            "id": f"C{index}",
            "claim": (
                f"Budget {result['budget_id']} compares validated baseline and candidate "
                f"aggregates under absolute and relative policy limits."
            ),
            "profile": result["profile"],
            "metric": result["metric"],
            "unit": result["unit"],
            "source_type": "validated_comparison",
            "value": {
                "baseline": result["baseline_value"],
                "candidate": result["candidate_value"],
                "delta": result["delta"],
                "increase_percent": result["increase_percent"],
                "maximum": result["absolute"]["maximum"],
                "maximum_increase_percent": result["relative"]["maximum_increase_percent"],
                "absolute_status": result["absolute"]["status"],
                "relative_status": result["relative"]["status"],
                "status": result["status"],
            },
            "baseline_evidence_id": result["baseline_evidence_id"],
            "candidate_evidence_id": result["candidate_evidence_id"],
            "source": candidate_packet["results_directory"],
            "baseline_source": baseline_packet["results_directory"],
        })
    limitations = list(comparison["limitations"])
    return {
        "packet_type": "godot_performance_evidence",
        "schema_version": 2,
        "evidence_kind": "comparison",
        "validation": {
            "status": "passed",
            "exit_code": 0,
            "candidate_file_count": comparison["candidate_validator"]["candidate_file_count"],
            "validated_file_count": comparison["candidate_validator"]["validated_file_count"],
            "baseline_file_count": comparison["baseline_validator"]["validated_file_count"],
            "policy_status": comparison["status"],
            "errors": [],
            "timed_out": False,
            "error_type": None,
        },
        "results_directory": candidate_packet["results_directory"],
        "baseline_results_directory": baseline_packet["results_directory"],
        "evidence": evidence,
        "limitations": limitations,
        "errors": [],
        "timeout": False,
        "error_category": None,
    }


def generate_packet(
    baseline_results: str,
    candidate_results: str,
    budget_file: str,
    *,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    root = resolve_workspace_root(workspace_root, REPOSITORY_ROOT)
    _base_path, base_relative = resolve_workspace_member(
        root, baseline_results, label="baseline results directory", expected="directory"
    )
    _candidate_path, candidate_relative = resolve_workspace_member(
        root, candidate_results, label="candidate results directory", expected="directory"
    )
    policy_path, _policy_relative = resolve_workspace_member(
        root, budget_file, label="budget file", expected="file", require_json=True
    )
    rules = check_budgets.load_budget_configuration(policy_path)
    if not rules or rules[0].schema_version != 3:
        raise check_budgets.BudgetConfigurationError(
            "comparison evidence requires budget schema version 3"
        )
    baseline_packet = check_budgets.run_validator_packet(base_relative, workspace_root=root)
    candidate_packet = check_budgets.run_validator_packet(candidate_relative, workspace_root=root)
    return build_packet(rules, baseline_packet, candidate_packet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root")
    parser.add_argument("baseline_results")
    parser.add_argument("candidate_results")
    parser.add_argument("budget_file")
    args = parser.parse_args(argv)
    try:
        packet = generate_packet(
            args.baseline_results,
            args.candidate_results,
            args.budget_file,
            workspace_root=args.workspace_root,
        )
    except (WorkspacePathError, check_budgets.BudgetConfigurationError, check_budgets.BudgetEvidenceError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(packet, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
