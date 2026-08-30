"""Run the deterministic ten-case competition evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = Path("evaluation/cases.json")
DEFAULT_INTEGRITY = Path("evaluation/integrity.json")
TIMEOUT_SECONDS = 30
INTEGRITY_HASH_MODE = "sha256_utf8_lf"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]"),
    re.compile(r"/(?:Users|home|root|tmp)/"),
)


class EvaluationError(ValueError):
    """Safe evaluation configuration or operational error."""


def canonical_json(value: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False) + "\n"


def _repository_member(value: str, *, kind: str) -> Path:
    if not isinstance(value, str) or not value:
        raise EvaluationError(f"{kind} path is missing")
    supplied = Path(value)
    if supplied.is_absolute() or supplied.drive or supplied.anchor or ".." in supplied.parts:
        raise EvaluationError(f"{kind} path must be repository-relative")
    resolved = (REPOSITORY_ROOT / supplied).resolve()
    try:
        resolved.relative_to(REPOSITORY_ROOT)
    except ValueError as error:
        raise EvaluationError(f"{kind} path escapes the repository") from error
    if kind.endswith("directory") and not resolved.is_dir():
        raise EvaluationError(f"{kind} is missing or not a directory")
    if kind.endswith("file") and not resolved.is_file():
        raise EvaluationError(f"{kind} is missing or not a file")
    return resolved


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationError(f"{label} could not be read as JSON") from error
    if not isinstance(value, dict):
        raise EvaluationError(f"{label} must be a JSON object")
    return value


def _sha256_utf8_lf(path: Path) -> str:
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise EvaluationError("an integrity file could not be read as UTF-8 text") from error
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def verify_integrity(path: Path) -> dict[str, Any]:
    manifest = _load_json(path, label="integrity manifest")
    required = {"baseline_revision", "files", "final_revision", "hash_mode", "schema_version"}
    if set(manifest) != required:
        raise EvaluationError("integrity manifest fields are invalid")
    if manifest["schema_version"] != 2:
        raise EvaluationError("integrity manifest schema is unsupported")
    if manifest["hash_mode"] != INTEGRITY_HASH_MODE:
        raise EvaluationError("integrity manifest hash mode is unsupported")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise EvaluationError("integrity manifest files are invalid")
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise EvaluationError("integrity file entry is malformed")
        relative = entry.get("path")
        expected = entry.get("sha256")
        if not isinstance(relative, str) or relative in seen:
            raise EvaluationError("integrity file paths are invalid or duplicated")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise EvaluationError("integrity hash is malformed")
        seen.add(relative)
        member = _repository_member(relative, kind="integrity file")
        if _sha256_utf8_lf(member) != expected:
            raise EvaluationError(f"integrity mismatch for {relative}")
    return manifest


def load_cases(path: Path) -> dict[str, Any]:
    manifest = _load_json(path, label="case manifest")
    required = {"baseline_revision", "cases", "final_revision", "primary_metric", "schema_version"}
    if set(manifest) != required or manifest.get("schema_version") != 1:
        raise EvaluationError("case manifest fields or schema are invalid")
    if manifest.get("primary_metric") != "correct_actionable_outcomes":
        raise EvaluationError("case manifest primary metric is unsupported")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 10:
        raise EvaluationError("case manifest must contain exactly ten cases")
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise EvaluationError("case entry is malformed")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not SAFE_ID.fullmatch(case_id) or case_id in ids:
            raise EvaluationError("case ids are invalid or duplicated")
        ids.add(case_id)
        if not isinstance(case.get("title"), str) or not case["title"]:
            raise EvaluationError(f"case {case_id} title is invalid")
        for side in ("baseline", "final"):
            config = case.get(side)
            if not isinstance(config, dict) or not isinstance(config.get("runner"), str):
                raise EvaluationError(f"case {case_id} {side} runner is invalid")
        expected = case.get("expected")
        if not isinstance(expected, dict) or set(expected) != {"checks", "exit_code", "outcome"}:
            raise EvaluationError(f"case {case_id} expected outcome is malformed")
        if not isinstance(expected["checks"], list):
            raise EvaluationError(f"case {case_id} checks are malformed")
    return manifest


def _run(command: list[str], *, cwd: Path = REPOSITORY_ROOT) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise EvaluationError("an evaluation command timed out") from error
    except OSError as error:
        raise EvaluationError("an evaluation command could not be launched") from error


def _parse_json_output(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise EvaluationError("an evaluation command returned malformed JSON") from error
    if not isinstance(value, dict):
        raise EvaluationError("an evaluation command returned a non-object JSON value")
    return value


def _synthetic_result(completed: subprocess.CompletedProcess[str]) -> tuple[str, dict[str, Any]]:
    count_match = re.search(r"Validated (\d+) result files successfully\.", completed.stdout)
    ratio_match = re.search(r"ratio=([0-9]+(?:\.[0-9]+)?)x", completed.stdout)
    evidence: dict[str, Any] = {}
    if count_match:
        evidence["validated_file_count"] = int(count_match.group(1))
    if ratio_match:
        evidence["workload_ratio"] = float(ratio_match.group(1))
    return ("passed" if completed.returncode == 0 else "safe_error"), evidence


def _generic_result(completed: subprocess.CompletedProcess[str]) -> tuple[str, dict[str, Any]]:
    packet = _parse_json_output(completed)
    validation = packet.get("validation") if isinstance(packet.get("validation"), dict) else {}
    evidence_items = packet.get("evidence") if isinstance(packet.get("evidence"), list) else []
    evidence: dict[str, Any] = {
        "candidate_file_count": validation.get("candidate_file_count"),
        "validated_file_count": validation.get("validated_file_count"),
        "error_markers": {},
    }
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        if item.get("metric") == "median_p95_process_time" and item.get("profile") == "main_scene":
            evidence["process_p95_ms"] = item.get("value")
        if item.get("metric") == "median_peak_node_count" and item.get("profile") == "main_scene":
            evidence["peak_nodes"] = item.get("value")
    errors = validation.get("errors") if isinstance(validation.get("errors"), list) else []
    evidence["error_markers"]["missing_schema_version"] = any(
        isinstance(item, str) and "schema_version" in item for item in errors
    )
    outcome = "passed" if validation.get("status") == "passed" and completed.returncode == 0 else "safe_error"
    return outcome, evidence


def _guardian_result(completed: subprocess.CompletedProcess[str]) -> tuple[str, dict[str, Any]]:
    report = _parse_json_output(completed)
    budget = report.get("budget") if isinstance(report.get("budget"), dict) else {}
    summary = budget.get("summary") if isinstance(budget.get("summary"), dict) else {}
    evidence: dict[str, Any] = {
        "failed_rule_count": summary.get("failed"),
        "rules": {},
        "comparison_rules": {},
    }
    for item in budget.get("results", []):
        if not isinstance(item, dict) or not isinstance(item.get("budget_id"), str):
            continue
        evidence["rules"][item["budget_id"]] = {
            "maximum": item.get("maximum_value"),
            "measured": item.get("measured_value"),
            "status": item.get("status"),
            "unit": item.get("unit"),
        }
    comparison = report.get("comparison") if isinstance(report.get("comparison"), dict) else None
    if comparison is not None:
        comparison_summary = comparison.get("summary") if isinstance(comparison.get("summary"), dict) else {}
        evidence["failed_rule_count"] = comparison_summary.get("failed")
        for item in comparison.get("results", []):
            if not isinstance(item, dict) or not isinstance(item.get("budget_id"), str):
                continue
            absolute = item.get("absolute") if isinstance(item.get("absolute"), dict) else {}
            relative = item.get("relative") if isinstance(item.get("relative"), dict) else {}
            evidence["comparison_rules"][item["budget_id"]] = {
                "absolute_maximum": absolute.get("maximum"),
                "absolute_status": absolute.get("status"),
                "baseline": item.get("baseline_value"),
                "candidate": item.get("candidate_value"),
                "delta": item.get("delta"),
                "increase_percent": item.get("increase_percent"),
                "relative_maximum": relative.get("maximum_increase_percent"),
                "relative_status": relative.get("status"),
                "status": item.get("status"),
                "unit": item.get("unit"),
            }
    deterministic = report.get("deterministic_status")
    outcome = "safe_error" if deterministic == "error" else deterministic
    if outcome not in {"passed", "budget_failed", "safe_error"}:
        raise EvaluationError("Guardian returned an unsupported deterministic status")
    return outcome, evidence


def _calibration_result(completed: subprocess.CompletedProcess[str]) -> tuple[str, dict[str, Any]]:
    report = _parse_json_output(completed)
    validator = report.get("validator") if isinstance(report.get("validator"), dict) else {}
    evidence: dict[str, Any] = {
        "validated_file_count": validator.get("validated_file_count"),
        "recommendations": {},
    }
    for item in report.get("recommendations", []):
        if not isinstance(item, dict) or not isinstance(item.get("budget_id"), str):
            continue
        evidence["recommendations"][item["budget_id"]] = {
            "observed": item.get("observed_value"),
            "proposed_maximum": item.get("proposed_maximum"),
            "relative_allowance_percent": item.get("relative_allowance_percent"),
            "unit": item.get("unit"),
        }
    return ("proposal_generated" if report.get("status") == "proposal_generated" else "safe_error"), evidence


def _execute_runner(case: dict[str, Any], side: str) -> tuple[int | None, str, dict[str, Any]]:
    config = case[side]
    runner = config["runner"]
    if runner == "unsupported":
        return None, "unsupported", {}
    inputs = case.get("inputs")
    if not isinstance(inputs, dict):
        raise EvaluationError(f"case {case['id']} inputs are malformed")
    results = _repository_member(inputs["results"], kind="results directory")
    if runner == "synthetic_validator":
        script = (
            REPOSITORY_ROOT / "evaluation/baseline/validate_results.py"
            if side == "baseline"
            else REPOSITORY_ROOT / "tools/validate_results.py"
        )
        completed = _run([sys.executable, str(script), str(results)])
        outcome, evidence = _synthetic_result(completed)
        return completed.returncode, outcome, evidence
    if runner == "generic_validator":
        script = REPOSITORY_ROOT / "tools/validate_results.py"
        completed = _run([sys.executable, str(script), "--evidence-json", str(results)])
        outcome, evidence = _generic_result(completed)
        return completed.returncode, outcome, evidence
    if runner in {"guardian", "guardian_comparison"}:
        _repository_member(inputs["budget"], kind="budget file")
        command = [
            sys.executable,
            str(REPOSITORY_ROOT / "tools/run_guardian.py"),
            "--json",
            "--investigate",
            "never",
        ]
        if runner == "guardian_comparison":
            _repository_member(inputs["baseline_results"], kind="baseline results directory")
            command.extend(["--baseline-results", inputs["baseline_results"]])
        command.extend([inputs["results"], inputs["budget"]])
        completed = _run(command)
        outcome, evidence = _guardian_result(completed)
        return completed.returncode, outcome, evidence
    if runner == "calibration":
        with tempfile.TemporaryDirectory(prefix="pbg-submission-evaluation-") as temporary:
            workspace = Path(temporary).resolve()
            copied_results = workspace / "results"
            shutil.copytree(results, copied_results)
            command = [
                sys.executable,
                str(REPOSITORY_ROOT / "tools/calibrate_budgets.py"),
                "--workspace-root",
                str(workspace),
                "--json",
                "--policy-output",
                "proposal.json",
                "--report-output",
                "report.json",
                "results",
            ]
            completed = _run(command)
            outcome, evidence = _calibration_result(completed)
            if completed.returncode == 0 and not (workspace / "proposal.json").is_file():
                raise EvaluationError("calibration did not create its proposed policy")
            return completed.returncode, outcome, evidence
    raise EvaluationError(f"case {case['id']} uses an unsupported runner")


def _value_at(value: Any, path: list[Any]) -> Any:
    current = value
    for part in path:
        if not isinstance(part, str) or not isinstance(current, dict) or part not in current:
            raise KeyError(part)
        current = current[part]
    return current


def _equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-9)
        )
    return actual == expected


def _unsafe(value: Any) -> bool:
    serialized = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return any(pattern.search(serialized) for pattern in SECRET_PATTERNS + ABSOLUTE_PATH_PATTERNS)


def _score(case: dict[str, Any], side: str) -> dict[str, Any]:
    exit_code, outcome, evidence = _execute_runner(case, side)
    expected = case["expected"]
    failures: list[str] = []
    if outcome == "unsupported":
        failures.append("unsupported_capability")
    else:
        if exit_code != expected["exit_code"]:
            failures.append("exit_code_mismatch")
        if outcome != expected["outcome"]:
            failures.append("outcome_mismatch")
        for index, check in enumerate(expected["checks"], 1):
            if not isinstance(check, dict) or set(check) != {"equals", "path"} or not isinstance(check["path"], list):
                raise EvaluationError(f"case {case['id']} check {index} is malformed")
            try:
                actual = _value_at(evidence, check["path"])
            except KeyError:
                failures.append(f"required_evidence_{index}_missing")
                continue
            if not _equal(actual, check["equals"]):
                failures.append(f"required_evidence_{index}_mismatch")
        if _unsafe(evidence):
            failures.append("unsafe_output")
    result: dict[str, Any] = {
        "correct_actionable_outcome": not failures,
        "evidence": evidence,
        "exit_code": exit_code,
        "failures": failures,
        "outcome": outcome,
    }
    if outcome == "unsupported":
        result["reason"] = case[side].get("reason", "Capability unavailable in this implementation.")
    return result


def _summary(results: list[dict[str, Any]], side: str) -> dict[str, Any]:
    correct = sum(1 for item in results if item[side]["correct_actionable_outcome"])
    total = len(results)
    outcomes: dict[str, int] = {}
    for item in results:
        outcome = item[side]["outcome"]
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    return {
        "correct_actionable_outcomes": correct,
        "outcome_counts": dict(sorted(outcomes.items())),
        "percent": round(correct * 100.0 / total, 3),
        "total_cases": total,
    }


def run_evaluation(*, cases_path: Path = DEFAULT_CASES, integrity_path: Path = DEFAULT_INTEGRITY) -> dict[str, Any]:
    cases_member = _repository_member(cases_path.as_posix(), kind="case manifest file")
    integrity_member = _repository_member(integrity_path.as_posix(), kind="integrity manifest file")
    integrity = verify_integrity(integrity_member)
    manifest = load_cases(cases_member)
    if manifest["baseline_revision"] != integrity["baseline_revision"]:
        raise EvaluationError("baseline revision metadata disagrees")
    if manifest["final_revision"] != integrity["final_revision"]:
        raise EvaluationError("final revision metadata disagrees")
    case_results: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        case_results.append({
            "baseline": _score(case, "baseline"),
            "challenging": bool(case.get("challenging", False)),
            "final": _score(case, "final"),
            "id": case["id"],
            "title": case["title"],
        })
    baseline = _summary(case_results, "baseline")
    final = _summary(case_results, "final")
    return {
        "api_cost_usd": 0,
        "baseline": {"revision": manifest["baseline_revision"], **baseline},
        "cases": case_results,
        "change_percentage_points": round(final["percent"] - baseline["percent"], 3),
        "final": {"revision": manifest["final_revision"], **final},
        "human_review_time": "not_measured",
        "limitations": [
            "The ten cases measure deterministic workflow coverage and evidence quality, not game-frame performance improvement.",
            "Baseline 0 exposes only its synthetic validator; unsupported later workflows are recorded as unsupported rather than simulated.",
            "Fixed fixtures make verdicts reproducible but do not replace fresh project captures on customer hardware.",
            "Human review time was not measured.",
            "Optional AI behavior is excluded from the primary score because model responses are nondeterministic and require external quota.",
        ],
        "primary_metric": {
            "definition": "A case counts only when status, required evidence, and safe actionable detail all match its predefined oracle.",
            "name": manifest["primary_metric"],
        },
        "report_type": "godot_performance_guardian_final_evaluation",
        "schema_version": 1,
    }


def _atomic_write(path: Path, content: str, *, replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        raise EvaluationError("evaluation output exists; pass --replace to replace it")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise EvaluationError("evaluation temporary-file collision")
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
        raise EvaluationError("evaluation output could not be written atomically") from error
    finally:
        temporary.unlink(missing_ok=True)


def _human(report: dict[str, Any]) -> str:
    lines = [
        "Final competition evaluation",
        f"Baseline: {report['baseline']['correct_actionable_outcomes']}/{report['baseline']['total_cases']} "
        f"({report['baseline']['percent']}%)",
        f"Final: {report['final']['correct_actionable_outcomes']}/{report['final']['total_cases']} "
        f"({report['final']['percent']}%)",
        f"Change: {report['change_percentage_points']} percentage points",
        "",
    ]
    for case in report["cases"]:
        marker = "PASS" if case["final"]["correct_actionable_outcome"] else "FAIL"
        lines.append(f"[{marker}] {case['id']}: {case['title']}")
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--output", help="optional repository-relative canonical JSON output")
    parser.add_argument("--replace", action="store_true", help="replace an existing output atomically")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.replace and not args.output:
            raise EvaluationError("--replace requires --output")
        report = run_evaluation()
        content = canonical_json(report)
        if args.output:
            output = Path(args.output)
            if output.is_absolute() or output.drive or output.anchor or ".." in output.parts or output.suffix.lower() != ".json":
                raise EvaluationError("evaluation output must be a repository-relative JSON path")
            resolved = (REPOSITORY_ROOT / output).resolve()
            try:
                resolved.relative_to(REPOSITORY_ROOT)
            except ValueError as error:
                raise EvaluationError("evaluation output escapes the repository") from error
            _atomic_write(resolved, content, replace=args.replace)
        print(content if args.json_output else _human(report), end="")
        return 0 if report["final"]["correct_actionable_outcomes"] == report["final"]["total_cases"] else 1
    except EvaluationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
