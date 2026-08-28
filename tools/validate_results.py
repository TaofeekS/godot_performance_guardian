#!/usr/bin/env python3
"""Validate deterministic Performance Guardian demo benchmark results."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Result JSON files or directories")
    args = parser.parse_args()

    validation = Validation()
    paths = collect_paths(args.paths)
    if not paths:
        print("ERROR: no result JSON files found", file=sys.stderr)
        return 1

    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            validation.fail(str(path), f"could not read valid JSON: {error}")
            continue
        validate_result(data, path, validation)
        if isinstance(data, dict):
            loaded.append((path, data))

    run_ids = [data.get("run_id") for _, data in loaded if isinstance(data.get("run_id"), str)]
    if len(run_ids) != len(set(run_ids)):
        validation.fail("result set", "run IDs are not unique")

    grouped: dict[str, list[dict[str, Any]]] = {scenario: [] for scenario in SCENARIOS}
    for _, data in loaded:
        if data.get("scenario") in grouped:
            grouped[data["scenario"]].append(data)
    for scenario, results in grouped.items():
        if len(results) < 3:
            validation.fail("result set", f"scenario {scenario!r} has {len(results)} runs; at least 3 required")

    if len(grouped["healthy"]) >= 3 and len(grouped["cpu_spike"]) >= 3:
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
            validation.fail(str(directory), f"temporary result files remain: {leftovers}")

    for note in validation.notes:
        print(f"INFO: {note}")
    if validation.errors:
        for error in validation.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(validation.errors)} error(s).", file=sys.stderr)
        return 1

    print(f"Validated {len(loaded)} result files successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
