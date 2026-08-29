"""Read-only OpenAI agent for interpreting validated Godot benchmark results."""

from __future__ import annotations

import argparse
from enum import Enum
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable

from agents import Agent, ModelBehaviorError, ModelSettings, Runner, function_tool
from agents.lifecycle import RunHooksBase
from openai import RateLimitError
from pydantic import BaseModel, ConfigDict, Field, ValidationError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = (REPOSITORY_ROOT / "tools" / "validate_results.py").resolve()
COMPARISON_PATH = (REPOSITORY_ROOT / "tools" / "comparison_evidence.py").resolve()
ACTIVE_WORKSPACE_ROOT = REPOSITORY_ROOT
ACTIVE_BASELINE_RESULTS: str | None = None
ACTIVE_BUDGET_FILE: str | None = None
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 30.0
SAFE_API_METADATA = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

INVESTIGATOR_INSTRUCTIONS = """\
You are the Godot Performance Investigator, a read-only reasoning layer over a
deterministic benchmark validator. You have exactly one tool. You must call
validate_benchmark_results before forming any verdict, using the exact
repository-relative results directory supplied by the user.

Treat the tool result as the only verified benchmark evidence available to you.
A successful validator exit means only that its configured checks passed. The
application, not you, renders verified facts, measurements, citations,
limitations, headings, and uncertainty from the packet.
For comparison packets, cite semantic baseline/candidate policy items and never
reveal, compare, or claim equality of source-revision values.

Return only the typed contribution requested by the response schema. Supply one
to three recommendations and zero to three hypotheses. Each item must cite one
to four unique opaque evidence IDs from the tool packet. Select recommendation
actions only from the schema enum. Hypothesis explanations are plain text of at
most 240 characters and must remain non-causal.

Do not put Markdown, newlines, measurements, paths, credentials, or bracketed
citations in explanation text. Do not use causal or conclusive terms such as
proves, confirmed, caused by, causes, memory leak, leak, or bottleneck. Do not
invent evidence or revision values. Recommendations are read-only controlled
investigations; you cannot modify, delete, overwrite, repair, or write files.
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
MODEL_REPORT_SOURCE_DISCLOSURE = (
    "Report source: Locally rendered from validated evidence and accepted "
    "model-authored investigation items."
)
EVIDENCE_CITATION = re.compile(r"\[([A-Za-z][A-Za-z0-9_.:-]{0,63})\]")
SYNTHETIC_REQUIRED_EVIDENCE = {
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
REQUIRED_EVIDENCE = SYNTHETIC_REQUIRED_EVIDENCE
GENERIC_METRIC_SPECS = {
    "process": ("median_p95_process_time", "validated_aggregate", "ms", "number"),
    "physics": ("median_p95_physics_process_time", "validated_aggregate", "ms", "number"),
    "duration": ("median_measurement_duration", "validated_aggregate", "ms", "number"),
    "objects": ("median_peak_object_count", "validated_aggregate", "objects", "number"),
    "nodes": ("median_peak_node_count", "validated_aggregate", "nodes", "number"),
    "orphans": ("median_peak_orphan_node_count", "validated_aggregate", "nodes", "number"),
    "memory": ("median_peak_memory_static_bytes", "validated_aggregate", "bytes", "number"),
    "memory_status": ("memory_static_availability", "validated_metadata", None, "memory_status"),
    "revision_status": ("source_revision_availability", "validated_metadata", None, "revision_status"),
}
GENERIC_PROFILE_DISCOVERY_METRICS = {
    specification[0] for specification in GENERIC_METRIC_SPECS.values()
}
GENERIC_MEMORY_STATUSES = {"available", "unavailable", "mixed"}
GENERIC_REVISION_STATUSES = {"present", "unknown", "mixed"}
SAFE_EVIDENCE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
SAFE_PROFILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class RecommendationAction(str, Enum):
    """Read-only recommendation actions exposed to the model."""

    COMPARE = "compare"
    INSPECT = "inspect"
    MEASURE = "measure"
    PROFILE = "profile"
    VALIDATE = "validate"
    CAPTURE = "capture"
    REPEAT_CAPTURE = "repeat_capture"


class HypothesisContribution(BaseModel):
    """A bounded, non-causal model-authored hypothesis."""

    model_config = ConfigDict(extra="forbid")
    explanation: str = Field(min_length=1, max_length=240)
    evidence_ids: list[str] = Field(min_length=1, max_length=4)


class RecommendationContribution(BaseModel):
    """An enum-selected investigation action linked to packet evidence."""

    model_config = ConfigDict(extra="forbid")
    action: RecommendationAction
    evidence_ids: list[str] = Field(min_length=1, max_length=4)


class InvestigatorContribution(BaseModel):
    """Strict typed output produced after the validator tool call."""

    model_config = ConfigDict(extra="forbid")
    hypotheses: list[HypothesisContribution] = Field(min_length=0, max_length=3)
    recommendations: list[RecommendationContribution] = Field(min_length=1, max_length=3)


class EvidenceSchemaError(ValueError):
    """The evidence packet cannot satisfy the semantic reporting contract."""


def resolve_workspace_root(value: str | Path | None = None) -> Path:
    candidate = REPOSITORY_ROOT if value is None else Path(value)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError("The workspace root does not exist.") from error
    if not resolved.is_dir():
        raise ValueError("The workspace root is not a directory.")
    return resolved


def resolve_results_directory(
    results_directory: str,
    workspace_root: Path | None = None,
) -> tuple[Path, str, int]:
    """Resolve and validate a repository-contained benchmark result directory."""

    if not isinstance(results_directory, str) or not results_directory.strip():
        raise ValueError("A repository-relative results directory is required.")

    supplied = Path(results_directory)
    if supplied.is_absolute() or supplied.drive or supplied.anchor:
        raise ValueError("The results directory must be repository-relative.")

    root = resolve_workspace_root(workspace_root or ACTIVE_WORKSPACE_ROOT)
    resolved = (root / supplied).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("The results directory must remain inside the workspace.") from error

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
        str(ACTIVE_WORKSPACE_ROOT),
        str(ACTIVE_WORKSPACE_ROOT).replace("\\", "/"),
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
        "evidence_kind": "failed",
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
    workspace_root: Path | None = None,
    subprocess_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    baseline_results: str | None = None,
    budget_file: str | None = None,
) -> dict[str, Any]:
    """Run the existing deterministic validator and return structured evidence."""

    root = resolve_workspace_root(workspace_root or ACTIVE_WORKSPACE_ROOT)
    try:
        _resolved, relative_directory, json_file_count = resolve_results_directory(
            results_directory,
            root,
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

    if (baseline_results is None) != (budget_file is None):
        return _evidence_packet(
            validation_status="error", validator_invoked=False,
            results_directory=relative_directory, json_file_count=json_file_count,
            exit_code=None, stderr="Baseline results and budget file must be supplied together.",
            error_type="invalid_comparison_inputs",
        )
    command = [sys.executable]
    if baseline_results is None:
        command.extend([str(VALIDATOR_PATH), "--evidence-json"])
    else:
        try:
            _base, relative_baseline, _base_count = resolve_results_directory(
                baseline_results, root
            )
            supplied_budget = Path(budget_file or "")
            if supplied_budget.is_absolute() or supplied_budget.drive or supplied_budget.anchor:
                raise ValueError("The budget file must be workspace-relative.")
            resolved_budget = (root / supplied_budget).resolve(strict=True)
            relative_budget = resolved_budget.relative_to(root).as_posix()
            if not resolved_budget.is_file() or resolved_budget.suffix.lower() != ".json":
                raise ValueError("The budget file must be a JSON file.")
        except (ValueError, OSError, FileNotFoundError, NotADirectoryError):
            return _evidence_packet(
                validation_status="error", validator_invoked=False,
                results_directory=relative_directory, json_file_count=json_file_count,
                exit_code=None, stderr="Comparison inputs are invalid.",
                error_type="invalid_comparison_inputs",
            )
        command.extend([
            str(COMPARISON_PATH),
            relative_baseline,
            relative_directory,
            relative_budget,
        ])
    if root != REPOSITORY_ROOT.resolve():
        command.extend(["--workspace-root", str(root)])
    if baseline_results is None:
        command.append(relative_directory)
    try:
        completed = subprocess_runner(
            command,
            cwd=root,
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

    if (
        not isinstance(packet, dict)
        or packet.get("packet_type") != "godot_performance_evidence"
        or packet.get("schema_version") not in {1, 2}
        or packet.get("evidence_kind") not in {"synthetic", "generic", "comparison", "failed"}
    ):
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
def validate_benchmark_results(
    results_directory: str,
    baseline_results: str | None = None,
    budget_file: str | None = None,
) -> dict[str, Any]:
    """Validate stored benchmark results before forming an investigation verdict."""

    if ACTIVE_BASELINE_RESULTS is not None:
        if baseline_results not in {None, ACTIVE_BASELINE_RESULTS} or budget_file not in {
            None,
            ACTIVE_BUDGET_FILE,
        }:
            return _evidence_packet(
                validation_status="error",
                validator_invoked=False,
                results_directory=None,
                json_file_count=None,
                exit_code=None,
                stderr="The comparison tool arguments did not match the approved CLI inputs.",
                error_type="invalid_comparison_inputs",
            )
        baseline_results = ACTIVE_BASELINE_RESULTS
        budget_file = ACTIVE_BUDGET_FILE
    return run_validator(
        results_directory,
        baseline_results=baseline_results,
        budget_file=budget_file,
    )


def build_investigator(model: str | None = None) -> Agent[None]:
    """Build the read-only investigator without making a network request."""

    selected_model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    return Agent(
        name="Godot Performance Investigator",
        instructions=INVESTIGATOR_INSTRUCTIONS,
        model=selected_model,
        tools=[validate_benchmark_results],
        output_type=InvestigatorContribution,
        model_settings=ModelSettings(
            tool_choice="required",
            parallel_tool_calls=False,
        ),
        tool_use_behavior="run_llm_again",
        reset_tool_choice=True,
    )


def _coerce_evidence_packet(output: object) -> dict[str, Any] | None:
    """Parse one tool output without accepting arbitrary response content."""

    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return None
    if not isinstance(output, dict) or output.get("packet_type") != "godot_performance_evidence":
        return None
    try:
        kind = _packet_evidence_kind(output)
        if kind == "synthetic":
            _semantic_evidence(output)
        elif kind == "generic":
            _generic_semantic_evidence(output)
        elif kind == "comparison":
            _comparison_semantic_evidence(output)
    except EvidenceSchemaError:
        return None
    return output


class EvidenceCaptureHooks(RunHooksBase):
    """Retain one safely validated tool packet if final-output parsing fails."""

    def __init__(self) -> None:
        self.packet: dict[str, Any] | None = None
        self.packet_count = 0

    async def on_tool_end(
        self,
        context: Any,
        agent: Any,
        tool: Any,
        result: object,
    ) -> None:
        if getattr(tool, "name", None) != "validate_benchmark_results":
            return
        packet = _coerce_evidence_packet(result)
        if packet is None:
            return
        self.packet_count += 1
        self.packet = packet if self.packet_count == 1 else None

    def recovered_packet(self) -> dict[str, Any] | None:
        return self.packet if self.packet_count == 1 else None


def extract_evidence_packet(run_result: Any) -> dict[str, Any] | None:
    """Extract the packet actually returned by the sole tool call."""

    packets: list[dict[str, Any]] = []
    for item in getattr(run_result, "new_items", []):
        output = getattr(item, "output", None)
        packet = _coerce_evidence_packet(output)
        if packet is not None:
            packets.append(packet)
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


def _safe_repository_reference(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    candidate = Path(value)
    return not candidate.is_absolute() and not candidate.drive and ".." not in candidate.parts


def _packet_evidence_kind(packet: dict[str, Any]) -> str:
    """Validate common packet metadata and return its explicit evidence kind."""

    if (
        not isinstance(packet, dict)
        or packet.get("packet_type") != "godot_performance_evidence"
        or isinstance(packet.get("schema_version"), bool)
        or packet.get("schema_version") not in {1, 2}
    ):
        raise EvidenceSchemaError("evidence packet identity is unsupported")
    kind = packet.get("evidence_kind")
    if kind not in {"synthetic", "generic", "comparison", "failed"}:
        raise EvidenceSchemaError("evidence kind is missing or unsupported")
    validation = packet.get("validation")
    if not isinstance(validation, dict) or validation.get("status") not in {
        "passed",
        "failed",
        "error",
    }:
        raise EvidenceSchemaError("validation metadata is invalid")
    passed = validation.get("status") == "passed"
    if passed != (kind in {"synthetic", "generic", "comparison"}):
        raise EvidenceSchemaError("evidence kind disagrees with validation status")
    for key in ("candidate_file_count", "validated_file_count"):
        value = validation.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise EvidenceSchemaError("validation count metadata is invalid")
    if passed and (
        validation.get("exit_code") != 0
        or validation["candidate_file_count"] < 1
        or validation["validated_file_count"] < 1
    ):
        raise EvidenceSchemaError("passed validation metadata is inconsistent")
    if not isinstance(validation.get("errors"), list):
        raise EvidenceSchemaError("validation errors metadata is invalid")
    if not isinstance(validation.get("timed_out"), bool):
        raise EvidenceSchemaError("validation timeout metadata is invalid")
    if validation.get("error_type") is not None and not isinstance(
        validation.get("error_type"), str
    ):
        raise EvidenceSchemaError("validation error metadata is invalid")
    results_directory = packet.get("results_directory")
    if kind == "failed":
        if results_directory is not None and not _safe_repository_reference(results_directory):
            raise EvidenceSchemaError("results directory metadata is unsafe")
    elif not _safe_repository_reference(results_directory):
        raise EvidenceSchemaError("results directory metadata is unsafe")

    evidence = packet.get("evidence")
    if not isinstance(evidence, list):
        raise EvidenceSchemaError("evidence must be a list")
    if kind == "failed" and evidence:
        raise EvidenceSchemaError("failed evidence packets must be empty")

    identifiers: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise EvidenceSchemaError("evidence items must be objects")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not SAFE_EVIDENCE_ID.fullmatch(identifier):
            raise EvidenceSchemaError("evidence IDs must be safe opaque labels")
        identifiers.append(identifier)
        has_scenario = "scenario" in item
        has_profile = "profile" in item
        if has_scenario == has_profile:
            raise EvidenceSchemaError("evidence items require exactly one identity")
        if kind == "synthetic" and not has_scenario:
            raise EvidenceSchemaError("synthetic evidence must use scenario")
        if kind in {"generic", "comparison"} and not has_profile:
            raise EvidenceSchemaError("generic evidence must use profile")
        identity = item.get("scenario") if has_scenario else item.get("profile")
        if not isinstance(identity, str) or not SAFE_PROFILE.fullmatch(identity):
            raise EvidenceSchemaError("evidence identity is unsafe")
        if (
            not isinstance(item.get("claim"), str)
            or not item["claim"]
            or not isinstance(item.get("metric"), str)
            or not item["metric"]
            or not isinstance(item.get("source_type"), str)
            or not item["source_type"]
            or (item.get("unit") is not None and not isinstance(item.get("unit"), str))
        ):
            raise EvidenceSchemaError("evidence item metadata is invalid")
        if not _safe_repository_reference(item.get("source")):
            raise EvidenceSchemaError("evidence source metadata is unsafe")
        if kind == "comparison" and not _safe_repository_reference(item.get("baseline_source")):
            raise EvidenceSchemaError("baseline evidence source metadata is unsafe")
    if len(identifiers) != len(set(identifiers)):
        raise EvidenceSchemaError("evidence IDs must be unique")

    limitations = packet.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        raise EvidenceSchemaError("limitations must be a nonempty list")
    limitation_ids: list[str] = []
    for limitation in limitations:
        if (
            not isinstance(limitation, dict)
            or set(limitation) != {"id", "statement"}
            or not isinstance(limitation.get("id"), str)
            or not SAFE_EVIDENCE_ID.fullmatch(limitation["id"])
            or not isinstance(limitation.get("statement"), str)
            or not limitation["statement"]
        ):
            raise EvidenceSchemaError("limitation metadata is invalid")
        limitation_ids.append(limitation["id"])
    if len(limitation_ids) != len(set(limitation_ids)) or set(identifiers) & set(limitation_ids):
        raise EvidenceSchemaError("packet identifiers must be unique")
    return kind


def _semantic_evidence(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Resolve required evidence by semantics; IDs are opaque citation labels."""

    if _packet_evidence_kind(packet) != "synthetic":
        raise EvidenceSchemaError("synthetic evidence is required")

    evidence = packet.get("evidence")
    if not isinstance(evidence, list):
        raise EvidenceSchemaError("evidence must be a list")

    resolved: dict[str, dict[str, Any]] = {}
    for name, (metric, scenario, source_type, unit, value_kind) in SYNTHETIC_REQUIRED_EVIDENCE.items():
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


