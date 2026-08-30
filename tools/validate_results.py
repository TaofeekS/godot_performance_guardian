#!/usr/bin/env python3
"""Validate deterministic Performance Guardian demo benchmark results."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

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


SCENARIOS = {"healthy", "node_leak", "cpu_spike"}
EXPECTED_PERCENTILE_DEFINITION = (
    "nearest-rank: sort ascending; select one-based rank ceil(p * N), "
    "clamped to 1..N"
)
SAMPLE_KEYS = {
    "frame",
    "elapsed_measurement_usec",
    "workload_time_usec",
    "process_time_ms",
    "physics_process_time_ms",
    "memory_static_bytes",
    "object_count",
    "node_count",
    "orphan_node_count",
    "owned_actor_count",
    "retained_node_count",
}
COUNT_SERIES = (
    "memory_static_bytes",
    "object_count",
    "node_count",
    "orphan_node_count",
    "owned_actor_count",
    "retained_node_count",
)
TIMING_SERIES = (
    "workload_time_usec",
    "process_time_ms",
    "physics_process_time_ms",
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_RELATIVE_PATH = "demo_project/scripts/benchmark_controller.gd"
CONTROLLER_PATH = REPOSITORY_ROOT / CONTROLLER_RELATIVE_PATH
GENERIC_RESULT_TYPE = "performance_budget_guardian_capture"
GENERIC_ADDON_NAME = "Performance Budget Guardian"
GENERIC_ADDON_VERSION = "1.1.0"
GENERIC_COMPATIBLE_ADDON_VERSIONS = {"1.0.1", GENERIC_ADDON_VERSION}
GENERIC_MEMORY_STORAGE_LIMITATION = (
    "Because the probe accumulates raw samples during capture, static-memory growth includes probe storage overhead "
    "and cannot by itself prove a project memory leak."
)
GENERIC_SAMPLE_KEYS = {
    "sample_index",
    "measured_frame",
    "elapsed_measurement_usec",
    "process_time_ms",
    "physics_process_time_ms",
    "memory_static_bytes",
    "object_count",
    "node_count",
    "orphan_node_count",
}
GENERIC_TIMING_SERIES = ("process_time_ms", "physics_process_time_ms")
GENERIC_COUNT_SERIES = (
    "memory_static_bytes",
    "object_count",
    "node_count",
    "orphan_node_count",
)


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notes: list[str] = []

    def fail(self, source: str, message: str) -> None:
        self.errors.append(f"{source}: {message}")

    def note(self, message: str) -> None:
        self.notes.append(message)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def close_enough(actual: Any, expected: Any) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if not is_number(actual) or not is_number(expected):
        return actual == expected
    return math.isclose(float(actual), float(expected), rel_tol=1e-8, abs_tol=1e-6)


def nearest_rank(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    rank = min(max(math.ceil(percentile * len(ordered)), 1), len(ordered))
    return ordered[rank - 1]


def timing_stats(values: list[float]) -> dict[str, float]:
    return {
        "mean": sum(values) / len(values),
        "p50": nearest_rank(values, 0.50),
        "p95": nearest_rank(values, 0.95),
        "max": max(values),
    }


def series_stats(values: list[float]) -> dict[str, float]:
    return {
        "initial": values[0],
        "final": values[-1],
        "peak": max(values),
        "delta": values[-1] - values[0],
    }


def require_mapping(parent: dict[str, Any], key: str, source: str, validation: Validation) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        validation.fail(source, f"{key!r} must be an object")
        return {}
    return value


def compare_summary(
    actual: dict[str, Any], expected: dict[str, Any], source: str, validation: Validation
) -> None:
    for key, expected_value in expected.items():
        if key not in actual:
            validation.fail(source, f"missing calculated field {key!r}")
        elif not close_enough(actual[key], expected_value):
            validation.fail(
                source,
                f"calculated {key}={actual[key]!r}, expected {expected_value!r} from raw samples",
            )


def is_safe_identifier(value: Any) -> bool:
    if not isinstance(value, str) or not 1 <= len(value) <= 64 or not value[0].isalnum():
        return False
    return all(character.isascii() and (character.isalnum() or character in "._-") for character in value)


def is_safe_revision(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not value or len(value) > 128 or value.startswith("/") or "\\" in value:
        return False
    if any(part in {"", ".", ".."} for part in value.split("/")):
        return False
    return all(character.isascii() and (character.isalnum() or character in "._-/") for character in value)


def is_safe_resource_path(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("res://") or "\\" in value:
        return False
    relative = value.removeprefix("res://")
    return bool(relative) and all(part not in {"", ".", ".."} for part in relative.split("/"))


def validate_generic_result(data: Any, path: Path, validation: Validation) -> None:
    source = path.name
    if not isinstance(data, dict):
        validation.fail(source, "top-level JSON value must be an object")
        return
    required = {
        "result_type": str,
        "schema_version": int,
        "profile": str,
        "project_name": str,
        "run_id": str,
        "godot_version": (str, int, float),
        "warmup_frames": int,
        "measured_frames": int,
        "sampling_interval_frames": int,
        "percentile_definition": str,
        "started_at_utc": str,
        "ended_at_utc": str,
        "headless": bool,
    }
    for key, expected_type in required.items():
        value = data.get(key)
        if (expected_type is not bool and isinstance(value, bool)) or not isinstance(value, expected_type):
            validation.fail(source, f"{key!r} has an invalid or missing type")
    if data.get("result_type") != GENERIC_RESULT_TYPE or data.get("schema_version") != 1:
        validation.fail(source, "generic capture identity or schema version is unsupported")
    if not is_safe_identifier(data.get("profile")):
        validation.fail(source, "profile is unsafe or invalid")
    if not is_safe_identifier(data.get("run_id")):
        validation.fail(source, "run_id is unsafe or invalid")
    if not isinstance(data.get("project_name"), str) or not data.get("project_name", "").strip():
        validation.fail(source, "project_name must be nonempty")
    if not is_safe_revision(data.get("source_revision")):
        validation.fail(source, "source_revision is unsafe")
    if data.get("headless") is not True:
        validation.fail(source, "generic verification capture was not headless")
    if data.get("percentile_definition") != EXPECTED_PERCENTILE_DEFINITION:
        validation.fail(source, "percentile_definition is missing or unexpected")

    warmup = data.get("warmup_frames")
    measured = data.get("measured_frames")
    interval = data.get("sampling_interval_frames")
    if not isinstance(warmup, int) or isinstance(warmup, bool) or not 0 <= warmup <= 1_000_000:
        validation.fail(source, "warmup_frames must be from 0 to 1000000")
    if not isinstance(measured, int) or isinstance(measured, bool) or not 1 <= measured <= 1_000_000:
        validation.fail(source, "measured_frames must be from 1 to 1000000")
    if not isinstance(interval, int) or isinstance(interval, bool) or interval < 1 or (
        isinstance(measured, int) and interval > measured
    ):
        validation.fail(source, "sampling_interval_frames is invalid")

    addon = require_mapping(data, "addon", source, validation)
    if addon.get("name") != GENERIC_ADDON_NAME:
        validation.fail(source, "addon identity is unsupported")
    if addon.get("version") not in GENERIC_COMPATIBLE_ADDON_VERSIONS:
        validation.fail(
            source,
            f"addon version {addon.get('version')!r} is unsupported; expected {GENERIC_ADDON_VERSION!r}; "
            "recapture with the current addon and a new run ID",
        )
    configuration = require_mapping(data, "measurement_configuration", source, validation)
    if not isinstance(configuration.get("auto_start"), bool) or not isinstance(configuration.get("auto_quit"), bool):
        validation.fail(source, "measurement configuration booleans are invalid")
    if not is_safe_resource_path(configuration.get("output_path")):
        validation.fail(source, "measurement output path is unsafe")
    environment = require_mapping(data, "environment", source, validation)
    for key in ("debug_build", "os_name", "os_version", "display_driver"):
        if key not in environment:
            validation.fail(source, f"environment is missing {key!r}")

    for key in ("started_at_utc", "ended_at_utc"):
        value = data.get(key)
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                validation.fail(source, f"{key} is not an ISO UTC timestamp")

    availability = require_mapping(data, "metric_availability", source, validation)
    memory_declaration = availability.get("memory_static_bytes")
    if not isinstance(memory_declaration, dict) or not isinstance(memory_declaration.get("available"), bool):
        validation.fail(source, "memory_static_bytes availability must be declared")
        memory_available = False
    else:
        memory_available = memory_declaration["available"]
        if memory_declaration.get("debug_only") is not True or not memory_declaration.get("reason"):
            validation.fail(source, "memory availability must include its debug-only reason")

    samples = data.get("samples")
    if not isinstance(samples, list):
        validation.fail(source, "samples must be an array")
        return
    if isinstance(measured, int) and isinstance(interval, int) and measured > 0 and interval > 0:
        expected_frames = list(range(interval, measured + 1, interval))
        if not expected_frames or expected_frames[-1] != measured:
            expected_frames.append(measured)
        if len(samples) != len(expected_frames):
            validation.fail(source, f"expected {len(expected_frames)} samples, found {len(samples)}")
    else:
        expected_frames = []
    for index, sample in enumerate(samples, 1):
        if not isinstance(sample, dict):
            validation.fail(source, f"sample {index} is not an object")
            continue
        missing = GENERIC_SAMPLE_KEYS - sample.keys()
        if missing:
            validation.fail(source, f"sample {index} is missing {sorted(missing)}")
        if sample.get("sample_index") != index:
            validation.fail(source, f"sample index sequence breaks at {index}")
        if index <= len(expected_frames) and sample.get("measured_frame") != expected_frames[index - 1]:
            validation.fail(source, f"measured-frame sequence breaks at sample {index}")
        for key in GENERIC_SAMPLE_KEYS - {"memory_static_bytes"}:
            if key in sample and (not is_number(sample[key]) or sample[key] < 0):
                validation.fail(source, f"sample {index} field {key!r} must be nonnegative numeric")
        memory_value = sample.get("memory_static_bytes")
        if memory_available and (not is_number(memory_value) or memory_value < 0):
            validation.fail(source, f"sample {index} must contain available memory")
        if not memory_available and memory_value is not None:
            validation.fail(source, f"sample {index} memory must be null when unavailable")

    elapsed = [sample.get("elapsed_measurement_usec") for sample in samples if isinstance(sample, dict)]
    if len(elapsed) == len(samples) and all(is_number(value) for value in elapsed):
        if any(right < left for left, right in zip(elapsed, elapsed[1:])):
            validation.fail(source, "elapsed_measurement_usec is not monotonic")

    summary = require_mapping(data, "summary", source, validation)
    timing_summary = require_mapping(summary, "timing", source, validation)
    count_summary = require_mapping(summary, "counts", source, validation)
    for key in GENERIC_TIMING_SERIES:
        values = [sample[key] for sample in samples if isinstance(sample, dict) and is_number(sample.get(key))]
        if len(values) == len(samples) and values:
            actual = timing_summary.get(key)
            if not isinstance(actual, dict):
                validation.fail(source, f"summary.timing.{key} must be an object")
            else:
                compare_summary(actual, timing_stats(values), source, validation)
    for key in GENERIC_COUNT_SERIES:
        values = [sample[key] for sample in samples if isinstance(sample, dict) and is_number(sample.get(key))]
        expected = series_stats(values) if values else {"initial": None, "final": None, "peak": None, "delta": None}
        actual = count_summary.get(key)
        if not isinstance(actual, dict):
            validation.fail(source, f"summary.counts.{key} must be an object")
        else:
            compare_summary(actual, expected, source, validation)
    for duration_key in ("measurement_duration_ms", "capture_duration_ms"):
        if not is_number(summary.get(duration_key)) or summary[duration_key] <= 0:
            validation.fail(source, f"summary.{duration_key} must be positive")
    if is_number(summary.get("measurement_duration_ms")) and is_number(summary.get("capture_duration_ms")):
        if summary["capture_duration_ms"] < summary["measurement_duration_ms"]:
            validation.fail(source, "capture duration is shorter than measurement duration")

    limitations = data.get("known_limitations")
    if not isinstance(limitations, list) or not limitations or not all(isinstance(item, str) and item for item in limitations):
        validation.fail(source, "known_limitations must be a nonempty string array")
    else:
        if GENERIC_MEMORY_STORAGE_LIMITATION not in limitations:
            validation.fail(source, "known_limitations is missing the required probe-storage memory limitation")
        if data.get("source_revision") is None and not any(
            "exact source revision is unknown" in item for item in limitations
        ):
            validation.fail(source, "missing source revision requires an explicit limitation")


def validate_result(data: Any, path: Path, validation: Validation) -> None:
    source = path.name
    if not isinstance(data, dict):
        validation.fail(source, "top-level JSON value must be an object")
        return

    required_scalars = {
        "schema_version": int,
        "scenario": str,
        "run_id": str,
        "godot_version": (str, int, float),
        "seed": int,
        "warmup_frames": int,
        "sample_frames": int,
        "sampling_interval_frames": int,
        "percentile_definition": str,
    }
    for key, expected_type in required_scalars.items():
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, expected_type):
            validation.fail(source, f"{key!r} has an invalid or missing type")

    scenario = data.get("scenario")
    if scenario not in SCENARIOS:
        validation.fail(source, f"unknown scenario {scenario!r}")
    if data.get("seed") != 1337:
        validation.fail(source, "seed must be 1337")
    if data.get("warmup_frames") != 120:
        validation.fail(source, "warmup_frames must be 120")
    if data.get("sample_frames") != 600:
        validation.fail(source, "sample_frames must be 600")
    if data.get("sampling_interval_frames") != 1:
        validation.fail(source, "sampling_interval_frames must be 1")
    if data.get("percentile_definition") != EXPECTED_PERCENTILE_DEFINITION:
        validation.fail(source, "percentile_definition is missing or unexpected")

    environment = require_mapping(data, "environment", source, validation)
    for key in (
        "godot_version_info",
        "debug_build",
        "os_name",
        "os_version",
        "distribution_name",
        "processor_name",
        "processor_count",
        "display_driver",
        "headless",
        "utc_started_at",
        "benchmark_arguments",
    ):
        if key not in environment:
            validation.fail(source, f"environment is missing {key!r}")
    if environment.get("headless") is not True:
        validation.fail(source, "run was not recorded as headless")

    config = require_mapping(data, "scenario_config", source, validation)
    if config.get("actor_count") != 64:
        validation.fail(source, "scenario_config.actor_count must be 64")
    if config.get("leak_interval_frames") != 5:
        validation.fail(source, "scenario_config.leak_interval_frames must be 5")

    availability = require_mapping(data, "metric_availability", source, validation)
    memory_availability = availability.get("memory_static_bytes")
    if not isinstance(memory_availability, dict) or not isinstance(
        memory_availability.get("available"), bool
    ):
        validation.fail(source, "memory_static_bytes availability must be declared")
        memory_available = False
    else:
        memory_available = memory_availability["available"]
        if memory_availability.get("debug_only") is not True or not memory_availability.get("reason"):
            validation.fail(source, "memory availability must identify its debug-only reason")

    tolerances = require_mapping(data, "tolerances", source, validation)
    if tolerances.get("healthy_object_count_growth") != 32:
        validation.fail(source, "healthy object-count tolerance must be 32")
    memory_tolerance = tolerances.get("healthy_memory_growth_bytes")
    if memory_available and not is_number(memory_tolerance):
        validation.fail(source, "available memory metric requires a numeric growth tolerance")
    if not memory_available and memory_tolerance is not None:
        validation.fail(source, "unavailable memory metric must have a null growth tolerance")

    baseline = require_mapping(data, "measurement_baseline", source, validation)
    post_cleanup = require_mapping(data, "post_cleanup", source, validation)
    summary = require_mapping(data, "summary", source, validation)
    timing_summary = require_mapping(summary, "timing", source, validation)
    count_summary = require_mapping(summary, "counts", source, validation)
    post_deltas = require_mapping(summary, "post_cleanup_deltas", source, validation)

    samples = data.get("samples")
    if not isinstance(samples, list):
        validation.fail(source, "samples must be an array")
        return
    if len(samples) != 600:
        validation.fail(source, f"expected 600 samples, found {len(samples)}")
        return

    for index, sample in enumerate(samples, 1):
        if not isinstance(sample, dict):
            validation.fail(source, f"sample {index} is not an object")
            continue
        missing = SAMPLE_KEYS - sample.keys()
        if missing:
            validation.fail(source, f"sample {index} is missing {sorted(missing)}")
        if sample.get("frame") != index:
            validation.fail(source, f"sample frame sequence breaks at index {index}")
        for key in SAMPLE_KEYS - {"memory_static_bytes"}:
            if key in sample and not is_number(sample[key]):
                validation.fail(source, f"sample {index} field {key!r} must be numeric")
        memory_value = sample.get("memory_static_bytes")
        if memory_available and not is_number(memory_value):
            validation.fail(source, f"sample {index} must contain available memory")
        if not memory_available and memory_value is not None:
            validation.fail(source, f"sample {index} memory must be null when unavailable")

    elapsed = [sample.get("elapsed_measurement_usec") for sample in samples]
    if all(is_number(value) for value in elapsed):
        if any(right < left for left, right in zip(elapsed, elapsed[1:])):
            validation.fail(source, "elapsed_measurement_usec is not monotonic")

    for key in TIMING_SERIES:
        values = [sample[key] for sample in samples if is_number(sample.get(key))]
        if len(values) == 600:
            actual = timing_summary.get(key)
            if not isinstance(actual, dict):
                validation.fail(source, f"summary.timing.{key} must be an object")
            else:
                compare_summary(actual, timing_stats(values), source, validation)

    for key in COUNT_SERIES:
        values = [sample[key] for sample in samples if is_number(sample.get(key))]
        expected = series_stats(values) if values else {
            "initial": None,
            "final": None,
            "peak": None,
            "delta": None,
        }
        actual = count_summary.get(key)
        if not isinstance(actual, dict):
            validation.fail(source, f"summary.counts.{key} must be an object")
        else:
            compare_summary(actual, expected, source, validation)

    for key in COUNT_SERIES:
        initial = baseline.get(key)
        final = post_cleanup.get(key)
        expected_delta = None if initial is None or final is None else final - initial
        if not close_enough(post_deltas.get(key), expected_delta):
            validation.fail(source, f"post-cleanup delta for {key} is incorrect")

    if not close_enough(data.get("retained_nodes"), post_cleanup.get("retained_node_count")):
        validation.fail(source, "headline retained_nodes disagrees with post-cleanup evidence")
    if not close_enough(data.get("p95_workload_time_usec"), timing_summary.get("workload_time_usec", {}).get("p95")):
        validation.fail(source, "headline workload p95 disagrees with summary")
    if not close_enough(data.get("p95_process_time_ms"), timing_summary.get("process_time_ms", {}).get("p95")):
        validation.fail(source, "headline process p95 disagrees with summary")

    actor_counts = [sample.get("owned_actor_count") for sample in samples]
    retained_counts = [sample.get("retained_node_count") for sample in samples]
    node_counts = [sample.get("node_count") for sample in samples]
    object_counts = [sample.get("object_count") for sample in samples]
    if scenario in SCENARIOS and all(is_number(value) for value in actor_counts):
        if any(value != 64 for value in actor_counts):
            validation.fail(source, f"{scenario} measured actor population was not stable at 64")

    if scenario == "healthy":
        if post_cleanup.get("owned_actor_count") != 0 or post_cleanup.get("retained_node_count") != 0:
            validation.fail(source, "healthy cleanup left scenario-owned nodes")
        object_growth = post_cleanup.get("object_count", 0) - baseline.get("object_count", 0)
        if object_growth > tolerances.get("healthy_object_count_growth", -1):
            validation.fail(source, f"healthy object growth {object_growth} exceeds tolerance")
        if memory_available:
            memory_growth = post_cleanup["memory_static_bytes"] - baseline["memory_static_bytes"]
            if memory_growth > memory_tolerance:
                validation.fail(source, f"healthy memory growth {memory_growth} exceeds tolerance")
    elif scenario == "node_leak":
        if retained_counts[-1] != 120:
            validation.fail(source, "final measured sample must contain exactly 120 retained nodes")
        if post_cleanup.get("retained_node_count") != 120:
            validation.fail(source, "post-cleanup evidence must retain exactly 120 leak nodes")
        if post_cleanup.get("owned_actor_count") != 0:
            validation.fail(source, "node-leak evidence cleanup left ordinary actors")
        if any(right < left for left, right in zip(retained_counts, retained_counts[1:])):
            validation.fail(source, "retained-node count is not monotonically increasing")
        # Performance's global monitors can lag mutations by one frame. Exact leak
        # ownership is asserted above; the global monitors only need to corroborate growth.
        if node_counts[-1] <= node_counts[0]:
            validation.fail(source, "global node count did not increase during the leak")
        if object_counts[-1] <= object_counts[0]:
            validation.fail(source, "global object count did not increase during the leak")
    elif scenario == "cpu_spike":
        if any(value != 0 for value in retained_counts):
            validation.fail(source, "cpu-spike scenario unexpectedly retained nodes")
        if post_cleanup.get("owned_actor_count") != 0 or post_cleanup.get("retained_node_count") != 0:
            validation.fail(source, "cpu-spike cleanup left scenario-owned nodes")

    for duration_key in ("measurement_duration_ms", "scenario_duration_ms"):
        if not is_number(summary.get(duration_key)) or summary[duration_key] <= 0:
            validation.fail(source, f"summary.{duration_key} must be positive")
    if is_number(summary.get("measurement_duration_ms")) and is_number(summary.get("scenario_duration_ms")):
        if summary["scenario_duration_ms"] < summary["measurement_duration_ms"]:
            validation.fail(source, "scenario duration is shorter than measurement duration")


def collect_paths(arguments: list[str]) -> list[Path]:
    collected: list[Path] = []
    for argument in arguments:
        path = Path(argument)
        if path.is_dir():
            collected.extend(sorted(path.glob("*.json")))
        else:
            collected.append(path)
    return collected


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return math.inf if numerator > 0 else 0.0
    return numerator / denominator


def _item(
    evidence_id: str,
    claim: str,
    metric: str,
    value: Any,
    unit: str | None,
    scenario: str,
    source_type: str,
    source: str,
    **details: Any,
) -> dict[str, Any]:
    item = {
        "id": evidence_id,
        "claim": claim,
        "metric": metric,
        "value": value,
        "unit": unit,
        "scenario": scenario,
        "source_type": source_type,
        "source": source,
    }
    item.update(details)
    return item


def _generic_item(
    evidence_id: str,
    claim: str,
    metric: str,
    value: Any,
    unit: str | None,
    profile: str,
    source_type: str,
    source: str,
    **details: Any,
) -> dict[str, Any]:
    item = {
        "id": evidence_id,
        "claim": claim,
        "metric": metric,
        "value": value,
        "unit": unit,
        "profile": profile,
        "source_type": source_type,
        "source": source,
    }
    item.update(details)
    return item


def _controller_behavior_evidence(validation: Validation) -> list[dict[str, Any]]:
    try:
        source = CONTROLLER_PATH.read_text(encoding="utf-8")
    except OSError:
        validation.fail("benchmark controller", "could not read allowlisted scenario source")
        return []

    required_fragments = {
        "actor workload": ("for actor in actors:", "actor.simulate_step(frame_index)"),
        "node-leak workload": (
            'if scenario == "node_leak":',
            "var temporary_node := Node2D.new()",
            "frame_index % LEAK_INTERVAL_FRAMES == 0",
            "leak_container.add_child(temporary_node)",
        ),
        "CPU-spike workload": (
            'elif scenario == "cpu_spike":',
            "_run_cpu_spike(frame_index)",
            "for outer_index in CPU_OUTER_ITERATIONS:",
            "for inner_index in CPU_INNER_ITERATIONS:",
        ),
    }
    for behavior, fragments in required_fragments.items():
        if any(fragment not in source for fragment in fragments):
            validation.fail("benchmark controller", f"allowlisted {behavior} changed unexpectedly")
    if validation.errors:
        return []

    return [
        _item(
            "E20",
            "The current controller routes cpu_spike frames through a nested numerical workload.",
            "scenario_behavior",
            "nested_numerical_workload_each_frame",
            None,
            "cpu_spike",
            "allowlisted_source",
            f"{CONTROLLER_RELATIVE_PATH}::_run_workload/_run_cpu_spike",
        ),
        _item(
            "E21",
            "The current controller creates a temporary node for node_leak and retains one every configured leak interval during measurement.",
            "scenario_behavior",
            "temporary_node_with_periodic_retention",
            None,
            "node_leak",
            "allowlisted_source",
            f"{CONTROLLER_RELATIVE_PATH}::_run_workload",
        ),
        _item(
            "E22",
            "All scenarios run the fixed actor simulation; healthy adds neither the leak branch nor the CPU-spike branch.",
            "scenario_behavior",
            "actor_simulation_only",
            None,
            "healthy",
            "allowlisted_source",
            f"{CONTROLLER_RELATIVE_PATH}::_run_workload",
        ),
    ]


def build_evidence(
    grouped: dict[str, list[dict[str, Any]]], validation: Validation
) -> list[dict[str, Any]]:
    """Build ordered evidence from the same validated data used for pass/fail."""

    if validation.errors:
        return []

    healthy = grouped["healthy"]
    cpu = grouped["cpu_spike"]
    leak = grouped["node_leak"]
    healthy_workload = statistics.median(
        result["summary"]["timing"]["workload_time_usec"]["p95"] for result in healthy
    )
    cpu_workload = statistics.median(
        result["summary"]["timing"]["workload_time_usec"]["p95"] for result in cpu
    )
    workload_ratio = _ratio(cpu_workload, healthy_workload)
    healthy_process = statistics.median(
        result["summary"]["timing"]["process_time_ms"]["p95"] for result in healthy
    )
    cpu_process = statistics.median(
        result["summary"]["timing"]["process_time_ms"]["p95"] for result in cpu
    )
    process_ratio = _ratio(cpu_process, healthy_process)
    healthy_duration = statistics.median(
        result["summary"]["scenario_duration_ms"] for result in healthy
    )
    cpu_duration = statistics.median(
        result["summary"]["scenario_duration_ms"] for result in cpu
    )
    duration_ratio = _ratio(cpu_duration, healthy_duration)
    source = "validated result aggregate"

    configurations: dict[str, int] = {}
    for result in cpu:
        config = result["scenario_config"]
        label = f'{config.get("cpu_outer_iterations")}x{config.get("cpu_inner_iterations")}'
        configurations[label] = configurations.get(label, 0) + 1

    evidence = [
        _item("E1", "All candidate result files passed the configured validator checks.", "validated_file_count", sum(len(values) for values in grouped.values()), "files", "all", "validated_result", source),
        _item("E2", "Healthy median per-run p95 workload time.", "median_p95_workload_time", healthy_workload, "usec", "healthy", "validated_aggregate", source),
        _item("E3", "CPU-spike median per-run p95 workload time.", "median_p95_workload_time", cpu_workload, "usec", "cpu_spike", "validated_aggregate", source),
        _item("E4", "CPU-spike to healthy workload-time ratio.", "workload_time_ratio", workload_ratio, "x", "cpu_spike_vs_healthy", "validated_aggregate", source),
        _item("E5", "CPU-spike workload-time increase over healthy.", "workload_time_increase", (workload_ratio - 1.0) * 100.0, "percent", "cpu_spike_vs_healthy", "validated_aggregate", source),
        _item("E6", "Healthy median per-run p95 process time.", "median_p95_process_time", healthy_process, "ms", "healthy", "validated_aggregate", source),
        _item("E7", "CPU-spike median per-run p95 process time.", "median_p95_process_time", cpu_process, "ms", "cpu_spike", "validated_aggregate", source),
        _item("E8", "CPU-spike to healthy process-time ratio.", "process_time_ratio", process_ratio, "x", "cpu_spike_vs_healthy", "validated_aggregate", source),
        _item("E9", "CPU-spike process-time increase over healthy.", "process_time_increase", (process_ratio - 1.0) * 100.0, "percent", "cpu_spike_vs_healthy", "validated_aggregate", source),
        _item("E10", "Healthy median scenario duration.", "median_scenario_duration", healthy_duration, "ms", "healthy", "validated_aggregate", source),
        _item("E11", "CPU-spike median scenario duration.", "median_scenario_duration", cpu_duration, "ms", "cpu_spike", "validated_aggregate", source),
        _item("E12", "CPU-spike to healthy scenario-duration ratio.", "scenario_duration_ratio", duration_ratio, "x", "cpu_spike_vs_healthy", "validated_aggregate", source),
        _item("E13", "CPU-spike scenario-duration increase over healthy.", "scenario_duration_increase", (duration_ratio - 1.0) * 100.0, "percent", "cpu_spike_vs_healthy", "validated_aggregate", source),
        _item("E14", f"Every one of the {len(leak)} node-leak runs retained 120 nodes after evidence cleanup.", "post_cleanup_retained_nodes", 120, "nodes", "node_leak", "validated_result", source, run_count=len(leak)),
        _item("E15", f"Every one of the {len(healthy)} healthy runs retained zero nodes after evidence cleanup.", "post_cleanup_retained_nodes", 0, "nodes", "healthy", "validated_result", source, run_count=len(healthy)),
        _item("E16", f"Every one of the {len(cpu)} CPU-spike runs retained zero nodes after evidence cleanup.", "post_cleanup_retained_nodes", 0, "nodes", "cpu_spike", "validated_result", source, run_count=len(cpu)),
        _item("E17", "Every validated result used 64 scenario-owned actors.", "actor_count", 64, "actors", "all", "validated_result", source),
        _item("E18", "Every validated result used a five-frame leak interval.", "leak_interval_frames", 5, "frames", "all", "validated_result", source),
        _item("E19", "Stored CPU-spike nested-workload configurations and run counts.", "cpu_workload_configurations", configurations, None, "cpu_spike", "validated_result", source),
    ]
    evidence.extend(_controller_behavior_evidence(validation))
    return [] if validation.errors else evidence


def _normalized_results_directory(arguments: list[str], workspace_root: Path) -> str:
    if len(arguments) != 1:
        return "multiple-inputs"
    path = (workspace_root / arguments[0]).resolve()
    try:
        return path.relative_to(workspace_root).as_posix()
    except ValueError:
        return "unsafe-results-directory"


def evidence_packet(
    arguments: list[str],
    paths: list[Path],
    loaded: list[tuple[Path, dict[str, Any]]],
    grouped: dict[str, list[dict[str, Any]]],
    validation: Validation,
    workspace_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    evidence = build_evidence(grouped, validation)
    configuration_item = next(
        (item for item in evidence if item.get("id") == "E19"), None
    )
    configurations = configuration_item.get("value", {}) if configuration_item else {}
    if isinstance(configurations, dict) and len(configurations) > 1:
        configuration_limitation = (
            "The stored result set mixes historical CPU-workload configurations, "
            "so its aggregate is descriptive rather than a single "
            "controlled-configuration comparison."
        )
    else:
        configuration_limitation = (
            "Timing aggregates describe only the stored workload configuration and "
            "recorded execution environments; they are not portable performance promises."
        )
    return {
        "packet_type": "godot_performance_evidence",
        "schema_version": 1,
        "evidence_kind": "failed" if validation.errors else "synthetic",
        "validation": {
            "status": "failed" if validation.errors else "passed",
            "candidate_file_count": len(paths),
            "validated_file_count": len(loaded) if not validation.errors else 0,
            "errors": validation.errors,
            "timed_out": False,
            "error_type": None,
            "exit_code": 1 if validation.errors else 0,
        },
        "results_directory": _normalized_results_directory(arguments, workspace_root),
        "evidence": evidence,
        "limitations": [
            {"id": "L1", "statement": "Validator success proves only that the configured checks passed; it does not prove that no other performance problem exists."},
            {"id": "L2", "statement": configuration_limitation},
            {"id": "L3", "statement": "Stored results do not contain a source revision or source hash, so current allowlisted source cannot prove the exact source used for every historical result."},
            {"id": "L4", "statement": "The benchmark is synthetic and headless; it does not establish rendering or GPU performance."},
            {"id": "L5", "statement": "The available evidence does not establish the root cause."},
        ],
    }


def generic_evidence_packet(
    arguments: list[str],
    paths: list[Path],
    loaded: list[tuple[Path, dict[str, Any]]],
    validation: Validation,
    workspace_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    if not validation.errors:
        source = _normalized_results_directory(arguments, workspace_root)
        evidence.append(
            _generic_item(
                "G1",
                "All candidate generic capture files passed the configured validator checks.",
                "validated_file_count",
                len(loaded),
                "files",
                "all",
                "validated_result",
                source,
            )
        )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for _path, result in loaded:
            grouped.setdefault(result["profile"], []).append(result)
        evidence_index = 2
        specifications = (
            ("median_p95_process_time", "ms", "timing", "process_time_ms", "p95"),
            ("median_p95_physics_process_time", "ms", "timing", "physics_process_time_ms", "p95"),
            ("median_measurement_duration", "ms", None, "measurement_duration_ms", None),
            ("median_peak_memory_static_bytes", "bytes", "counts", "memory_static_bytes", "peak"),
            ("median_peak_object_count", "objects", "counts", "object_count", "peak"),
            ("median_peak_node_count", "nodes", "counts", "node_count", "peak"),
            ("median_peak_orphan_node_count", "nodes", "counts", "orphan_node_count", "peak"),
        )
        for profile in sorted(grouped):
            results = grouped[profile]
            for metric, unit, section, series, statistic in specifications:
                values: list[float] = []
                for result in results:
                    summary = result["summary"]
                    value = summary[series] if section is None else summary[section][series][statistic]
                    if is_number(value):
                        values.append(float(value))
                if len(values) != len(results):
                    continue
                value = statistics.median(values)
                item = _generic_item(
                    f"G{evidence_index}",
                    f"{profile} median {metric.replace('_', ' ')} across validated captures.",
                    metric,
                    value,
                    unit,
                    profile,
                    "validated_aggregate",
                    source,
                    run_count=len(results),
                )
                evidence.append(item)
                evidence_index += 1

            memory_flags = [
                bool(result["metric_availability"]["memory_static_bytes"]["available"])
                for result in results
            ]
            memory_status = (
                "available" if all(memory_flags) else
                "unavailable" if not any(memory_flags) else
                "mixed"
            )
            evidence.append(
                _generic_item(
                    f"G{evidence_index}",
                    f"{profile} static-memory evidence availability across validated captures.",
                    "memory_static_availability",
                    memory_status,
                    None,
                    profile,
                    "validated_metadata",
                    source,
                    run_count=len(results),
                )
            )
            evidence_index += 1

            revision_flags = [result.get("source_revision") is not None for result in results]
            revision_status = (
                "present" if all(revision_flags) else
                "unknown" if not any(revision_flags) else
                "mixed"
            )
            evidence.append(
                _generic_item(
                    f"G{evidence_index}",
                    f"{profile} source-revision availability across validated captures.",
                    "source_revision_availability",
                    revision_status,
                    None,
                    profile,
                    "validated_metadata",
                    source,
                    run_count=len(results),
                )
            )
            evidence_index += 1

    limitations = [
        {"id": "GL1", "statement": "Validator success proves only that configured generic schema and summary checks passed."},
        {"id": "GL2", "statement": "Global engine monitors are not owned solely by the named project profile."},
        {"id": "GL3", "statement": "Process timing includes engine scheduling and probe overhead; no project workload timer is claimed."},
        {"id": "GL4", "statement": "Headless capture does not establish rendering or GPU performance."},
        {"id": "GL5", "statement": "Timing limits require calibration on stable project hardware and are not universal recommendations."},
        {"id": "GL6", "statement": GENERIC_MEMORY_STORAGE_LIMITATION},
    ]
    if any(result.get("source_revision") is None for _path, result in loaded):
        limitations.append({"id": "GL7", "statement": "At least one capture did not supply a source revision, so its exact source revision is unknown."})
    return {
        "packet_type": "godot_performance_evidence",
        "schema_version": 1,
        "evidence_kind": "failed" if validation.errors else "generic",
        "validation": {
            "status": "failed" if validation.errors else "passed",
            "candidate_file_count": len(paths),
            "validated_file_count": len(loaded) if not validation.errors else 0,
            "errors": validation.errors,
            "timed_out": False,
            "error_type": None,
            "exit_code": 1 if validation.errors else 0,
        },
        "results_directory": _normalized_results_directory(arguments, workspace_root),
        "evidence": [] if validation.errors else evidence,
        "limitations": limitations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-json",
        action="store_true",
        help="emit a deterministic machine-readable evidence packet",
    )
    parser.add_argument(
        "--workspace-root",
        help="explicit workspace root for repository-relative generic captures",
    )
    parser.add_argument("paths", nargs="+", help="Result JSON files or directories")
    args = parser.parse_args()

    try:
        workspace_root = resolve_workspace_root(args.workspace_root, REPOSITORY_ROOT)
        normalized_arguments: list[str] = []
        resolved_arguments: list[str] = []
        for argument in args.paths:
            if args.workspace_root is None:
                resolved = Path(argument).resolve()
                if not resolved.exists():
                    raise WorkspacePathError("result input does not exist")
                try:
                    normalized = resolved.relative_to(workspace_root).as_posix()
                except ValueError:
                    normalized = resolved.as_posix()
            else:
                resolved, normalized = resolve_workspace_member(
                    workspace_root,
                    argument,
                    label="result input",
                    expected=None,
                )
                if not resolved.exists():
                    raise WorkspacePathError("result input does not exist")
            normalized_arguments.append(normalized)
            resolved_arguments.append(str(resolved))
    except WorkspacePathError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    validation = Validation()
    paths = collect_paths(resolved_arguments)
    if not paths:
        if args.evidence_json:
            validation.fail("result set", "no result JSON files found")
            grouped = {scenario: [] for scenario in SCENARIOS}
            print(
                json.dumps(
                    evidence_packet(
                        normalized_arguments,
                        paths,
                        [],
                        grouped,
                        validation,
                        workspace_root,
                    ),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 1
        print("ERROR: no result JSON files found", file=sys.stderr)
        return 1

    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            validation.fail(path.name, f"could not read valid JSON: {error}")
            continue
        if isinstance(data, dict):
            loaded.append((path, data))

    result_kinds = {
        "generic" if data.get("result_type") == GENERIC_RESULT_TYPE else (
            "synthetic" if "result_type" not in data else "unknown"
        )
        for _, data in loaded
    }
    if len(result_kinds) > 1:
        validation.fail("result set", "mixed synthetic and generic result types are not supported")
    if "unknown" in result_kinds:
        validation.fail("result set", "unsupported result_type")
    result_kind = next(iter(result_kinds), "synthetic")
    if workspace_root != REPOSITORY_ROOT.resolve() and result_kind != "generic":
        validation.fail(
            "result set",
            "external workspaces support generic performance captures only",
        )
    for path, data in loaded:
        if result_kind == "generic":
            validate_generic_result(data, path, validation)
        elif result_kind == "synthetic":
            validate_result(data, path, validation)

    run_ids = [data.get("run_id") for _, data in loaded if isinstance(data.get("run_id"), str)]
    if len(run_ids) != len(set(run_ids)):
        validation.fail("result set", "run IDs are not unique")

    grouped: dict[str, list[dict[str, Any]]] = {scenario: [] for scenario in SCENARIOS}
    if result_kind == "synthetic":
        for _, data in loaded:
            if data.get("scenario") in grouped:
                grouped[data["scenario"]].append(data)
        for scenario, results in grouped.items():
            if len(results) < 3:
                validation.fail("result set", f"scenario {scenario!r} has {len(results)} runs; at least 3 required")

    if result_kind == "synthetic" and len(grouped["healthy"]) >= 3 and len(grouped["cpu_spike"]) >= 3:
        healthy_p95 = statistics.median(
            result["summary"]["timing"]["workload_time_usec"]["p95"]
            for result in grouped["healthy"]
        )
        cpu_p95 = statistics.median(
            result["summary"]["timing"]["workload_time_usec"]["p95"]
            for result in grouped["cpu_spike"]
        )
        ratio = math.inf if healthy_p95 == 0 and cpu_p95 > 0 else (
            cpu_p95 / healthy_p95 if healthy_p95 else 0.0
        )
        validation.note(
            f"median p95 workload: healthy={healthy_p95:.3f} usec, "
            f"cpu_spike={cpu_p95:.3f} usec, ratio={ratio:.2f}x"
        )
        if cpu_p95 < healthy_p95 * 2.0:
            validation.fail("result set", f"CPU-spike workload ratio {ratio:.2f}x is below 2.00x")

        healthy_process = statistics.median(
            result["summary"]["timing"]["process_time_ms"]["p95"]
            for result in grouped["healthy"]
        )
        cpu_process = statistics.median(
            result["summary"]["timing"]["process_time_ms"]["p95"]
            for result in grouped["cpu_spike"]
        )
        healthy_duration = statistics.median(
            result["summary"]["scenario_duration_ms"] for result in grouped["healthy"]
        )
        cpu_duration = statistics.median(
            result["summary"]["scenario_duration_ms"] for result in grouped["cpu_spike"]
        )
        validation.note(
            f"supporting evidence: process p95 healthy={healthy_process:.6f} ms, "
            f"cpu_spike={cpu_process:.6f} ms; duration healthy={healthy_duration:.3f} ms, "
            f"cpu_spike={cpu_duration:.3f} ms"
        )

    result_directories = {path.parent for path in paths}
    for directory in result_directories:
        leftovers = sorted(directory.glob("*.tmp.*"))
        if leftovers:
            validation.fail(
                directory.name,
                "temporary result files remain",
            )

    if args.evidence_json:
        packet = (
            generic_evidence_packet(
                normalized_arguments,
                paths,
                loaded,
                validation,
                workspace_root,
            )
            if result_kind == "generic"
            else evidence_packet(
                normalized_arguments,
                paths,
                loaded,
                grouped,
                validation,
                workspace_root,
            )
        )
        print(json.dumps(packet, sort_keys=True, separators=(",", ":")))
        return packet["validation"]["exit_code"]

    for note in validation.notes:
        print(f"INFO: {note}")
    if validation.errors:
        for error in validation.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(validation.errors)} error(s).", file=sys.stderr)
        return 1

    label = " generic capture" if result_kind == "generic" else ""
    print(f"Validated {len(loaded)}{label} result files successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
