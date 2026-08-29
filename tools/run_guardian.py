#!/usr/bin/env python3
"""Run deterministic performance validation, budgets, and optional investigation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Mapping

if __package__:
    from . import check_budgets
    from .workspace_paths import (
        WorkspacePathError,
        resolve_workspace_member,
        resolve_workspace_root,
    )
else:  # Direct execution places this file's directory on sys.path.
    import check_budgets
    from workspace_paths import (
        WorkspacePathError,
        resolve_workspace_member,
        resolve_workspace_root,
    )


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INVESTIGATOR_PATH = (REPOSITORY_ROOT / "agent" / "investigator.py").resolve()
INVESTIGATOR_TIMEOUT_SECONDS = 120.0
INVESTIGATION_MODES = ("never", "on-failure", "always")
INVESTIGATION_OUTCOMES = {
    "not_requested",
    "not_needed",
    "skipped_no_key",
    "accepted",
    "fallback",
    "api_error",
}
MODEL_REPORT_SOURCE_DISCLOSURE = (
    "Report source: Locally rendered from validated evidence and accepted "
    "model-authored investigation items."
)
FALLBACK_REPORT_SOURCE_DISCLOSURE = (
    "Report source: Deterministic fallback generated after model output failed "
    "grounding."
)
SAFE_RULE_ID = re.compile(r"\b(?:C|G)\d{2}_[A-Z][A-Z0-9_]*\b")
SAFE_ERROR_TYPE = re.compile(r"investigator run failed \(([A-Za-z][A-Za-z0-9]{0,63}Error)\)")
SENSITIVE_OUTPUT = re.compile(
    r"(?i)(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|bearer\s+[A-Za-z0-9._-]+|"
    r"OPENAI_API_KEY\s*=|(?:^|[\s(\"'])\b[A-Z]:[\\/]|"
    r"(?:^|\s)\\\\[^\s]+|/(?:users|home)/[^\s]+)"
)
REPORT_HEADINGS = (
    "## Validation status",
    "## Verified facts",
    "## Possible explanations",
    "## Recommended next investigation",
    "## Remaining uncertainty",
)


class GuardianConfigurationError(ValueError):
    """A repository-contained runner input is invalid."""


def resolve_repository_input(
    value: str,
    *,
    kind: str,
    workspace_root: Path = REPOSITORY_ROOT,
) -> tuple[Path, str]:
    """Resolve one input inside the repository without exposing absolute paths."""

    try:
        resolved, relative = resolve_workspace_member(
            workspace_root,
            value,
            label=kind,
            expected="directory" if kind == "results directory" else "file",
            require_json=kind == "budget file",
        )
    except WorkspacePathError as error:
        raise GuardianConfigurationError(str(error)) from error

    if kind == "results directory":
        if not any(path.is_file() for path in resolved.glob("*.json")):
            raise GuardianConfigurationError("results directory contains no JSON files")
    elif kind == "budget file":
        pass
    else:
        raise GuardianConfigurationError("unsupported input kind")
    return resolved, relative


def _empty_investigation(mode: str, outcome: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "requested": mode != "never",
        "api_request_attempted": False,
        "outcome": outcome,
        "rule_ids": [],
        "error_category": None,
        "report": None,
    }


def _error_report(mode: str, reason: str, *, configuration_error: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "deterministic_status": "error",
        "validator": {
            "status": "not_run" if configuration_error else "failed",
            "candidate_file_count": 0,
            "validated_file_count": 0,
            "results_directory": None,
        },
        "budget": {
            "status": "error" if configuration_error else "not_evaluated",
            "summary": {},
            "results": [],
            "limitations": [],
        },
        "investigation": _empty_investigation(mode, "not_needed"),
        "authoritative_exit_code": 2,
        "authoritative_exit_reason": reason,
    }


def run_deterministic_pipeline(
    results_directory: str,
    budget_file: str,
    *,
    mode: str,
    workspace_root: str | Path | None = None,
    validator_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Run configuration, validator, then existing budget evaluation in order."""

    try:
        resolved_root = resolve_workspace_root(workspace_root, REPOSITORY_ROOT)
        _results_path, relative_results = resolve_repository_input(
            results_directory,
            kind="results directory",
            workspace_root=resolved_root,
        )
        budget_path, _relative_budget = resolve_repository_input(
            budget_file,
            kind="budget file",
            workspace_root=resolved_root,
        )
        rules = check_budgets.load_budget_configuration(budget_path)
    except (
        WorkspacePathError,
        GuardianConfigurationError,
        check_budgets.BudgetConfigurationError,
    ) as error:
        return _error_report(mode, str(error), configuration_error=True)

    try:
        packet = check_budgets.run_validator_packet(
            relative_results,
            workspace_root=resolved_root,
            subprocess_runner=validator_runner,
        )
        budget_report = check_budgets.evaluate_budgets(rules, packet)
    except check_budgets.BudgetEvidenceError as error:
        return _error_report(mode, str(error), configuration_error=False)

    failed = budget_report["status"] == "failed"
    exit_code = 1 if failed else 0
    investigation_outcome = (
        "not_requested"
        if mode == "never"
        else "not_needed"
        if mode == "on-failure" and not failed
        else "not_needed"
    )
    return {
        "schema_version": 1,
        "deterministic_status": "budget_failed" if failed else "passed",
        "validator": dict(budget_report["validator"]),
        "budget": {
            "status": budget_report["status"],
            "summary": dict(budget_report["summary"]),
            "results": list(budget_report["results"]),
            "limitations": list(budget_report["limitations"]),
        },
        "investigation": _empty_investigation(mode, investigation_outcome),
        "authoritative_exit_code": exit_code,
        "authoritative_exit_reason": (
            "Validation passed and every configured budget passed."
            if exit_code == 0
            else "Validation passed, but one or more configured budgets failed."
        ),
    }


