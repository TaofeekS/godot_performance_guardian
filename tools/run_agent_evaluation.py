"""Run or verify the frozen Experiment 19 paired agent evaluation."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Any, AsyncIterator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from agents import (
    Agent,
    ModelBehaviorError,
    ModelRetrySettings,
    ModelSettings,
    RunConfig,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from agents.models.openai_responses import OpenAIResponsesModel
from agents.models.interface import Model
from openai import APIError, AsyncOpenAI

from agent import investigator


PACKAGE_ROOT = REPOSITORY_ROOT / "evaluation" / "agent"
CONFIG_PATH = PACKAGE_ROOT / "config.json"
CASES_PATH = PACKAGE_ROOT / "cases.json"
INTEGRITY_PATH = PACKAGE_ROOT / "integrity.json"
TYPED_PROMPT_PATH = PACKAGE_ROOT / "prompts" / "typed.txt"
FREE_FORM_PROMPT_PATH = PACKAGE_ROOT / "prompts" / "free_form.txt"
TYPED_SCHEMA_PATH = PACKAGE_ROOT / "typed-schema.json"
DEFAULT_RESULT_PATH = PACKAGE_ROOT / "results" / "agent-evaluation.json"
SAFE_RULE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
FAILED_RULE_GRADER_VERSION = 1


class AgentEvaluationError(RuntimeError):
    """A safe evaluation configuration or operational failure."""


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _normalized_text_bytes(path: Path) -> bytes:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise AgentEvaluationError(f"frozen component is unreadable: {path.relative_to(REPOSITORY_ROOT).as_posix()}") from error
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_integrity() -> dict[str, Any]:
    try:
        manifest = json.loads(INTEGRITY_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AgentEvaluationError("agent evaluation integrity manifest is invalid") from error
    if set(manifest) != {"schema_version", "hash_mode", "files"}:
        raise AgentEvaluationError("agent evaluation integrity manifest shape is invalid")
    if manifest["schema_version"] != 1 or manifest["hash_mode"] != "sha256_utf8_lf":
        raise AgentEvaluationError("agent evaluation integrity mode is unsupported")
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        raise AgentEvaluationError("agent evaluation integrity members are missing")
    for relative, expected in sorted(files.items()):
        if not isinstance(relative, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise AgentEvaluationError("agent evaluation integrity member is invalid")
        path = (REPOSITORY_ROOT / relative).resolve()
        try:
            path.relative_to(REPOSITORY_ROOT.resolve())
        except ValueError as error:
            raise AgentEvaluationError("agent evaluation integrity path escaped the repository") from error
        if not path.is_file() or _sha256(_normalized_text_bytes(path)) != expected:
            raise AgentEvaluationError(f"integrity mismatch for {relative}")
    return manifest


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AgentEvaluationError(f"invalid frozen JSON: {path.relative_to(REPOSITORY_ROOT).as_posix()}") from error


def load_frozen_evaluation() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    config = _load_json(CONFIG_PATH)
    cases_document = _load_json(CASES_PATH)
    prompts = {
        "typed": TYPED_PROMPT_PATH.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n"),
        "free_form": FREE_FORM_PROMPT_PATH.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n"),
    }
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise AgentEvaluationError("agent evaluation configuration is invalid")
    cases = cases_document.get("cases") if isinstance(cases_document, dict) else None
    if not isinstance(cases, list) or len(cases) != 10:
        raise AgentEvaluationError("exactly ten frozen agent cases are required")
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != 10 or len(set(ids)) != 10:
        raise AgentEvaluationError("agent case identifiers are invalid")
    expected_order = config.get("execution_order")
    if expected_order != [
        {"case_id": case["id"], "variants": (["free_form", "typed"] if index % 2 == 1 else ["typed", "free_form"])}
        for index, case in enumerate(cases, start=1)
    ]:
        raise AgentEvaluationError("agent execution order is invalid")
    for case in cases:
        packet_path = case.get("packet_path")
        if not isinstance(packet_path, str):
            raise AgentEvaluationError(f"case {case.get('id')} has no packet path")
        resolved_packet = (REPOSITORY_ROOT / packet_path).resolve()
        try:
            resolved_packet.relative_to(PACKAGE_ROOT.resolve())
        except ValueError as error:
            raise AgentEvaluationError(f"case {case.get('id')} packet escaped the package") from error
        packet = _load_json(resolved_packet)
        if not isinstance(packet, dict) or investigator._packet_evidence_kind(packet) != "comparison":
            raise AgentEvaluationError(f"case {case.get('id')} has invalid comparison evidence")
        investigator._comparison_semantic_evidence(packet)
        if packet.get("validation", {}).get("policy_status") != "failed":
            raise AgentEvaluationError(f"case {case.get('id')} is not a failure packet")
        case["packet"] = packet
    return config, cases, prompts


def observed_request_cost(
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
    rate_card: dict[str, float],
) -> float:
    values = (input_tokens, cached_input_tokens, output_tokens)
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
        raise AgentEvaluationError("model usage is missing or invalid")
    if cached_input_tokens > input_tokens:
        raise AgentEvaluationError("cached input tokens exceed total input tokens")
    uncached = input_tokens - cached_input_tokens
    return (
        uncached * rate_card["uncached_input_per_million"]
        + cached_input_tokens * rate_card["cached_input_per_million"]
        + output_tokens * rate_card["output_per_million"]
    ) / 1_000_000


def conservative_next_cost(input_bound: int, config: dict[str, Any]) -> float:
    return (
        input_bound * config["rate_card_usd_per_million_tokens"]["uncached_input_per_million"]
        + config["max_output_tokens_per_run"]
        * config["rate_card_usd_per_million_tokens"]["output_per_million"]
    ) / 1_000_000


def conservative_input_bound(
    *, config: dict[str, Any], case: dict[str, Any], prompt: str, variant: str
) -> int:
    frozen_material = {
        "prompt": prompt,
        "packet": case["packet"],
        "typed_schema": _load_json(TYPED_SCHEMA_PATH) if variant == "typed" else None,
        "tool": {
            "name": "validate_benchmark_results",
            "arguments": {"case_id": case["id"]},
        },
        "two_turn_material": [case["id"], variant, config["model_snapshot"]],
    }
    return len(_canonical_bytes(frozen_material)) + config["protocol_input_margin_tokens"]


def failed_rule_ids(packet: dict[str, Any]) -> list[str]:
    semantic = investigator._comparison_semantic_evidence(packet)
    return sorted(item["id"] for item in semantic["rules"] if item["value"]["status"] == "failed")


def evaluation_grade(report: str, packet: dict[str, Any]) -> list[str]:
    """Apply the production grounder plus failure-specific actionability rules."""

    errors = set(investigator.validate_grounded_report(report, packet))
    sections = investigator._report_sections(report)
    if sections is None:
        return sorted(errors | {"E01_REPORT_SECTIONS"})
    failed = failed_rule_ids(packet)
    facts = sections["## Verified facts"]
    recommendations = sections["## Recommended next investigation"]
    for identifier in failed:
        if f"[{identifier}]" not in facts:
            errors.add("E02_FAILED_RULE_FACT_MISSING")
    recommendation_lines = [line.strip() for line in recommendations.splitlines() if line.strip().startswith("-")]
    if not any(any(f"[{identifier}]" in line for identifier in failed) for line in recommendation_lines):
        errors.add("E03_FAILED_RULE_RECOMMENDATION")
    if not any(
        any(f"[{identifier}]" in line for identifier in failed)
        and "profile " in line.lower()
        and "metric " in line.lower()
        and re.search(r"\b(compare|inspect|measure|profile|validate|capture|repeat)\b", line.lower())
        and re.search(r"\b(controlled|identical|same|comparable)\b", line.lower())
        for line in recommendation_lines
    ):
        errors.add("E04_RECOMMENDATION_NOT_SPECIFIC")
    return sorted(errors)


def _accepted_typed(
    output: object, packet: dict[str, Any]
) -> tuple[str | None, list[str], list[dict[str, Any]]]:
    contribution, contribution_errors = investigator.accepted_model_contribution(output, packet)
    if contribution is None:
        return None, contribution_errors, []
    report = investigator.render_model_contribution(packet, contribution)
    grade = evaluation_grade(report, packet)
    if grade:
        return None, sorted(set(contribution_errors + grade)), []
    actions = [item.model_dump(mode="json") for item in contribution.recommendations]
    return report, contribution_errors, actions


def _accepted_free_form(output: object, packet: dict[str, Any]) -> tuple[str | None, list[str]]:
    if not isinstance(output, str):
        return None, ["E05_FREE_FORM_OUTPUT"]
    errors = evaluation_grade(output, packet)
    return (output, []) if not errors else (None, errors)


def _raw_output_hash(value: object) -> str:
    if isinstance(value, str):
        data = value.encode("utf-8")
    elif hasattr(value, "model_dump"):
        data = _canonical_bytes(value.model_dump(mode="json"))
    else:
        data = _canonical_bytes(value)
    return _sha256(data)


class TwoTurnModel(Model):
    """Enforce the frozen per-turn output split and retain usage only."""

    def __init__(self, delegate: OpenAIResponsesModel, token_split: list[int]) -> None:
        self.delegate = delegate
        self.token_split = token_split
        self.request_count = 0
        self.responses: list[Any] = []

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        if self.request_count >= len(self.token_split):
            raise ModelBehaviorError("evaluation model request limit exceeded")
        model_settings = kwargs.get("model_settings")
        positional = list(args)
        if model_settings is None and len(positional) >= 3:
            model_settings = positional[2]
            positional[2] = replace(model_settings, max_tokens=self.token_split[self.request_count])
        else:
            kwargs["model_settings"] = replace(model_settings, max_tokens=self.token_split[self.request_count])
        self.request_count += 1
        response = await self.delegate.get_response(*positional, **kwargs)
        self.responses.append(response)
        return response

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise ModelBehaviorError("streaming is disabled for the frozen evaluation")
        yield  # pragma: no cover


def _make_packet_tool(packet: dict[str, Any], case_id: str, counter: dict[str, int]) -> Any:
    @function_tool(
        name_override="validate_benchmark_results",
        description_override="Return the one frozen, deterministically validated comparison packet for this evaluation case.",
    )
    def packet_tool(requested_case_id: str) -> dict[str, Any]:
        counter["calls"] += 1
        if requested_case_id != case_id:
            raise ValueError("the requested case identifier did not match the frozen case")
        return packet

    return packet_tool


def _model_settings(config: dict[str, Any]) -> ModelSettings:
    return ModelSettings(
        tool_choice="required",
        parallel_tool_calls=False,
        store=False,
        include_usage=True,
        preserve_raw_usage=True,
        timeout=config["request_timeout_seconds"],
        retry=ModelRetrySettings(max_retries=0),
    )


def _usage_from_responses(responses: list[Any], rate_card: dict[str, float]) -> dict[str, Any]:
    request_entries: list[dict[str, Any]] = []
    for response in responses:
        usage = getattr(response, "usage", None)
        if usage is None or not isinstance(getattr(usage, "input_tokens", None), int):
            raise AgentEvaluationError("complete model usage was not returned")
        cached = int(getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0)
        entry = {
            "input_tokens": usage.input_tokens,
            "cached_input_tokens": cached,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        }
        entry["estimated_cost_usd"] = observed_request_cost(
            entry["input_tokens"], entry["cached_input_tokens"], entry["output_tokens"], rate_card
        )
        request_entries.append(entry)
    totals = {
        "model_requests": len(request_entries),
        "input_tokens": sum(item["input_tokens"] for item in request_entries),
        "cached_input_tokens": sum(item["cached_input_tokens"] for item in request_entries),
        "output_tokens": sum(item["output_tokens"] for item in request_entries),
        "total_tokens": sum(item["total_tokens"] for item in request_entries),
        "estimated_cost_usd": sum(item["estimated_cost_usd"] for item in request_entries),
        "requests": request_entries,
    }
    return totals


def _last_raw_response_hash(model: TwoTurnModel) -> str | None:
    if not model.responses:
        return None
    output = getattr(model.responses[-1], "output", None)
    serializable = [item.model_dump(mode="json") if hasattr(item, "model_dump") else str(type(item).__name__) for item in (output or [])]
    return _sha256(_canonical_bytes(serializable))


def run_one_agent(
    *,
    client: AsyncOpenAI,
    config: dict[str, Any],
    case: dict[str, Any],
    variant: str,
    prompt: str,
) -> dict[str, Any]:
    counter = {"calls": 0}
    tool = _make_packet_tool(case["packet"], case["id"], counter)
    delegate = OpenAIResponsesModel(model=config["model_snapshot"], openai_client=client)
    bounded_model = TwoTurnModel(delegate, config["output_token_split"])
    output_type: object = investigator.InvestigatorContribution if variant == "typed" else str
    agent = Agent(
        name=("Grounded Typed Investigator" if variant == "typed" else "Matched Free-Form Investigator"),
        instructions=prompt,
        model=bounded_model,
        tools=[tool],
        output_type=output_type,
        model_settings=_model_settings(config),
        tool_use_behavior="run_llm_again",
        reset_tool_choice=True,
    )
    started = time.perf_counter_ns()
    result: Any = None
    behavior_error = False
    try:
        result = Runner.run_sync(
            agent,
            f"Investigate frozen case {case['id']}. Call validate_benchmark_results with requested_case_id set to {case['id']}.",
            max_turns=2,
            run_config=RunConfig(
                tracing_disabled=True,
                trace_include_sensitive_data=False,
                workflow_name="Frozen grounded-agent evaluation",
            ),
        )
    except ModelBehaviorError:
        behavior_error = True
    except (APIError, TimeoutError, asyncio.TimeoutError, OSError) as error:
        raise AgentEvaluationError(f"live model request failed safely: {type(error).__name__}") from None
    latency_ms = (time.perf_counter_ns() - started) / 1_000_000
    usage = _usage_from_responses(bounded_model.responses, config["rate_card_usd_per_million_tokens"])
    final_output = getattr(result, "final_output", None)
    direct_report: str | None = None
    grader_ids: list[str] = []
    accepted_actions: list[dict[str, Any]] = []
    if not behavior_error and counter["calls"] == 1 and usage["model_requests"] == 2:
        if variant == "typed":
            direct_report, grader_ids, accepted_actions = _accepted_typed(final_output, case["packet"])
        else:
            direct_report, grader_ids = _accepted_free_form(final_output, case["packet"])
    else:
        if counter["calls"] != 1:
            grader_ids.append("E06_PACKET_TOOL_COUNT")
        if usage["model_requests"] != 2:
            grader_ids.append("E07_MODEL_REQUEST_COUNT")
        if behavior_error:
            grader_ids.append("E08_MODEL_BEHAVIOR")
    fallback_report = None
    fallback_errors: list[str] = []
    rejected_hash = None
    if direct_report is None:
        if final_output is not None:
            rejected_hash = _raw_output_hash(final_output)
        else:
            rejected_hash = _last_raw_response_hash(bounded_model)
        fallback_report = investigator.render_deterministic_fallback(case["packet"])
        fallback_errors = evaluation_grade(fallback_report, case["packet"])
        if fallback_errors:
            raise AgentEvaluationError("deterministic fallback failed frozen grounding")
    return {
        "variant": variant,
        "direct_status": "accepted" if direct_report is not None else "rejected",
        "grader_rule_ids": sorted(set(grader_ids)),
        "direct_report": direct_report,
        "fallback_status": "not_needed" if direct_report is not None else "grounded",
        "fallback_report": fallback_report,
        "rejected_report_sha256": rejected_hash,
        "accepted_actions": accepted_actions,
        "agent_runs": 1,
        "tool_calls": counter["calls"],
        "latency_ms": round(latency_ms, 3),
        "usage": usage,
    }


def _nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, min(len(ordered), math.ceil(percentile * len(ordered))))
    return ordered[rank - 1]


def recompute_summary(result: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    runs = [run for case in result.get("cases", []) for run in case.get("runs", [])]
    typed = [run for run in runs if run.get("variant") == "typed"]
    free = [run for run in runs if run.get("variant") == "free_form"]
    typed_passes = sum(run.get("direct_status") == "accepted" for run in typed)
    free_passes = sum(run.get("direct_status") == "accepted" for run in free)
    pairs = {"both_passed": 0, "typed_passed_free_form_failed": 0, "free_form_passed_typed_failed": 0, "both_failed": 0}
    for case in result.get("cases", []):
        by_variant = {run["variant"]: run for run in case["runs"]}
        typed_ok = by_variant["typed"]["direct_status"] == "accepted"
        free_ok = by_variant["free_form"]["direct_status"] == "accepted"
        key = "both_passed" if typed_ok and free_ok else "typed_passed_free_form_failed" if typed_ok else "free_form_passed_typed_failed" if free_ok else "both_failed"
        pairs[key] += 1
    latencies = [float(run["latency_ms"]) for run in runs]
    total_cost = sum(float(run["usage"]["estimated_cost_usd"]) for run in runs)
    target = (
        len(typed) == 10
        and len(free) == 10
        and typed_passes >= config["success_criteria"]["typed_minimum_direct_passes"]
        and typed_passes - free_passes >= config["success_criteria"]["minimum_typed_advantage"]
        and all(run["fallback_status"] == "grounded" for run in typed if run["direct_status"] == "rejected")
    )
    return {
        "agent_runs": len(runs),
        "model_requests": sum(run["usage"]["model_requests"] for run in runs),
        "tool_calls": sum(run["tool_calls"] for run in runs),
        "input_tokens": sum(run["usage"]["input_tokens"] for run in runs),
        "cached_input_tokens": sum(run["usage"]["cached_input_tokens"] for run in runs),
        "output_tokens": sum(run["usage"]["output_tokens"] for run in runs),
        "total_tokens": sum(run["usage"]["total_tokens"] for run in runs),
        "estimated_cost_usd": total_cost,
        "typed_direct_passes": typed_passes,
        "free_form_direct_passes": free_passes,
        "typed_grounded_fallbacks": sum(run["fallback_status"] == "grounded" for run in typed),
        "paired_outcomes": pairs,
        "median_latency_ms": statistics.median(latencies) if latencies else None,
        "p95_latency_ms": _nearest_rank(latencies, 0.95) if latencies else None,
        "success_criteria_met": target,
    }


def _headline(summary: dict[str, Any]) -> str:
    return (
        "Across ten fixed performance-failure packets, the grounded typed agent produced "
        f"directly accepted safe, actionable reports on {summary['typed_direct_passes']}/10 cases "
        f"versus {summary['free_form_direct_passes']}/10 for the matched free-form baseline; "
        f"deterministic fallback safely covered {summary['typed_grounded_fallbacks']} rejected typed cases."
    )


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise AgentEvaluationError("the evaluation output already exists")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(_canonical_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def _base_result(config: dict[str, Any], integrity: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_type": "grounded_agent_evaluation",
        "schema_version": 1,
        "status": "incomplete",
        "model_snapshot": config["model_snapshot"],
        "integrity": {"schema_version": integrity["schema_version"], "hash_mode": integrity["hash_mode"], "manifest_sha256": _sha256(_normalized_text_bytes(INTEGRITY_PATH))},
        "configuration": {
            "case_count": 10,
            "variant_count": 2,
            "max_output_tokens_per_run": config["max_output_tokens_per_run"],
            "output_token_split": config["output_token_split"],
            "estimated_cost_ceiling_usd": config["estimated_cost_ceiling_usd"],
            "rate_card_usd_per_million_tokens": config["rate_card_usd_per_million_tokens"],
            "tracing_disabled": True,
            "client_max_retries": 0,
            "model_max_retries": 0,
        },
        "cases": [],
        "summary": None,
        "headline": None,
        "incomplete_reason": None,
    }


def run_live(output_path: Path) -> int:
    integrity = verify_integrity()
    config, cases, prompts = load_frozen_evaluation()
    result = _base_result(config, integrity)
    if output_path.exists():
        raise AgentEvaluationError("the evaluation output already exists")
    if not os.environ.get("OPENAI_API_KEY"):
        result["incomplete_reason"] = "missing_api_key"
        _atomic_write(output_path, result)
        return 2
    set_tracing_disabled(True)
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0, timeout=config["request_timeout_seconds"])
    observed_cost = 0.0
    try:
        for case in cases:
            case_result = {"case_id": case["id"], "title": case["title"], "failed_evidence_ids": failed_rule_ids(case["packet"]), "runs": []}
            result["cases"].append(case_result)
            order = next(item["variants"] for item in config["execution_order"] if item["case_id"] == case["id"])
            for variant in order:
                bound = conservative_input_bound(config=config, case=case, prompt=prompts[variant], variant=variant)
                if observed_cost + conservative_next_cost(bound, config) > config["estimated_cost_ceiling_usd"]:
                    result["incomplete_reason"] = "cost_preflight"
                    _atomic_write(output_path, result)
                    return 2
                run = run_one_agent(client=client, config=config, case=case, variant=variant, prompt=prompts[variant])
                case_result["runs"].append(run)
                observed_cost += run["usage"]["estimated_cost_usd"]
                if observed_cost > config["estimated_cost_ceiling_usd"]:
                    result["incomplete_reason"] = "cost_ceiling_exceeded"
                    _atomic_write(output_path, result)
                    return 2
    except AgentEvaluationError as error:
        result["incomplete_reason"] = str(error)
        _atomic_write(output_path, result)
        return 2
    result["status"] = "complete"
    result["summary"] = recompute_summary(result, config)
    result["headline"] = _headline(result["summary"])
    _atomic_write(output_path, result)
    return 0 if result["summary"]["success_criteria_met"] else 1


def verify_result(path: Path) -> int:
    verify_integrity()
    config, cases, _prompts = load_frozen_evaluation()
    result = _load_json(path)
    if not isinstance(result, dict) or result.get("report_type") != "grounded_agent_evaluation" or result.get("schema_version") != 1:
        raise AgentEvaluationError("agent evaluation result schema is invalid")
    if result.get("status") != "complete":
        return 2
    expected_cases = {case["id"]: case for case in cases}
    if set(case.get("case_id") for case in result.get("cases", [])) != set(expected_cases):
        raise AgentEvaluationError("agent evaluation result cases do not match the frozen manifest")
    for case_result in result["cases"]:
        packet = expected_cases[case_result["case_id"]]["packet"]
        if case_result.get("failed_evidence_ids") != failed_rule_ids(packet):
            raise AgentEvaluationError("stored failed-rule evidence does not match the frozen packet")
        if {run.get("variant") for run in case_result.get("runs", [])} != {"typed", "free_form"}:
            raise AgentEvaluationError("stored paired runs are incomplete")
        for run in case_result["runs"]:
            report = run.get("direct_report") if run.get("direct_status") == "accepted" else run.get("fallback_report")
            if not isinstance(report, str) or evaluation_grade(report, packet):
                raise AgentEvaluationError("stored accepted or fallback report failed re-grading")
            if run.get("direct_status") == "rejected" and not re.fullmatch(r"[0-9a-f]{64}", run.get("rejected_report_sha256") or ""):
                raise AgentEvaluationError("rejected report hash is missing")
            usage = run.get("usage", {})
            expected_cost = sum(
                observed_request_cost(item["input_tokens"], item["cached_input_tokens"], item["output_tokens"], config["rate_card_usd_per_million_tokens"])
                for item in usage.get("requests", [])
            )
            if not math.isclose(expected_cost, usage.get("estimated_cost_usd", -1), rel_tol=0, abs_tol=1e-12):
                raise AgentEvaluationError("stored request cost is inconsistent")
    summary = recompute_summary(result, config)
    if summary != result.get("summary") or result.get("headline") != _headline(summary):
        raise AgentEvaluationError("stored evaluation summary is inconsistent")
    return 0 if summary["success_criteria_met"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or verify the frozen grounded-agent evaluation.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.live:
            return run_live(args.output.resolve())
        return verify_result(args.verify.resolve())
    except AgentEvaluationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
