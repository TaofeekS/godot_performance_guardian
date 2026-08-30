#!/usr/bin/env python3
"""Render a canonical Guardian report for GitHub Actions without changing its verdict."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


REPORT_SCHEMAS = {1, 2}
REPORT_STATUSES = {"passed", "budget_failed", "error"}
VALIDATOR_STATUSES = {"not_run", "passed", "failed", "error"}
BUDGET_STATUSES = {"not_evaluated", "passed", "failed", "error"}
INVESTIGATION_OUTCOMES = {
    "not_requested", "not_needed", "skipped_no_key", "accepted", "fallback", "api_error"
}
MODEL_DISCLOSURE = (
    "Report source: Locally rendered from validated evidence and accepted "
    "model-authored investigation items."
)
FALLBACK_DISCLOSURE = (
    "Report source: Deterministic fallback generated after model output failed grounding."
)
SENSITIVE_TEXT = re.compile(
    r"(?i)(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|bearer\s+[A-Za-z0-9._-]+|"
    r"OPENAI_API_KEY\s*=|(?:^|[\s(\"'])\b[A-Z]:[\\/]|"
    r"(?:^|\s)\\\\[^\s]+|/(?:users|home)/[^\s]+|"
    r"(?:source[ _-]?revision|revision[ _-]?value)\s*[:=])"
)


class ActionReportError(ValueError):
    """The canonical report cannot be presented safely."""


CALIBRATION_REPORT_TYPE = "performance_budget_calibration"


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ActionReportError(f"{label} is malformed")
    return value


def _finite_number(value: Any, label: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActionReportError(f"{label} is invalid")
    if not math.isfinite(float(value)):
        raise ActionReportError(f"{label} is invalid")


def _validate_absolute_result(value: Any) -> None:
    result = _mapping(value, "budget result")
    for field in ("budget_id", "metric", "unit", "evidence_id"):
        if not isinstance(result.get(field), str) or not result[field]:
            raise ActionReportError(f"budget result {field} is invalid")
    if result.get("status") not in {"passed", "failed"}:
        raise ActionReportError("budget result status is invalid")
    _finite_number(result.get("measured_value"), "budget measured value")
    _finite_number(result.get("maximum_value"), "budget maximum value")


def _validate_comparison_result(value: Any) -> None:
    result = _mapping(value, "comparison result")
    for field in ("budget_id", "metric", "unit", "baseline_evidence_id", "candidate_evidence_id"):
        if not isinstance(result.get(field), str) or not result[field]:
            raise ActionReportError(f"comparison result {field} is invalid")
    if result.get("status") not in {"passed", "failed"}:
        raise ActionReportError("comparison result status is invalid")
    for field in ("baseline_value", "candidate_value", "delta"):
        _finite_number(result.get(field), f"comparison {field}")
    _finite_number(result.get("increase_percent"), "comparison increase percent", nullable=True)
    absolute = _mapping(result.get("absolute"), "comparison absolute")
    relative = _mapping(result.get("relative"), "comparison relative")
    _finite_number(absolute.get("maximum"), "comparison absolute maximum")
    _finite_number(relative.get("maximum_increase_percent"), "comparison relative maximum")
    if absolute.get("status") not in {"passed", "failed"} or relative.get("status") not in {"passed", "failed"}:
        raise ActionReportError("comparison threshold status is invalid")


def validate_report(report: Any) -> dict[str, Any]:
    """Validate the stable presentation surface of Guardian report schemas v1/v2."""

    data = _mapping(report, "report")
    if data.get("schema_version") not in REPORT_SCHEMAS:
        raise ActionReportError("report schema is unsupported")
    if data.get("deterministic_status") not in REPORT_STATUSES:
        raise ActionReportError("deterministic status is unsupported")
    if data.get("authoritative_exit_code") not in {0, 1, 2}:
        raise ActionReportError("authoritative exit code is invalid")
    if not isinstance(data.get("authoritative_exit_reason"), str):
        raise ActionReportError("authoritative exit reason is missing")
    expected_status = {0: "passed", 1: "budget_failed", 2: "error"}[data["authoritative_exit_code"]]
    if data["deterministic_status"] != expected_status:
        raise ActionReportError("deterministic status contradicts authoritative exit")
    presentation_data = dict(data)
    if isinstance(data.get("investigation"), dict):
        presentation_data["investigation"] = dict(data["investigation"], report=None)
    if SENSITIVE_TEXT.search(json.dumps(presentation_data, sort_keys=True)):
        raise ActionReportError("report contains unsafe presentation data")

    validator = _mapping(data.get("validator"), "validator")
    if validator.get("status") not in VALIDATOR_STATUSES:
        raise ActionReportError("validator status is unsupported")
    for field in ("candidate_file_count", "validated_file_count"):
        if not isinstance(validator.get(field), int) or validator[field] < 0:
            raise ActionReportError(f"validator {field} is invalid")

    budget = _mapping(data.get("budget"), "budget")
    if budget.get("status") not in BUDGET_STATUSES:
        raise ActionReportError("budget status is unsupported")
    if not isinstance(budget.get("results"), list):
        raise ActionReportError("budget results are malformed")
    if not isinstance(budget.get("summary"), dict):
        raise ActionReportError("budget summary is malformed")
    if not isinstance(budget.get("limitations"), list):
        raise ActionReportError("budget limitations are malformed")
    for result in budget["results"]:
        _validate_absolute_result(result)

    investigation = _mapping(data.get("investigation"), "investigation")
    if investigation.get("outcome") not in INVESTIGATION_OUTCOMES:
        raise ActionReportError("investigation outcome is unsupported")
    if investigation.get("report") is not None and not isinstance(investigation["report"], str):
        raise ActionReportError("investigation report is malformed")

    comparison = data.get("comparison")
    if data["schema_version"] == 2:
        comparison = _mapping(comparison, "comparison")
        if not isinstance(comparison.get("results"), list):
            raise ActionReportError("comparison results are malformed")
        for result in comparison["results"]:
            _validate_comparison_result(result)
    elif comparison is not None:
        raise ActionReportError("schema v1 cannot contain comparison results")
    return data


def validate_calibration_report(report: Any) -> dict[str, Any]:
    """Validate the safe presentation surface of calibration report schema v1."""

    data = _mapping(report, "calibration report")
    if data.get("report_type") != CALIBRATION_REPORT_TYPE or data.get("schema_version") != 1:
        raise ActionReportError("calibration report schema is unsupported")
    if data.get("status") != "proposal_generated":
        raise ActionReportError("calibration report status is unsupported")
    if SENSITIVE_TEXT.search(json.dumps(data, sort_keys=True)):
        raise ActionReportError("calibration report contains unsafe presentation data")
    validator = _mapping(data.get("validator"), "calibration validator")
    if validator.get("status") != "passed":
        raise ActionReportError("calibration validator did not pass")
    for field in ("candidate_file_count", "validated_file_count"):
        if isinstance(validator.get(field), bool) or not isinstance(validator.get(field), int) or validator[field] < 3:
            raise ActionReportError(f"calibration validator {field} is invalid")
    calibration = _mapping(data.get("calibration"), "calibration settings")
    if calibration.get("preset") != "balanced" or calibration.get("proposal_authoritative") is not False:
        raise ActionReportError("calibration settings are unsupported")
    recommendations = data.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        raise ActionReportError("calibration recommendations are malformed")
    seen: set[str] = set()
    for value in recommendations:
        item = _mapping(value, "calibration recommendation")
        for field in ("budget_id", "evidence_id", "metric", "profile", "unit"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ActionReportError(f"calibration recommendation {field} is invalid")
        if item["budget_id"] in seen:
            raise ActionReportError("calibration recommendation ids are duplicated")
        seen.add(item["budget_id"])
        for field in ("observed_value", "margin_percent", "proposed_maximum", "relative_allowance_percent"):
            _finite_number(item.get(field), f"calibration recommendation {field}")
        if isinstance(item.get("run_count"), bool) or not isinstance(item.get("run_count"), int) or item["run_count"] < 3:
            raise ActionReportError("calibration recommendation run count is invalid")
    if not isinstance(data.get("proposed_policy"), dict) or not isinstance(data.get("limitations"), list):
        raise ActionReportError("calibration proposal metadata is malformed")
    return data


def _number(value: Any) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "invalid"
    if isinstance(value, float) and not math.isfinite(value):
        return "invalid"
    if float(value).is_integer():
        return str(int(value))
    return format(value, ".12g")


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _command_escape(value: Any, *, property_value: bool = False) -> str:
    escaped = str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        escaped = escaped.replace(":", "%3A").replace(",", "%2C")
    return escaped


def _safe_ai_report(investigation: dict[str, Any]) -> str | None:
    report = investigation.get("report")
    if investigation.get("outcome") not in {"accepted", "fallback"} or not isinstance(report, str):
        return None
    disclosure = MODEL_DISCLOSURE if investigation["outcome"] == "accepted" else FALLBACK_DISCLOSURE
    if disclosure not in report or len(report) > 40_000 or SENSITIVE_TEXT.search(report):
        return None
    return report.strip()


def _absolute_line(result: dict[str, Any]) -> str:
    measured = _number(result.get("measured_value"))
    maximum = _number(result.get("maximum_value"))
    unit = result.get("unit", "")
    operator = "<=" if result.get("status") == "passed" else ">"
    return f"{measured} {unit} {operator} {maximum} {unit}".strip()


def _comparison_line(result: dict[str, Any]) -> str:
    baseline = _number(result.get("baseline_value"))
    candidate = _number(result.get("candidate_value"))
    delta = _number(result.get("delta"))
    increase = _number(result.get("increase_percent"))
    maximum = _number(_mapping(result.get("relative"), "comparison relative").get("maximum_increase_percent"))
    return (
        f"baseline {baseline}, candidate {candidate}, delta {delta}; "
        f"increase {increase}% (maximum {maximum}%)"
    )


def _failed_annotations(report: dict[str, Any]) -> list[str]:
    failed: dict[str, list[str]] = {}
    for result in report["budget"]["results"]:
        if isinstance(result, dict) and result.get("status") == "failed":
            budget_id = str(result.get("budget_id", "unknown-rule"))
            failed.setdefault(budget_id, []).append(f"absolute: {_absolute_line(result)}")
    comparison = report.get("comparison")
    if isinstance(comparison, dict):
        for result in comparison.get("results", []):
            if not isinstance(result, dict) or result.get("status") != "failed":
                continue
            budget_id = str(result.get("budget_id", "unknown-rule"))
            relative = result.get("relative")
            if isinstance(relative, dict) and relative.get("status") == "failed":
                failed.setdefault(budget_id, []).append(f"relative: {_comparison_line(result)}")
    lines = []
    for budget_id in sorted(failed):
        details = "; ".join(dict.fromkeys(failed[budget_id]))
        title = _command_escape(f"Performance budget failed: {budget_id}", property_value=True)
        message = _command_escape(f"{budget_id} failed ({details}).")
        lines.append(f"::error title={title}::{message}")
    if not lines and report["authoritative_exit_code"] == 2:
        title = _command_escape("Performance Guardian evaluation error", property_value=True)
        message = _command_escape(
            "Deterministic validation or configuration prevented budget evaluation. "
            f"{report['authoritative_exit_reason']}"
        )
        lines.append(f"::error title={title}::{message}")
    return lines


def render_log(report: dict[str, Any], artifact_name: str) -> str:
    validator = report["validator"]
    budget = report["budget"]
    lines = [
        "Performance Guardian deterministic result",
        f"Validation: {validator['status'].upper()} "
        f"({validator['validated_file_count']} validated of {validator['candidate_file_count']} candidate files)",
        f"Budgets: {budget['status'].upper()}",
    ]
    for result in budget["results"]:
        if isinstance(result, dict):
            lines.append(
                f"- {str(result.get('status', 'unknown')).upper()} "
                f"{result.get('budget_id', 'unknown-rule')}: {_absolute_line(result)} "
                f"[{result.get('evidence_id', 'no-evidence')}]"
            )
    comparison = report.get("comparison")
    if isinstance(comparison, dict):
        lines.append(f"Comparison: {str(comparison.get('status', 'unknown')).upper()}")
        for result in comparison.get("results", []):
            if isinstance(result, dict):
                lines.append(
                    f"- {str(result.get('status', 'unknown')).upper()} "
                    f"{result.get('budget_id', 'unknown-rule')}: {_comparison_line(result)}"
                )
    investigation = report["investigation"]
    outcome = investigation["outcome"]
    if outcome == "api_error":
        lines.append(f"Optional AI: API_ERROR ({investigation.get('error_category') or 'unknown'})")
    else:
        lines.append(f"Optional AI: {outcome.upper()}")
    lines.extend(
        [
            f"Authoritative exit {report['authoritative_exit_code']}: {report['authoritative_exit_reason']}",
            f"Evidence artifact: {artifact_name}",
        ]
    )
    lines.extend(_failed_annotations(report))
    return "\n".join(lines) + "\n"


def render_summary(report: dict[str, Any], artifact_name: str) -> str:
    exit_code = report["authoritative_exit_code"]
    icon = "✅" if exit_code == 0 else "❌"
    validator = report["validator"]
    lines = [
        "# Performance Guardian",
        "",
        "> **Deterministic validation and budgets decide the job result. AI explanations are non-authoritative.**",
        "",
        "## Authoritative result",
        "",
        f"{icon} **Exit {exit_code}:** {_md(report['authoritative_exit_reason'])}",
        "",
        "## Validation",
        "",
        f"**{str(validator['status']).upper()}** — {validator['validated_file_count']} validated of "
        f"{validator['candidate_file_count']} candidate files.",
        "",
        "## Budget rules",
        "",
        "| Result | Rule | Metric | Measured | Maximum | Evidence |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for result in report["budget"]["results"]:
        if isinstance(result, dict):
            mark = "✅ Pass" if result.get("status") == "passed" else "❌ Fail"
            unit = result.get("unit", "")
            lines.append(
                f"| {mark} | `{_md(result.get('budget_id', 'unknown-rule'))}` | "
                f"`{_md(result.get('metric', 'unknown'))}` | "
                f"{_number(result.get('measured_value'))} {_md(unit)} | "
                f"{_number(result.get('maximum_value'))} {_md(unit)} | "
                f"`{_md(result.get('evidence_id', ''))}` |"
            )
    if not report["budget"]["results"]:
        lines.append("| Not evaluated | — | — | — | — | — |")

    comparison = report.get("comparison")
    if isinstance(comparison, dict) and comparison.get("status") != "not_requested":
        lines.extend(
            [
                "",
                "## Protected-base comparison",
                "",
                "| Result | Rule | Baseline | Candidate | Delta | Increase | Allowed | Evidence |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for result in comparison.get("results", []):
            if isinstance(result, dict):
                relative = result.get("relative") if isinstance(result.get("relative"), dict) else {}
                mark = "✅ Pass" if result.get("status") == "passed" else "❌ Fail"
                evidence = f"{result.get('baseline_evidence_id', '')}, {result.get('candidate_evidence_id', '')}"
                lines.append(
                    f"| {mark} | `{_md(result.get('budget_id', 'unknown-rule'))}` | "
                    f"{_number(result.get('baseline_value'))} | {_number(result.get('candidate_value'))} | "
                    f"{_number(result.get('delta'))} | {_number(result.get('increase_percent'))}% | "
                    f"{_number(relative.get('maximum_increase_percent'))}% | `{_md(evidence)}` |"
                )

    lines.extend(["", "## Optional AI explanation — non-authoritative", ""])
    investigation = report["investigation"]
    ai_report = _safe_ai_report(investigation)
    if ai_report is not None:
        lines.append(ai_report.replace("## ", "### "))
    elif investigation["outcome"] == "api_error":
        lines.append(
            f"AI investigation failed safely: `{_md(investigation.get('error_category') or 'unknown')}`."
        )
    elif investigation.get("report") is not None:
        lines.append("AI explanation omitted because it did not satisfy the safe presentation contract.")
    else:
        lines.append(f"AI investigation outcome: `{_md(investigation['outcome'])}`.")

    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"Download artifact `{_md(artifact_name)}` for the unchanged canonical JSON, raw captures, logs, and manifests available for this run.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_calibration_log(report: dict[str, Any], artifact_name: str) -> str:
    validator = report["validator"]
    lines = [
        "Performance Guardian calibration proposal",
        "PROPOSAL ONLY - NOT AN ENFORCED VERDICT",
        f"Validation: PASSED ({validator['validated_file_count']} validated captures)",
    ]
    for item in report["recommendations"]:
        lines.append(
            f"- {item['budget_id']}: observed {_number(item['observed_value'])} {item['unit']}; "
            f"margin {_number(item['margin_percent'])}%; proposed maximum "
            f"{_number(item['proposed_maximum'])} {item['unit']}; relative allowance "
            f"{_number(item['relative_allowance_percent'])}% [{item['evidence_id']}]"
        )
    lines.extend([
        f"Evidence artifact: {artifact_name}",
        "Download and review the proposal before applying or committing it.",
    ])
    return "\n".join(lines) + "\n"


def render_calibration_summary(report: dict[str, Any], artifact_name: str) -> str:
    validator = report["validator"]
    lines = [
        "# Performance Guardian calibration",
        "",
        "> **Proposal only—not an enforced verdict. Calibration does not decide whether a build passes.**",
        "",
        f"Validated **{validator['validated_file_count']}** captures with the balanced preset.",
        "",
        "## Proposed rules",
        "",
        "| Profile | Metric | Observed | Margin | Proposed maximum | Relative allowance | Evidence |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report["recommendations"]:
        lines.append(
            f"| `{_md(item['profile'])}` | `{_md(item['metric'])}` | "
            f"{_number(item['observed_value'])} {_md(item['unit'])} | "
            f"{_number(item['margin_percent'])}% | "
            f"{_number(item['proposed_maximum'])} {_md(item['unit'])} | "
            f"{_number(item['relative_allowance_percent'])}% | `{_md(item['evidence_id'])}` |"
        )
    lines.extend([
        "",
        "## Review and migration",
        "",
        "1. Run calibration on the default branch.",
        "2. Download and review the proposal.",
        "3. Apply it explicitly with `tools/calibrate_budgets.py --apply-proposal`.",
        "4. Commit the v3 policy while protected-base comparison remains disabled.",
        "5. Enable protected-base comparison in a later pull request.",
        "",
        "## Evidence",
        "",
        f"Download artifact `{_md(artifact_name)}` for the five captures, sanitized logs, manifests, calibration report, and proposed policy.",
    ])
    return "\n".join(lines) + "\n"


def render(report_path: Path, summary_path: Path, artifact_name: str) -> tuple[str, str]:
    if not artifact_name.strip() or any(character in artifact_name for character in "\r\n"):
        raise ActionReportError("artifact name is invalid")
    try:
        raw_report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ActionReportError("canonical report could not be read") from error
    if isinstance(raw_report, dict) and raw_report.get("report_type") == CALIBRATION_REPORT_TYPE:
        report = validate_calibration_report(raw_report)
        log = render_calibration_log(report, artifact_name)
        summary = render_calibration_summary(report, artifact_name)
    else:
        report = validate_report(raw_report)
        log = render_log(report, artifact_name)
        summary = render_summary(report, artifact_name)
    try:
        with summary_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(summary)
    except OSError as error:
        raise ActionReportError("job summary could not be written") from error
    return log, summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-file", required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("guardian_report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        log, _summary = render(
            Path(args.guardian_report), Path(args.summary_file), args.artifact_name
        )
    except ActionReportError:
        print(
            "::warning title=Performance Guardian presentation warning::"
            "Action report rendering failed safely; download the canonical report artifact."
        )
        return 2
    print(log, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
