"""Read-only OpenAI agent for interpreting validated Godot benchmark results."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable

from agents import Agent, ModelSettings, Runner, function_tool
from openai import RateLimitError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = (REPOSITORY_ROOT / "tools" / "validate_results.py").resolve()
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 30.0
SAFE_API_METADATA = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

INVESTIGATOR_INSTRUCTIONS = """\
You are the Godot Performance Investigator, a read-only reasoning layer over a
deterministic benchmark validator. You have exactly one tool. You must call
validate_benchmark_results before forming any verdict, using the exact
repository-relative results directory supplied by the user.

Treat the tool result as the only verified benchmark evidence available to you.
A successful validator exit means only that the supplied result set passed the
validator's configured assertions. It does not prove that the project has no
performance problems. Cite every numerical claim and every verified factual
claim with the opaque evidence ID supplied by the matching packet item, using
square brackets. Cover healthy, node_leak, and cpu_spike. You may connect
scenario behavior to an observed result only
when citing both validated-result evidence and allowlisted-source evidence.

Do not introduce thermal throttling, scheduling delays, locking, contention,
resource contention, system load, or another cause absent from the evidence.
Other ideas must be explicitly labeled as hypotheses, not findings. Include
this exact sentence: The available evidence does not establish the root cause.
Recommendations must be read-only, testable, and linked to evidence IDs.
Do not invent measurements or claim to have inspected files that the tool did
not expose.

Return a concise Markdown report using exactly these section headings:

## Validation status
## Verified facts
## Possible explanations
## Recommended next investigation
## Remaining uncertainty

Use this content skeleton. Validation status cites the validated-file-count
item. Verified facts cite workload, process, duration, retained-node,
configuration, and scenario-behavior items for all three scenarios. Possible
explanations connect observations only to allowlisted scenario behavior.
Every recommendation begins with a read-only test action and cites the evidence
that motivated it. Remaining uncertainty includes the exact required sentence.