def _safe_report(value: str, disclosure: str) -> str | None:
    report = value.strip()
    if not report or disclosure not in report or SENSITIVE_OUTPUT.search(report):
        return None
    positions = [report.find(heading) for heading in REPORT_HEADINGS]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        return None
    if len(re.findall(r"^## .+$", report, flags=re.MULTILINE)) != len(REPORT_HEADINGS):
        return None
    return report + "\n"


def _camel_error_category(value: str) -> str:
    stem = value.removesuffix("Error")
    category = re.sub(r"(?<!^)(?=[A-Z])", "_", stem).lower()
    if category in {"authentication", "permission_denied", "not_found", "bad_request"}:
        return "model_access_error" if category != "authentication" else "authentication_error"
    return "investigator_error"


def _api_error_category(stderr: str) -> str:
    lowered = stderr.lower()
    if "insufficient_quota" in lowered or "no available quota" in lowered:
        return "insufficient_quota"
    if "openai api rate limit" in lowered or "http 429" in lowered:
        return "rate_limit"
    match = SAFE_ERROR_TYPE.search(stderr)
    if match:
        return _camel_error_category(match.group(1))
    if "g00_evidence_packet" in lowered or "g15_evidence_schema" in lowered:
        return "grounding_error"
    return "investigator_error"


def _investigation_needed(report: dict[str, Any]) -> bool:
    mode = report["investigation"]["mode"]
    return mode == "always" or (
        mode == "on-failure" and report["authoritative_exit_code"] == 1
    )