def _generic_semantic_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    """Resolve generic evidence by profile semantics, excluding reserved all."""

    if _packet_evidence_kind(packet) != "generic":
        raise EvidenceSchemaError("generic evidence is required")
    evidence = packet["evidence"]
    count_matches = [
        item
        for item in evidence
        if item.get("metric") == "validated_file_count"
        and item.get("profile") == "all"
        and item.get("source_type") == "validated_result"
        and item.get("unit") == "files"
    ]
    if len(count_matches) != 1:
        raise EvidenceSchemaError("generic validation-count evidence is missing or ambiguous")
    count = count_matches[0]
    if (
        not isinstance(count.get("value"), (int, float))
        or isinstance(count.get("value"), bool)
        or not math.isfinite(count["value"])
        or count["value"] < 1
    ):
        raise EvidenceSchemaError("generic validation-count evidence is invalid")

    profiles = sorted(
        {
            item["profile"]
            for item in evidence
            if item.get("profile") != "all"
            and item.get("metric") in GENERIC_PROFILE_DISCOVERY_METRICS
            and item.get("source_type") in {"validated_aggregate", "validated_metadata"}
            and isinstance(item.get("profile"), str)
            and SAFE_PROFILE.fullmatch(item["profile"])
        }
    )
    if not profiles:
        raise EvidenceSchemaError("generic packet has no reportable profiles")

    resolved_profiles: dict[str, dict[str, dict[str, Any]]] = {}
    for profile in profiles:
        resolved: dict[str, dict[str, Any]] = {}
        for name, (metric, source_type, unit, value_kind) in GENERIC_METRIC_SPECS.items():
            matches = [
                item
                for item in evidence
                if item.get("metric") == metric
                and item.get("profile") == profile
                and item.get("source_type") == source_type
                and item.get("unit") == unit
            ]
            if name == "memory":
                if len(matches) > 1:
                    raise EvidenceSchemaError(f"generic {profile} memory evidence is ambiguous")
                if matches:
                    value = matches[0].get("value")
                    if (
                        not isinstance(value, (int, float))
                        or isinstance(value, bool)
                        or not math.isfinite(value)
                    ):
                        raise EvidenceSchemaError(f"generic {profile} memory evidence is invalid")
                    resolved[name] = matches[0]
                continue
            if len(matches) != 1:
                raise EvidenceSchemaError(
                    f"generic {profile} evidence {name!r} is missing or ambiguous"
                )
            item = matches[0]
            value = item.get("value")
            if value_kind == "number" and (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise EvidenceSchemaError(f"generic {profile} evidence {name!r} must be numeric")
            if value_kind == "memory_status" and value not in GENERIC_MEMORY_STATUSES:
                raise EvidenceSchemaError(f"generic {profile} memory status is invalid")
            if value_kind == "revision_status" and value not in GENERIC_REVISION_STATUSES:
                raise EvidenceSchemaError(f"generic {profile} revision status is invalid")
            resolved[name] = item

        memory_available = resolved["memory_status"]["value"] == "available"
        if memory_available != ("memory" in resolved):
            raise EvidenceSchemaError(
                f"generic {profile} memory metric conflicts with availability"
            )
        resolved_profiles[profile] = resolved

    limitations = packet["limitations"]
    return {"validated_count": count, "profiles": resolved_profiles, "limitations": limitations}


def _comparison_semantic_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    if _packet_evidence_kind(packet) != "comparison":
        raise EvidenceSchemaError("comparison evidence is required")
    if packet.get("schema_version") != 2:
        raise EvidenceSchemaError("comparison packet schema version 2 is required")
    if not _safe_repository_reference(packet.get("baseline_results_directory")):
        raise EvidenceSchemaError("baseline results directory metadata is unsafe")

    def contains_revision_value(value: object) -> bool:
        if isinstance(value, dict):
            return any(
                key in {
                    "source_revision",
                    "revision_value",
                    "baseline_revision",
                    "candidate_revision",
                }
                or contains_revision_value(child)
                for key, child in value.items()
            )
        if isinstance(value, list):
            return any(contains_revision_value(child) for child in value)
        return False

    if contains_revision_value(packet):
        raise EvidenceSchemaError("comparison evidence must not contain revision values")
    validation = packet["validation"]
    for key in ("baseline_file_count",):
        value = validation.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise EvidenceSchemaError("comparison count metadata is invalid")
    if validation.get("policy_status") not in {"passed", "failed"}:
        raise EvidenceSchemaError("comparison policy status is invalid")
    resolved: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in packet["evidence"]:
        if item.get("source_type") != "validated_comparison":
            raise EvidenceSchemaError("comparison source type is invalid")
        key = (item.get("profile"), item.get("metric"))
        if not all(isinstance(part, str) and part for part in key) or key in seen:
            raise EvidenceSchemaError("comparison evidence is missing or ambiguous")
        seen.add(key)
        value = item.get("value")
        required = {
            "baseline", "candidate", "delta", "increase_percent", "maximum",
            "maximum_increase_percent", "absolute_status", "relative_status", "status",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise EvidenceSchemaError("comparison value shape is invalid")
        for name in ("baseline", "candidate", "delta", "maximum", "maximum_increase_percent"):
            number = value[name]
            if not isinstance(number, (int, float)) or isinstance(number, bool) or not math.isfinite(number):
                raise EvidenceSchemaError("comparison numeric evidence is invalid")
        percent = value["increase_percent"]
        if percent is not None and (
            not isinstance(percent, (int, float)) or isinstance(percent, bool) or not math.isfinite(percent)
        ):
            raise EvidenceSchemaError("comparison percentage evidence is invalid")
        for name in ("absolute_status", "relative_status", "status"):
            if value[name] not in {"passed", "failed"}:
                raise EvidenceSchemaError("comparison policy status is invalid")
        resolved.append(item)
    if not resolved:
        raise EvidenceSchemaError("comparison packet has no rules")
    return {"rules": sorted(resolved, key=lambda item: (item["profile"], item["metric"])), "limitations": packet["limitations"]}


def _citation(item: dict[str, Any]) -> str:
    return f"[{item['id']}]"


def _formatted_number(value: int | float, decimal_places: int) -> str:
    return f"{float(value):,.{decimal_places}f}"


def _failure_report() -> str:
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


def _generic_status_sentence(label: str, profile: str, status: str, item: dict[str, Any]) -> str:
    return f"{label} for {profile} was {status} {_citation(item)}."


def _render_generic_fallback(packet: dict[str, Any]) -> str:
    semantic = _generic_semantic_evidence(packet)
    count = semantic["validated_count"]
    capture_label = "capture file" if float(count["value"]) == 1.0 else "capture files"
    profile_lines: list[str] = []
    explanation_lines: list[str] = []
    recommendation_lines: list[str] = []
    for profile, items in semantic["profiles"].items():
        profile_lines.append(
            f"Profile {profile} recorded median p95 process time "
            f"{_formatted_number(items['process']['value'], 6)} ms, median p95 physics-process time "
            f"{_formatted_number(items['physics']['value'], 6)} ms, and median measurement duration "
            f"{_formatted_number(items['duration']['value'], 3)} ms "
            f"{_citation(items['process'])} {_citation(items['physics'])} {_citation(items['duration'])}."
        )
        profile_lines.append(
            f"Profile {profile} recorded median peak object count "
            f"{_formatted_number(items['objects']['value'], 0)}, median peak node count "
            f"{_formatted_number(items['nodes']['value'], 0)}, and median peak orphan-node count "
            f"{_formatted_number(items['orphans']['value'], 0)} "
            f"{_citation(items['objects'])} {_citation(items['nodes'])} {_citation(items['orphans'])}."
        )
        memory_status = items["memory_status"]["value"]
        if memory_status == "available":
            profile_lines.append(
                f"Profile {profile} recorded median peak static memory "
                f"{_formatted_number(items['memory']['value'], 0)} bytes "
                f"{_citation(items['memory'])}; "
                + _generic_status_sentence(
                    "static-memory evidence", profile, memory_status, items["memory_status"]
                )
            )
        else:
            profile_lines.append(
                _generic_status_sentence(
                    "Static-memory evidence", profile, memory_status, items["memory_status"]
                )
            )
        profile_lines.append(
            _generic_status_sentence(
                "Source-revision availability",
                profile,
                items["revision_status"]["value"],
                items["revision_status"],
            )
        )
        explanation_lines.append(
            f"Profile {profile}'s measurements identify controlled comparisons to run next, "
            f"but do not establish a causal defect {_citation(items['process'])} "
            f"{_citation(items['objects'])} {_citation(items['nodes'])}."
        )
        recommendation_lines.append(
            f"- Compare repeated {profile} captures with identical probe settings and host conditions "
            f"{_citation(items['process'])} {_citation(items['physics'])} {_citation(items['duration'])}."
        )
        recommendation_lines.append(
            f"- Measure {profile} object, node, and orphan-node peaks across one controlled change "
            f"{_citation(items['objects'])} {_citation(items['nodes'])} {_citation(items['orphans'])}."
        )
        if memory_status == "available":
            recommendation_lines.append(
                f"- Compare {profile} static-memory captures only with matching measured-frame and "
                f"sampling settings {_citation(items['memory'])} {_citation(items['memory_status'])}."
            )
        else:
            recommendation_lines.append(
                f"- Capture {profile} again in a comparable environment that declares static-memory "
                f"availability {_citation(items['memory_status'])}."
            )
        recommendation_lines.append(
            f"- Capture {profile} with source-revision metadata when correlating future evidence "
            f"{_citation(items['revision_status'])}."
        )

    limitation_lines = [
        f"- {limitation['statement']} [{limitation['id']}]"
        for limitation in semantic["limitations"]
    ]
    return f"""## Validation status
{REPORT_SOURCE_DISCLOSURE}
The validator passed {_formatted_number(count['value'], 0)} generic {capture_label} under its configured checks {_citation(count)}.

## Verified facts
{chr(10).join(profile_lines)}

## Possible explanations
{chr(10).join(explanation_lines)}

## Recommended next investigation
{chr(10).join(recommendation_lines)}

## Remaining uncertainty
{chr(10).join(limitation_lines)}
{REQUIRED_UNCERTAINTY}
"""


def _render_comparison_fallback(packet: dict[str, Any]) -> str:
    semantic = _comparison_semantic_evidence(packet)
    facts: list[str] = []
    recommendations: list[str] = []
    for item in semantic["rules"]:
        value = item["value"]
        percent = (
            "undefined because the baseline was zero"
            if value["increase_percent"] is None
            else f"{_formatted_number(value['increase_percent'], 3)} percent"
        )
        facts.append(
            f"Profile {item['profile']} metric {item['metric']} changed from "
            f"{_formatted_number(value['baseline'], 6)} {item['unit']} to "
            f"{_formatted_number(value['candidate'], 6)} {item['unit']}, a delta of "
            f"{_formatted_number(value['delta'], 6)} {item['unit']} and an increase of "
            f"{percent}; its absolute status was {value['absolute_status']} and its relative "
            f"status was {value['relative_status']} {_citation(item)}."
        )
        recommendations.append(
            f"- Repeat the paired capture for profile {item['profile']} with identical settings "
            f"and compare metric {item['metric']} {_citation(item)}."
        )
    limitation_lines = [
        f"- {item['statement']} [{item['id']}]" for item in semantic["limitations"]
    ]
    return f"""## Validation status
{REPORT_SOURCE_DISCLOSURE}
Both baseline and candidate captures passed deterministic validation; comparison policy status was {packet['validation']['policy_status']} {_citation(semantic['rules'][0])}.

## Verified facts
{chr(10).join(facts)}

## Possible explanations
The paired measurements identify controlled follow-up comparisons but do not establish a causal defect {_citation(semantic['rules'][0])}.

## Recommended next investigation
{chr(10).join(recommendations)}

## Remaining uncertainty
{chr(10).join(limitation_lines)}
{REQUIRED_UNCERTAINTY}
"""


def render_deterministic_fallback(packet: dict[str, Any]) -> str:
    """Render a report using only semantically matched packet evidence."""

    validation = packet.get("validation")
    passed = isinstance(validation, dict) and validation.get("status") == "passed"
    if not passed:
        _packet_evidence_kind(packet)
        return _failure_report()

    kind = _packet_evidence_kind(packet)
    if kind == "generic":
        return _render_generic_fallback(packet)
    if kind == "comparison":
        return _render_comparison_fallback(packet)
    if kind != "synthetic":
        raise EvidenceSchemaError("passed evidence kind is unsupported")

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


MODEL_TEXT_FORBIDDEN = re.compile(
    r"[\r\n#*_`\[\]<>!|/\\%]|\d|"
    r"(?i:\b(?:ms|usec|bytes?|nodes?|objects?|files?|percent)\b)"
)
MODEL_CAUSAL_TERMS = re.compile(
    r"(?i:\b(?:proves?|confirm(?:s|ed)?|caused\s+by|causes?|memory\s+leaks?|leaks?|bottlenecks?)\b)"
)
MODEL_SENSITIVE_TEXT = re.compile(
    r"(?i:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|bearer\s+[A-Za-z0-9._-]+|"
    r"OPENAI_API_KEY|[A-Z]:|\\\\|https?://)"
)


def _model_item_ids_are_valid(evidence_ids: list[str], known_ids: set[str]) -> bool:
    return (
        1 <= len(evidence_ids) <= 4
        and len(evidence_ids) == len(set(evidence_ids))
        and all(identifier in known_ids for identifier in evidence_ids)
    )


def _model_text_is_valid(value: str) -> bool:
    return (
        value == value.strip()
        and 1 <= len(value) <= 240
        and MODEL_TEXT_FORBIDDEN.search(value) is None
        and MODEL_CAUSAL_TERMS.search(value) is None
        and MODEL_SENSITIVE_TEXT.search(value) is None
    )


def accepted_model_contribution(
    output: object,
    packet: dict[str, Any],
) -> tuple[InvestigatorContribution | None, list[str]]:
    """Filter typed model items and require a real accepted recommendation."""

    try:
        contribution = (
            output
            if isinstance(output, InvestigatorContribution)
            else InvestigatorContribution.model_validate(output)
        )
        _packet_evidence_kind(packet)
    except (ValidationError, EvidenceSchemaError):
        return None, ["C01_TYPED_CONTRIBUTION"]

    known_ids = {
        item["id"]
        for item in [*packet["evidence"], *packet["limitations"]]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    errors: set[str] = set()
    hypotheses: list[HypothesisContribution] = []
    for hypothesis in contribution.hypotheses:
        if not _model_item_ids_are_valid(hypothesis.evidence_ids, known_ids):
            errors.add("C02_HYPOTHESIS_EVIDENCE")
            continue
        if not _model_text_is_valid(hypothesis.explanation):
            errors.add("C03_HYPOTHESIS_TEXT")
            continue
        hypotheses.append(hypothesis)

    recommendations: list[RecommendationContribution] = []
    for recommendation in contribution.recommendations:
        if not _model_item_ids_are_valid(recommendation.evidence_ids, known_ids):
            errors.add("C04_RECOMMENDATION_EVIDENCE")
            continue
        recommendations.append(recommendation)

    if not recommendations:
        errors.add("C05_RECOMMENDATION_REQUIRED")
        return None, sorted(errors)
    return InvestigatorContribution(
        hypotheses=hypotheses,
        recommendations=recommendations,
    ), sorted(errors)


RECOMMENDATION_TEMPLATES = {
    RecommendationAction.COMPARE: "Compare a controlled repeat against the cited evidence",
    RecommendationAction.INSPECT: "Inspect the collection conditions represented by the cited evidence",
    RecommendationAction.MEASURE: "Measure the cited metrics again under controlled conditions",
    RecommendationAction.PROFILE: "Profile the execution interval represented by the cited evidence",
    RecommendationAction.VALIDATE: "Validate a comparable result set against the same configured checks",
    RecommendationAction.CAPTURE: "Capture another comparable run for the cited evidence",
    RecommendationAction.REPEAT_CAPTURE: "Re-run a comparable capture with identical settings",
}


def _item_citations(evidence_ids: list[str]) -> str:
    return " ".join(f"[{identifier}]" for identifier in evidence_ids)


def render_model_contribution(
    packet: dict[str, Any],
    contribution: InvestigatorContribution,
) -> str:
    """Render accepted model choices inside deterministic report sections."""

    base = render_deterministic_fallback(packet)
    sections = _report_sections(base)
    if sections is None:
        raise EvidenceSchemaError("deterministic report sections are invalid")

    validation_status = sections["## Validation status"].replace(
        REPORT_SOURCE_DISCLOSURE,
        MODEL_REPORT_SOURCE_DISCLOSURE,
        1,
    )
    if contribution.hypotheses:
        explanations = "\n".join(
            f"Hypothesis: {item.explanation} {_item_citations(item.evidence_ids)}."
            for item in contribution.hypotheses
        )
    else:
        explanations = "No model-authored hypothesis was accepted."
    recommendations = "\n".join(
        f"- {RECOMMENDATION_TEMPLATES[item.action]} {_item_citations(item.evidence_ids)}."
        for item in contribution.recommendations
    )
    return f"""## Validation status
{validation_status}

## Verified facts
{sections['## Verified facts']}

## Possible explanations
{explanations}

## Recommended next investigation
{recommendations}

## Remaining uncertainty
{sections['## Remaining uncertainty']}
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


def _validate_synthetic_grounded_report(report: str, packet: dict[str, Any]) -> list[str]:
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
                    and content not in {REPORT_SOURCE_DISCLOSURE, MODEL_REPORT_SOURCE_DISCLOSURE}
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


def _validate_generic_grounded_report(report: str, packet: dict[str, Any]) -> list[str]:
    """Validate a generic-profile report against its exact packet evidence."""

    errors: set[str] = set()
    sections = _report_sections(report)
    if sections is None:
        return ["G01_REPORT_SECTIONS"]
    try:
        semantic = _generic_semantic_evidence(packet)
    except EvidenceSchemaError:
        return ["G15_EVIDENCE_SCHEMA"]

    evidence_items = packet["evidence"]
    limitations = semantic["limitations"]
    by_id = {item["id"]: item for item in evidence_items}
    by_id.update({item["id"]: item for item in limitations})
    citations = EVIDENCE_CITATION.findall(report)
    if any(citation not in by_id for citation in citations):
        errors.add("G02_UNKNOWN_EVIDENCE")

    required_ids = {semantic["validated_count"]["id"]}
    for items in semantic["profiles"].values():
        required_ids.update(item["id"] for item in items.values())
    required_ids.update(item["id"] for item in limitations)
    if not required_ids.issubset(set(citations)):
        errors.add("G03_REQUIRED_EVIDENCE_MISSING")

    lowered = report.lower()
    if re.search(r"\bprofile\s+[`\"']?all\b", lowered):
        errors.add("G26_RESERVED_PROFILE")
    for profile, items in semantic["profiles"].items():
        if profile.lower() not in lowered:
            errors.add("G17_PROFILE_COVERAGE")
        memory_status = items["memory_status"]["value"]
        memory_sentence = f"static-memory evidence for {profile} was {memory_status}"
        if memory_sentence.lower() not in lowered:
            errors.add("G18_MEMORY_AVAILABILITY")
        revision_status = items["revision_status"]["value"]
        revision_sentence = f"source-revision availability for {profile} was {revision_status}"
        if revision_sentence.lower() not in lowered:
            errors.add("G19_REVISION_AVAILABILITY")
        if memory_status != "available":
            for line in report.splitlines():
                normalized_line = line.lower().replace("static-memory", "static memory")
                if profile.lower() in normalized_line and "static memory" in normalized_line and "bytes" in normalized_line:
                    errors.add("G20_INVENTED_MEMORY")

    for limitation in limitations:
        if limitation["statement"] not in report:
            errors.add("G21_GENERIC_LIMITATION_MISSING")
    if REQUIRED_UNCERTAINTY not in sections["## Remaining uncertainty"]:
        errors.add("G08_REQUIRED_UNCERTAINTY")

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
        if numbers and cited_items and any(
            not _supported_number(number, cited_items) for number in numbers
        ):
            errors.add("G07_UNSUPPORTED_NUMBER")

    for heading in ("## Validation status", "## Verified facts"):
        for line in sections[heading].splitlines():
            content = line.strip().lstrip("-* ")
            if (
                content
                and content not in {REPORT_SOURCE_DISCLOSURE, MODEL_REPORT_SOURCE_DISCLOSURE}
                and not EVIDENCE_CITATION.search(content)
            ):
                errors.add("G14_UNCITED_VERIFIED_FACT")

    for synthetic_term in (
        "healthy",
        "node_leak",
        "cpu_spike",
        "workload_time_usec",
        "retained nodes",
        "scenario-owned",
    ):
        if synthetic_term in lowered:
            errors.add("G22_SYNTHETIC_CLAIM")

    limitation_stripped = report
    for limitation in limitations:
        limitation_stripped = limitation_stripped.replace(limitation["statement"], "")
    if re.search(
        r"\b(proves?|confirms?|demonstrates?|shows?|is|was|caused by)\b.{0,50}\b(bottleneck|memory leak|leak|causal defect)\b",
        limitation_stripped,
        flags=re.IGNORECASE,
    ):
        errors.add("G23_UNSUPPORTED_GENERIC_CAUSE")
    for phrase in BANNED_SPECULATION:
        if phrase in limitation_stripped.lower():
            errors.add("G09_UNSUPPORTED_CAUSE")

    revision_stripped = limitation_stripped
    for profile, items in semantic["profiles"].items():
        allowed = (
            f"Source-revision availability for {profile} was "
            f"{items['revision_status']['value']} {_citation(items['revision_status'])}."
        )
        revision_stripped = revision_stripped.replace(allowed, "")
        allowed_recommendation = (
            f"- Capture {profile} with source-revision metadata when correlating future evidence "
            f"{_citation(items['revision_status'])}."
        )
        revision_stripped = revision_stripped.replace(allowed_recommendation, "")
    if "revision" in revision_stripped.lower():
        errors.add("G24_REVISION_VALUE_OR_EQUALITY")

    recommendations = sections["## Recommended next investigation"]
    for line in recommendations.splitlines():
        content = line.strip().lstrip("-* ")
        if not content:
            continue
        if not EVIDENCE_CITATION.search(content):
            errors.add("G11_UNCITED_RECOMMENDATION")
        if re.search(r"\b(modify|edit|delete|overwrite|repair|fix|write)\b", content.lower()):
            errors.add("G12_MUTATING_RECOMMENDATION")
        if not re.search(
            r"\b(inspect|compare|measure|profile|validate|review|run|re-run|separate|capture)\b",
            content.lower(),
        ):
            errors.add("G13_UNTESTABLE_RECOMMENDATION")

    sensitive_patterns = (
        r"(?i)(?:^|[\s(\"'])\b[A-Z]:[\\/]",
        r"(?i)(?:^|\s)\\\\[^\s]+",
        r"(?i)/(?:users|home)/[^\s]+",
        r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}",
        r"(?i)bearer\s+[A-Za-z0-9._-]+",
        r"OPENAI_API_KEY\s*=\s*\S+",
    )
    if any(re.search(pattern, report, flags=re.MULTILINE) for pattern in sensitive_patterns):
        errors.add("G25_SENSITIVE_OUTPUT")
    return sorted(errors)


def validate_grounded_report(report: str, packet: dict[str, Any]) -> list[str]:
    """Dispatch grounding validation from explicit packet evidence kind."""

    try:
        kind = _packet_evidence_kind(packet)
    except EvidenceSchemaError:
        return ["G15_EVIDENCE_SCHEMA"]
    if kind == "generic":
        return _validate_generic_grounded_report(report, packet)
    if kind == "comparison":
        try:
            semantic = _comparison_semantic_evidence(packet)
        except EvidenceSchemaError:
            return ["G15_EVIDENCE_SCHEMA"]
        errors: set[str] = set()
        sections = _report_sections(report)
        if sections is None:
            return ["G01_REPORT_SECTIONS"]
        known = {item["id"]: item for item in semantic["rules"]}
        known.update({item["id"]: item for item in semantic["limitations"]})
        citations = EVIDENCE_CITATION.findall(report)
        if any(item not in known for item in citations):
            errors.add("G02_UNKNOWN_EVIDENCE")
        required = set(known)
        if not required.issubset(citations):
            errors.add("G03_REQUIRED_EVIDENCE_MISSING")
        lowered = report.lower()
        for item in semantic["rules"]:
            if item["profile"].lower() not in lowered or item["metric"].lower() not in lowered:
                errors.add("G17_PROFILE_COVERAGE")
        for limitation in semantic["limitations"]:
            if limitation["statement"] not in report:
                errors.add("G21_GENERIC_LIMITATION_MISSING")
        if REQUIRED_UNCERTAINTY not in sections["## Remaining uncertainty"]:
            errors.add("G08_REQUIRED_UNCERTAINTY")
        causal_scan = report
        for limitation in semantic["limitations"]:
            causal_scan = causal_scan.replace(limitation["statement"], "")
        if re.search(r"\b(proves?|confirmed|caused by|causes|memory leak|leak|bottleneck)\b", causal_scan.lower()):
            errors.add("G23_UNSUPPORTED_GENERIC_CAUSE")
        if re.search(r"\brevision\b.{0,40}\b(?:equal|same|value|[0-9a-f]{7,40})\b", lowered):
            errors.add("G24_REVISION_VALUE_OR_EQUALITY")
        for line in report.splitlines():
            if line.startswith("##"):
                continue
            line_citations = EVIDENCE_CITATION.findall(line)
            numeric_text = EVIDENCE_CITATION.sub("", line)
            numbers = re.findall(
                r"(?<![A-Za-z_0-9])[-+]?\d[\d,]*(?:\.\d+)?",
                numeric_text,
            )
            if numbers and not line_citations:
                errors.add("G06_UNCITED_NUMBER")
            cited_items = [known[citation] for citation in line_citations if citation in known]
            if numbers and cited_items and any(
                not _supported_number(number, cited_items) for number in numbers
            ):
                errors.add("G07_UNSUPPORTED_NUMBER")
        for line in sections["## Recommended next investigation"].splitlines():
            content = line.strip().lstrip("-* ")
            if not content:
                continue
            if not EVIDENCE_CITATION.search(content):
                errors.add("G11_UNCITED_RECOMMENDATION")
            if re.search(r"\b(modify|edit|delete|overwrite|repair|fix|write)\b", content.lower()):
                errors.add("G12_MUTATING_RECOMMENDATION")
            if not re.search(
                r"\b(inspect|compare|measure|profile|validate|review|run|re-run|capture|repeat)\b",
                content.lower(),
            ):
                errors.add("G13_UNTESTABLE_RECOMMENDATION")
        if re.search(r"(?i)(?:^|[\s(\"'])\b[A-Z]:[\\/]|sk-(?:proj-)?[A-Za-z0-9_-]{20,}", report):
            errors.add("G25_SENSITIVE_OUTPUT")
        return sorted(errors)
    return _validate_synthetic_grounded_report(report, packet)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interpret existing Godot benchmark results without modifying them."
    )
    parser.add_argument(
        "--workspace-root",
        help="explicit workspace root for repository-relative generic captures",
    )
    parser.add_argument("--baseline-results")
    parser.add_argument("--budget-file")
    parser.add_argument(
        "results_directory",
        help="Repository-relative directory containing benchmark result JSON files",
    )
    return parser


def _emit_deterministic_fallback(packet: dict[str, Any], rule_ids: list[str]) -> int:
    """Render and verify fallback without exposing rejected model content."""

    print(
        f"WARNING: model contribution failed ({','.join(rule_ids)}); "
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
    print(report)
    return 0 if packet["validation"].get("status") == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    global ACTIVE_WORKSPACE_ROOT, ACTIVE_BASELINE_RESULTS, ACTIVE_BUDGET_FILE
    args = _argument_parser().parse_args(argv)
    ACTIVE_BASELINE_RESULTS = None
    ACTIVE_BUDGET_FILE = None

    try:
        ACTIVE_WORKSPACE_ROOT = resolve_workspace_root(args.workspace_root)
        _resolved, relative_directory, _count = resolve_results_directory(
            args.results_directory,
            ACTIVE_WORKSPACE_ROOT,
        )
        relative_baseline = None
        relative_budget = None
        if args.baseline_results is not None or args.budget_file is not None:
            if args.baseline_results is None or args.budget_file is None:
                raise ValueError("Baseline results and budget file must be supplied together.")
            _base, relative_baseline, _base_count = resolve_results_directory(
                args.baseline_results, ACTIVE_WORKSPACE_ROOT
            )
            supplied_budget = Path(args.budget_file)
            if supplied_budget.is_absolute() or supplied_budget.drive or supplied_budget.anchor:
                raise ValueError("The budget file must be workspace-relative.")
            resolved_budget = (ACTIVE_WORKSPACE_ROOT / supplied_budget).resolve(strict=True)
            relative_budget = resolved_budget.relative_to(ACTIVE_WORKSPACE_ROOT).as_posix()
            if not resolved_budget.is_file() or resolved_budget.suffix.lower() != ".json":
                raise ValueError("The budget file must be a JSON file.")
            ACTIVE_BASELINE_RESULTS = relative_baseline
            ACTIVE_BUDGET_FILE = relative_budget
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
    if relative_baseline is not None:
        prompt += (
            f" Compare it with baseline directory {relative_baseline!r} under "
            f"budget file {relative_budget!r}."
        )
    hooks = EvidenceCaptureHooks()
    try:
        result = Runner.run_sync(build_investigator(), prompt, hooks=hooks)
    except RateLimitError as error:
        print(format_rate_limit_error(error), file=sys.stderr)
        return 1
    except ModelBehaviorError:
        packet = hooks.recovered_packet()
        if packet is None:
            print("ERROR: investigator grounding failed (G00_EVIDENCE_PACKET).", file=sys.stderr)
            return 1
        return _emit_deterministic_fallback(packet, ["C01_TYPED_CONTRIBUTION"])
    except Exception as error:  # The CLI must fail safely without exposing request details.
        print(f"ERROR: investigator run failed ({type(error).__name__}).", file=sys.stderr)
        return 1

    packet = extract_evidence_packet(result)
    if packet is None:
        print("ERROR: investigator grounding failed (G00_EVIDENCE_PACKET).", file=sys.stderr)
        return 1
    if packet["validation"].get("status") != "passed":
        return _emit_deterministic_fallback(packet, ["C06_VALIDATION_FAILED"])

    contribution, contribution_errors = accepted_model_contribution(
        result.final_output,
        packet,
    )
    if contribution is None:
        return _emit_deterministic_fallback(packet, contribution_errors)
    if contribution_errors:
        print(
            f"WARNING: discarded model items ({','.join(contribution_errors)}).",
            file=sys.stderr,
        )

    try:
        report = render_model_contribution(packet, contribution)
    except EvidenceSchemaError:
        return _emit_deterministic_fallback(packet, ["C07_MODEL_RENDER"])
    grounding_errors = validate_grounded_report(report, packet)
    if grounding_errors:
        return _emit_deterministic_fallback(packet, grounding_errors)

    validation = packet.get("validation", {})
    print(report)
    return 0 if validation.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