If validation fails or the tool returns an error, explain that limitation and
recommend resolving it before interpreting performance. Never propose edits as
though they were already made. You cannot modify, delete, or overwrite files.
"""

REPORT_HEADINGS = (
    "## Validation status",
    "## Verified facts",
    "## Possible explanations",
    "## Recommended next investigation",
    "## Remaining uncertainty",
)
REQUIRED_UNCERTAINTY = "The available evidence does not establish the root cause."
BANNED_SPECULATION = (
    "thermal throttling",
    "scheduling delay",
    "locking",
    "contention",
    "resource contention",
    "system load",
)
REPORT_SOURCE_DISCLOSURE = (
    "Report source: Deterministic fallback generated after model output failed "
    "grounding."
)
EVIDENCE_CITATION = re.compile(r"\[([A-Za-z][A-Za-z0-9_.:-]{0,63})\]")
REQUIRED_EVIDENCE = {
    "validated_count": ("validated_file_count", "all", "validated_result", "files", "number"),
    "healthy_workload": ("median_p95_workload_time", "healthy", "validated_aggregate", "usec", "number"),
    "cpu_workload": ("median_p95_workload_time", "cpu_spike", "validated_aggregate", "usec", "number"),
    "workload_ratio": ("workload_time_ratio", "cpu_spike_vs_healthy", "validated_aggregate", "x", "number"),
    "healthy_process": ("median_p95_process_time", "healthy", "validated_aggregate", "ms", "number"),
    "cpu_process": ("median_p95_process_time", "cpu_spike", "validated_aggregate", "ms", "number"),
    "healthy_duration": ("median_scenario_duration", "healthy", "validated_aggregate", "ms", "number"),
    "cpu_duration": ("median_scenario_duration", "cpu_spike", "validated_aggregate", "ms", "number"),
    "duration_increase": ("scenario_duration_increase", "cpu_spike_vs_healthy", "validated_aggregate", "percent", "number"),
    "healthy_retained": ("post_cleanup_retained_nodes", "healthy", "validated_result", "nodes", "number"),
    "leak_retained": ("post_cleanup_retained_nodes", "node_leak", "validated_result", "nodes", "number"),
    "cpu_retained": ("post_cleanup_retained_nodes", "cpu_spike", "validated_result", "nodes", "number"),
    "cpu_configurations": ("cpu_workload_configurations", "cpu_spike", "validated_result", None, "mapping"),
    "healthy_behavior": ("scenario_behavior", "healthy", "allowlisted_source", None, "string"),
    "leak_behavior": ("scenario_behavior", "node_leak", "allowlisted_source", None, "string"),
    "cpu_behavior": ("scenario_behavior", "cpu_spike", "allowlisted_source", None, "string"),
}


class EvidenceSchemaError(ValueError):
    """The evidence packet cannot satisfy the semantic reporting contract."""


def resolve_results_directory(results_directory: str) -> tuple[Path, str, int]:
    """Resolve and validate a repository-contained benchmark result directory."""

    if not isinstance(results_directory, str) or not results_directory.strip():
        raise ValueError("A repository-relative results directory is required.")

    supplied = Path(results_directory)
    if supplied.is_absolute() or supplied.drive or supplied.anchor:
        raise ValueError("The results directory must be repository-relative.")

    resolved = (REPOSITORY_ROOT / supplied).resolve()
    try:
        relative = resolved.relative_to(REPOSITORY_ROOT)
    except ValueError as error:
        raise ValueError("The results directory must remain inside the repository.") from error

    if not resolved.exists():
        raise FileNotFoundError("The results directory does not exist.")
    if not resolved.is_dir():
        raise NotADirectoryError("The results path is not a directory.")

    json_file_count = sum(1 for path in resolved.glob("*.json") if path.is_file())
    if json_file_count == 0:
        raise FileNotFoundError("The results directory contains no JSON result files.")

    return resolved, relative.as_posix(), json_file_count


def _sanitized_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    text = value.decode(errors="replace") if isinstance(value, bytes) else str(value)
    root_variants = {
        str(REPOSITORY_ROOT),
        str(REPOSITORY_ROOT).replace("\\", "/"),
    }
    for root in root_variants:
        text = text.replace(root, "<repository>")
    return text


def _safe_api_metadata(value: object) -> str | None:
    if not isinstance(value, str) or not SAFE_API_METADATA.fullmatch(value):
        return None
    return value


def _numeric_retry_after(error: RateLimitError) -> float | None:
    headers = error.response.headers
    for header, divisor in (("retry-after-ms", 1000.0), ("retry-after", 1.0)):
        value = headers.get(header)
        try:
            seconds = float(value) / divisor
        except (TypeError, ValueError):
            continue
        if math.isfinite(seconds) and seconds >= 0:
            return seconds
    return None


def format_rate_limit_error(error: RateLimitError) -> str:
    """Return actionable 429 diagnostics without exposing raw API content."""

    code = _safe_api_metadata(error.code)
    error_type = _safe_api_metadata(error.type)
    request_id = _safe_api_metadata(error.request_id)
    retry_after = _numeric_retry_after(error)

    details = ["HTTP 429"]
    if code:
        details.append(f"code={code}")
    if error_type:
        details.append(f"type={error_type}")
    if request_id:
        details.append(f"request_id={request_id}")
    if retry_after is not None:
        details.append(f"retry_after={retry_after:g}s")

    classification = {value.lower() for value in (code, error_type) if value}
    prefix = f"ERROR: OpenAI API rate limit ({'; '.join(details)}). "
    if "insufficient_quota" in classification:
        return prefix + (
            "The API project has no available quota. Check API billing, credits, "
            "and project usage limits; retrying will not resolve this condition."
        )

    guidance = (
        "The request was throttled after the SDK's built-in retries. Check the "
        "API project's rate limits"
    )
    if retry_after is not None:
        guidance += f" and wait at least {retry_after:g} seconds before trying again"
    else:
        guidance += " before trying again"
    if any("model" in value.lower() for value in (code, error_type) if value):
        guidance += "; this limit appears model-specific, so verify OPENAI_MODEL access"
    return prefix + guidance + "."


def _evidence_packet(
    *,
    validation_status: str,
    validator_invoked: bool,
    results_directory: str | None,
    json_file_count: int | None,
    exit_code: int | None,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
    error_type: str | None = None,
) -> dict[str, Any]:
    return {
        "packet_type": "godot_performance_evidence",
        "schema_version": 1,
        "validation": {
            "status": validation_status,
            "validator_invoked": validator_invoked,
            "candidate_file_count": json_file_count or 0,
            "validated_file_count": 0,
            "exit_code": exit_code,
            "errors": [stderr] if stderr else [],
            "timed_out": timed_out,
            "error_type": error_type,
        },
        "results_directory": results_directory,
        "evidence": [],
        "limitations": [
            {
                "id": "L1",
                "statement": "No benchmark claim is verified because deterministic validation did not complete successfully.",
            }
        ],
    }


def run_validator(
    results_directory: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    *,
    subprocess_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Run the existing deterministic validator and return structured evidence."""

    try:
        _resolved, relative_directory, json_file_count = resolve_results_directory(
            results_directory
        )
    except (ValueError, FileNotFoundError, NotADirectoryError) as error:
        return _evidence_packet(
            validation_status="error",
            validator_invoked=False,
            results_directory=None,
            json_file_count=None,
            exit_code=None,
            stderr=str(error),
            error_type="invalid_results_directory",
        )

    command = [
        sys.executable,
        str(VALIDATOR_PATH),
        "--evidence-json",
        relative_directory,
    ]
    try:
        completed = subprocess_runner(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return _evidence_packet(
            validation_status="error",
            validator_invoked=True,
            results_directory=relative_directory,
            json_file_count=json_file_count,
            exit_code=None,
            stdout=_sanitized_text(error.stdout),
            stderr=_sanitized_text(error.stderr),
            timed_out=True,
            error_type="timeout",
        )
    except OSError:
        return _evidence_packet(
            validation_status="error",
            validator_invoked=True,
            results_directory=relative_directory,
            json_file_count=json_file_count,
            exit_code=None,
            stderr="The validator process could not be started.",
            error_type="os_error",
        )

    try:
        packet = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        return _evidence_packet(
            validation_status="error",
            validator_invoked=True,
            results_directory=relative_directory,
            json_file_count=json_file_count,
            exit_code=completed.returncode,
            stderr="The validator did not return a valid evidence packet.",
            error_type="invalid_evidence_packet",
        )

    if not isinstance(packet, dict) or packet.get("packet_type") != "godot_performance_evidence":
        return _evidence_packet(
            validation_status="error",
            validator_invoked=True,
            results_directory=relative_directory,
            json_file_count=json_file_count,
            exit_code=completed.returncode,
            stderr="The validator returned an unsupported evidence packet.",
            error_type="invalid_evidence_packet",
        )
    packet_validation = packet.get("validation")
    if not isinstance(packet_validation, dict) or packet_validation.get("exit_code") != completed.returncode:
        return _evidence_packet(
            validation_status="error",
            validator_invoked=True,
            results_directory=relative_directory,
            json_file_count=json_file_count,
            exit_code=completed.returncode,
            stderr="The validator evidence packet disagreed with the process exit status.",
            error_type="invalid_evidence_packet",
        )
    return packet


@function_tool(
    name_override="validate_benchmark_results",
    description_override=(
        "Run the repository's deterministic benchmark validator against a "
        "repository-relative results directory and return structured evidence."
    ),
)
def validate_benchmark_results(results_directory: str) -> dict[str, Any]:
    """Validate stored benchmark results before forming an investigation verdict."""

    return run_validator(results_directory)


def build_investigator(model: str | None = None) -> Agent[None]:
    """Build the read-only investigator without making a network request."""

    selected_model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    return Agent(
        name="Godot Performance Investigator",
        instructions=INVESTIGATOR_INSTRUCTIONS,
        model=selected_model,
        tools=[validate_benchmark_results],
        model_settings=ModelSettings(
            tool_choice="required",
            parallel_tool_calls=False,
        ),
        tool_use_behavior="run_llm_again",
        reset_tool_choice=True,
    )


def extract_evidence_packet(run_result: Any) -> dict[str, Any] | None:
    """Extract the packet actually returned by the sole tool call."""

    packets: list[dict[str, Any]] = []
    for item in getattr(run_result, "new_items", []):
        output = getattr(item, "output", None)
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError:
                continue
        if isinstance(output, dict) and output.get("packet_type") == "godot_performance_evidence":
            packets.append(output)
    return packets[0] if len(packets) == 1 else None


def _report_sections(report: str) -> dict[str, str] | None:
    positions = [report.find(heading) for heading in REPORT_HEADINGS]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        return None
    if len(re.findall(r"^## .+$", report, flags=re.MULTILINE)) != len(REPORT_HEADINGS):
        return None
    sections: dict[str, str] = {}
    for index, heading in enumerate(REPORT_HEADINGS):
        start = positions[index] + len(heading)
        end = positions[index + 1] if index + 1 < len(positions) else len(report)
        sections[heading] = report[start:end].strip()
    return sections


def _semantic_evidence(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Resolve required evidence by semantics; IDs are opaque citation labels."""

    evidence = packet.get("evidence")
    if not isinstance(evidence, list):
        raise EvidenceSchemaError("evidence must be a list")

    identifiers: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise EvidenceSchemaError("evidence items must be objects")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_.:-]{0,63}", identifier
        ):
            raise EvidenceSchemaError("evidence IDs must be safe opaque labels")
        identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise EvidenceSchemaError("evidence IDs must be unique")

    resolved: dict[str, dict[str, Any]] = {}
    for name, (metric, scenario, source_type, unit, value_kind) in REQUIRED_EVIDENCE.items():
        matches = [
            item
            for item in evidence
            if item.get("metric") == metric
            and item.get("scenario") == scenario
            and item.get("source_type") == source_type
        ]
        if len(matches) != 1:
            raise EvidenceSchemaError(f"semantic evidence {name!r} is missing or ambiguous")
        item = matches[0]
        if item.get("unit") != unit:
            raise EvidenceSchemaError(f"semantic evidence {name!r} has an invalid unit")
        value = item.get("value")
        if value_kind == "number" and (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            raise EvidenceSchemaError(f"semantic evidence {name!r} must be numeric")
        if value_kind == "mapping" and (
            not isinstance(value, dict) or not value
        ):
            raise EvidenceSchemaError(f"semantic evidence {name!r} must be a mapping")
        if value_kind == "string" and (
            not isinstance(value, str) or not value
        ):
            raise EvidenceSchemaError(f"semantic evidence {name!r} must be a string")
        if metric == "post_cleanup_retained_nodes" and (
            not isinstance(item.get("run_count"), int)
            or isinstance(item.get("run_count"), bool)
            or item["run_count"] <= 0
        ):
            raise EvidenceSchemaError(f"semantic evidence {name!r} needs a run count")
        if value_kind == "mapping" and any(
            not isinstance(key, str)
            or not key
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
            for key, count in value.items()
        ):
            raise EvidenceSchemaError(f"semantic evidence {name!r} has invalid entries")
        resolved[name] = item
    return resolved


def _citation(item: dict[str, Any]) -> str:
    return f"[{item['id']}]"


def _formatted_number(value: int | float, decimal_places: int) -> str:
    return f"{float(value):,.{decimal_places}f}"


def render_deterministic_fallback(packet: dict[str, Any]) -> str:
    """Render a report using only semantically matched packet evidence."""

    validation = packet.get("validation")
    passed = isinstance(validation, dict) and validation.get("status") == "passed"
    if not passed:
        return f"""## Validation status
{REPORT_SOURCE_DISCLOSURE}
Deterministic validation failed, so no benchmark fact is treated as verified.

## Verified facts
No benchmark facts are available.

## Possible explanations
The validation failure must be resolved before interpreting performance.

## Recommended next investigation
- Resolve the validator failure and run validation again.

## Remaining uncertainty
{REQUIRED_UNCERTAINTY}
"""

    evidence = _semantic_evidence(packet)
    configurations = evidence["cpu_configurations"]["value"]
    configuration_text = ", ".join(
        f"{configuration} across {run_count} runs"
        for configuration, run_count in sorted(configurations.items())
    )
    return f"""## Validation status
{REPORT_SOURCE_DISCLOSURE}
The validator passed {_formatted_number(evidence['validated_count']['value'], 0)} files under its configured checks {_citation(evidence['validated_count'])}.

## Verified facts
The healthy median p95 workload was {_formatted_number(evidence['healthy_workload']['value'], 3)} usec and the cpu_spike value was {_formatted_number(evidence['cpu_workload']['value'], 3)} usec, a {_formatted_number(evidence['workload_ratio']['value'], 2)}x ratio {_citation(evidence['healthy_workload'])} {_citation(evidence['cpu_workload'])} {_citation(evidence['workload_ratio'])}.
The corresponding process medians were {_formatted_number(evidence['healthy_process']['value'], 6)} ms and {_formatted_number(evidence['cpu_process']['value'], 6)} ms {_citation(evidence['healthy_process'])} {_citation(evidence['cpu_process'])}.
Median duration increased from {_formatted_number(evidence['healthy_duration']['value'], 3)} ms to {_formatted_number(evidence['cpu_duration']['value'], 3)} ms, an increase of {_formatted_number(evidence['duration_increase']['value'], 1)} percent {_citation(evidence['healthy_duration'])} {_citation(evidence['cpu_duration'])} {_citation(evidence['duration_increase'])}.
Every node_leak run retained {_formatted_number(evidence['leak_retained']['value'], 0)} nodes across {_formatted_number(evidence['leak_retained'].get('run_count', 0), 0)} runs {_citation(evidence['leak_retained'])}. Healthy retained {_formatted_number(evidence['healthy_retained']['value'], 0)} across {_formatted_number(evidence['healthy_retained'].get('run_count', 0), 0)} runs {_citation(evidence['healthy_retained'])}, and cpu_spike retained {_formatted_number(evidence['cpu_retained']['value'], 0)} across {_formatted_number(evidence['cpu_retained'].get('run_count', 0), 0)} runs {_citation(evidence['cpu_retained'])}.
Stored CPU configurations were {configuration_text} {_citation(evidence['cpu_configurations'])}.
The current controller gives healthy the actor workload only {_citation(evidence['healthy_behavior'])}, routes cpu_spike through the nested numerical workload {_citation(evidence['cpu_behavior'])}, and periodically retains node_leak nodes {_citation(evidence['leak_behavior'])}.

## Possible explanations
The observed cpu_spike timing is consistent with its intentional nested numerical workload {_citation(evidence['cpu_workload'])} {_citation(evidence['cpu_behavior'])}.
The node_leak retention is consistent with the controller's intentional periodic retention branch {_citation(evidence['leak_retained'])} {_citation(evidence['leak_behavior'])}.

## Recommended next investigation
- Compare each CPU configuration separately to avoid mixing stored configurations {_citation(evidence['cpu_configurations'])}.
- Inspect repeated healthy and cpu_spike runs under one fixed configuration {_citation(evidence['healthy_workload'])} {_citation(evidence['cpu_workload'])} {_citation(evidence['cpu_configurations'])}.
- Measure node growth over the node_leak samples against its retention behavior {_citation(evidence['leak_retained'])} {_citation(evidence['leak_behavior'])}.

## Remaining uncertainty
Validator success proves only that the configured checks passed; it does not prove that no other performance problem exists {_citation(evidence['validated_count'])}.
{REQUIRED_UNCERTAINTY}
"""


def _supported_number(token: str, cited_items: list[dict[str, Any]]) -> bool:
    normalized = token.replace(",", "")
    try:
        observed = float(normalized)
    except ValueError:
        return False

    candidates: list[float] = []
    for item in cited_items:
        values = [item.get("value"), item.get("run_count")]
        value = item.get("value")
        if isinstance(value, dict):
            for key, count in value.items():
                values.extend(re.findall(r"\d+(?:\.\d+)?", str(key)))
                values.append(count)
        for value in values:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                candidates.append(float(value))
            elif isinstance(value, str):
                try:
                    candidates.append(float(value))
                except ValueError:
                    pass
    return any(
        math.isclose(observed, candidate, rel_tol=0.0, abs_tol=max(1e-9, 0.05 * 10 ** -max(len(normalized.partition(".")[2]), 0)))
        or observed in {round(candidate, digits) for digits in range(0, 7)}
        for candidate in candidates
    )


def validate_grounded_report(report: str, packet: dict[str, Any]) -> list[str]:
    """Return stable rule identifiers for any grounding-contract violations."""

    errors: set[str] = set()
    sections = _report_sections(report)
    if sections is None:
        return ["G01_REPORT_SECTIONS"]

    evidence = packet.get("evidence") if isinstance(packet, dict) else None
    evidence_items = evidence if isinstance(evidence, list) else []
    by_id = {
        item.get("id"): item
        for item in evidence_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    citations = EVIDENCE_CITATION.findall(report)
    if any(citation not in by_id for citation in citations):
        errors.add("G02_UNKNOWN_EVIDENCE")

    validation = packet.get("validation", {}) if isinstance(packet, dict) else {}
    passed = isinstance(validation, dict) and validation.get("status") == "passed"
    lowered = report.lower()
    if passed:
        try:
            semantic = _semantic_evidence(packet)
        except EvidenceSchemaError:
            semantic = {}
            errors.add("G15_EVIDENCE_SCHEMA")
        required_ids = {item["id"] for item in semantic.values()}
        if not required_ids.issubset(set(citations)):
            errors.add("G03_REQUIRED_EVIDENCE_MISSING")
        for scenario in ("healthy", "node_leak", "cpu_spike"):
            if scenario not in lowered:
                errors.add("G04_SCENARIO_COVERAGE")
    elif re.search(r"\b(validation|validator)\b.{0,30}\b(pass|passed|success|successful)\b", lowered):
        errors.add("G05_FALSE_VALIDATION_SUCCESS")

    for line in report.splitlines():
        if line.startswith("##"):
            continue
        line_citations = EVIDENCE_CITATION.findall(line)
        numeric_text = EVIDENCE_CITATION.sub("", line)
        numeric_text = re.sub(r"(?<=\d)[x×](?=\d)", " ", numeric_text)
        numbers = re.findall(r"(?<![A-Za-z_0-9])\d[\d,]*(?:\.\d+)?", numeric_text)
        if numbers and not line_citations:
            errors.add("G06_UNCITED_NUMBER")
        cited_items = [by_id[citation] for citation in line_citations if citation in by_id]
        if numbers and cited_items and any(not _supported_number(number, cited_items) for number in numbers):
            errors.add("G07_UNSUPPORTED_NUMBER")

    if passed:
        for heading in ("## Validation status", "## Verified facts"):
            for line in sections[heading].splitlines():
                content = line.strip().lstrip("-* ")
                if (
                    content
                    and content != REPORT_SOURCE_DISCLOSURE
                    and not EVIDENCE_CITATION.search(content)
                ):
                    errors.add("G14_UNCITED_VERIFIED_FACT")

    if REQUIRED_UNCERTAINTY not in sections["## Remaining uncertainty"]:
        errors.add("G08_REQUIRED_UNCERTAINTY")
    supported_claims = " ".join(str(item.get("claim", "")) for item in evidence_items).lower()
    for phrase in BANNED_SPECULATION:
        if phrase in lowered and phrase not in supported_claims:
            errors.add("G09_UNSUPPORTED_CAUSE")

    if passed:
        behavior_ids = {
            semantic[name]["id"]
            for name in ("healthy_behavior", "leak_behavior", "cpu_behavior")
            if name in semantic
        }
        explanations = sections["## Possible explanations"]
        for line in explanations.splitlines():
            content = line.strip().lstrip("-* ")
            if not content or content == REQUIRED_UNCERTAINTY:
                continue
            cited = set(EVIDENCE_CITATION.findall(content))
            if "hypothesis" not in content.lower() and not cited.intersection(behavior_ids):
                errors.add("G10_UNGROUNDED_EXPLANATION")

    recommendations = sections["## Recommended next investigation"]
    for line in recommendations.splitlines():
        content = line.strip().lstrip("-* ")
        if not content:
            continue
        if passed and not EVIDENCE_CITATION.search(content):
            errors.add("G11_UNCITED_RECOMMENDATION")
        if re.search(r"\b(modify|edit|delete|overwrite|repair|fix|write)\b", content.lower()):
            errors.add("G12_MUTATING_RECOMMENDATION")
        if not re.search(r"\b(inspect|compare|measure|profile|validate|review|run|re-run|separate|capture|resolve)\b", content.lower()):
            errors.add("G13_UNTESTABLE_RECOMMENDATION")

    return sorted(errors)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interpret existing Godot benchmark results without modifying them."
    )
    parser.add_argument(
        "results_directory",
        help="Repository-relative directory containing benchmark result JSON files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)

    try:
        _resolved, relative_directory, _count = resolve_results_directory(
            args.results_directory
        )
    except (ValueError, FileNotFoundError, NotADirectoryError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not configured.", file=sys.stderr)
        return 2

    prompt = (
        "Investigate the stored Godot benchmark results in the repository-relative "
        f"directory {relative_directory!r}. Validate them before forming any verdict."
    )
    try:
        result = Runner.run_sync(build_investigator(), prompt)
    except RateLimitError as error:
        print(format_rate_limit_error(error), file=sys.stderr)
        return 1
    except Exception as error:  # The CLI must fail safely without exposing request details.
        print(f"ERROR: investigator run failed ({type(error).__name__}).", file=sys.stderr)
        return 1

    packet = extract_evidence_packet(result)
    if packet is None:
        print("ERROR: investigator grounding failed (G00_EVIDENCE_PACKET).", file=sys.stderr)
        return 1
    report = str(result.final_output)
    grounding_errors = validate_grounded_report(report, packet)
    if grounding_errors:
        print(
            f"WARNING: model output failed grounding ({','.join(grounding_errors)}); "
            "using deterministic fallback.",
            file=sys.stderr,
        )
        try:
            report = render_deterministic_fallback(packet)
        except EvidenceSchemaError:
            print("ERROR: investigator grounding failed (G15_EVIDENCE_SCHEMA).", file=sys.stderr)
            return 1
        fallback_errors = validate_grounded_report(report, packet)
        if fallback_errors:
            print(
                f"ERROR: deterministic fallback failed grounding "
                f"({','.join(fallback_errors)}).",
                file=sys.stderr,
            )
            return 1
        validation = packet.get("validation", {})
        print(report)
        return 0 if validation.get("status") == "passed" else 1

    validation = packet.get("validation", {})
    print(report)
    return 0 if validation.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