def run_optional_investigation(
    report: dict[str, Any],
    *,
    workspace_root: Path = REPOSITORY_ROOT,
    environment: Mapping[str, str] = os.environ,
    subprocess_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    """Mutate only the optional investigation portion of a deterministic report."""

    if report["authoritative_exit_code"] == 2 or not _investigation_needed(report):
        return
    if not environment.get("OPENAI_API_KEY"):
        report["investigation"] = _empty_investigation(
            report["investigation"]["mode"], "skipped_no_key"
        )
        print(
            "WARNING: optional AI investigation was skipped because OPENAI_API_KEY is not configured.",
            file=sys.stderr,
        )
        return

    command = [
        sys.executable,
        str(INVESTIGATOR_PATH),
    ]
    if workspace_root.resolve() != REPOSITORY_ROOT.resolve():
        command.extend(["--workspace-root", str(workspace_root.resolve())])
    command.append(report["validator"]["results_directory"])
    investigation = _empty_investigation(report["investigation"]["mode"], "api_error")
    investigation["api_request_attempted"] = True
    try:
        completed = subprocess_runner(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=INVESTIGATOR_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        investigation["error_category"] = "timeout"
        report["investigation"] = investigation
        print("WARNING: optional AI investigation timed out.", file=sys.stderr)
        return
    except OSError:
        investigation["api_request_attempted"] = False
        investigation["error_category"] = "os_error"
        report["investigation"] = investigation
        print("WARNING: optional AI investigator could not be started.", file=sys.stderr)
        return

    stderr = completed.stderr if isinstance(completed.stderr, str) else ""
    stdout = completed.stdout if isinstance(completed.stdout, str) else ""
    investigation["rule_ids"] = sorted(set(SAFE_RULE_ID.findall(stderr)))
    if completed.returncode == 0:
        accepted = _safe_report(stdout, MODEL_REPORT_SOURCE_DISCLOSURE)
        fallback = _safe_report(stdout, FALLBACK_REPORT_SOURCE_DISCLOSURE)
        if (accepted is None) == (fallback is None):
            investigation["error_category"] = "invalid_investigator_output"
        elif accepted is not None:
            investigation["outcome"] = "accepted"
            investigation["report"] = accepted
        else:
            investigation["outcome"] = "fallback"
            investigation["report"] = fallback
    else:
        investigation["error_category"] = _api_error_category(stderr)
    report["investigation"] = investigation
    if investigation["outcome"] == "api_error":
        print(
            "WARNING: optional AI investigation failed safely "
            f"({investigation['error_category']}).",
            file=sys.stderr,
        )


def canonical_json(report: dict[str, Any]) -> str:
    return json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"


def human_report(report: dict[str, Any]) -> str:
    validator = report["validator"]
    budget = report["budget"]
    investigation = report["investigation"]
    lines = ["Validation result"]
    if validator["status"] == "passed":
        lines.append(
            f"PASS: {validator['validated_file_count']} validated files from "
            f"{validator['results_directory']}."
        )
    else:
        lines.append(f"{validator['status'].upper()}: deterministic validation did not pass.")

    lines.extend(["", "Budget result"])
    if budget["status"] in {"passed", "failed"}:
        summary = budget["summary"]
        lines.append(
            f"{budget['status'].upper()}: {summary['passed']} passed, "
            f"{summary['failed']} failed, {summary['total']} total."
        )
        for result in budget["results"]:
            lines.append(
                f"- {result['budget_id']}: {result['status']} "
                f"[{result['evidence_id']}]"
            )
    else:
        lines.append(f"{budget['status'].upper()}: budgets were not authoritatively evaluated.")

    lines.extend(["", "Optional investigator explanation"])
    outcome = investigation["outcome"]
    if investigation["report"] is not None:
        lines.append(investigation["report"].rstrip())
    elif outcome == "api_error":
        lines.append(f"AI investigation failed safely ({investigation['error_category']}).")
    else:
        lines.append(f"AI investigation outcome: {outcome}.")

    lines.extend(
        [
            "",
            "Final authoritative exit reason",
            f"Exit {report['authoritative_exit_code']}: "
            f"{report['authoritative_exit_reason']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--investigate",
        choices=INVESTIGATION_MODES,
        default="never",
    )
    parser.add_argument(
        "--workspace-root",
        help="explicit workspace root for repository-relative generic captures",
    )
    parser.add_argument("results_directory")
    parser.add_argument("budget_file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    report = run_deterministic_pipeline(
        args.results_directory,
        args.budget_file,
        mode=args.investigate,
        workspace_root=args.workspace_root,
    )
    try:
        workspace_root = resolve_workspace_root(args.workspace_root, REPOSITORY_ROOT)
    except WorkspacePathError:
        workspace_root = REPOSITORY_ROOT
    if workspace_root.resolve() == REPOSITORY_ROOT.resolve():
        run_optional_investigation(report)
    else:
        run_optional_investigation(report, workspace_root=workspace_root)
    output = canonical_json(report) if args.json_output else human_report(report)
    print(output, end="")
    return report["authoritative_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
