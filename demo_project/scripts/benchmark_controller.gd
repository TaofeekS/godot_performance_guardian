extends Node2D

const VALID_SCENARIOS := ["healthy", "node_leak", "cpu_spike"]
const FIXED_SEED := 1337
const WARMUP_FRAMES := 120
const SAMPLE_FRAMES := 600
const ACTOR_COUNT := 64
const LEAK_INTERVAL_FRAMES := 5
const CPU_OUTER_ITERATIONS := 240
const CPU_INNER_ITERATIONS := 240
const OBJECT_COUNT_TOLERANCE := 32
const MEMORY_ABSOLUTE_TOLERANCE_BYTES := 1048576
const MEMORY_RELATIVE_TOLERANCE := 0.02
const PERCENTILE_DEFINITION := "nearest-rank: sort ascending; select one-based rank ceil(p * N), clamped to 1..N"

var scenario := ""
var run_id := ""
var output_argument := ""
var rng := RandomNumberGenerator.new()
var actors: Array[BenchmarkTestActor] = []
var samples: Array[Dictionary] = []
var actor_container := Node2D.new()
var leak_container := Node2D.new()
var transient_container := Node2D.new()
var workload_checksum: float = 0.0
var total_start_usec: int = 0
var measurement_start_usec: int = 0
var measurement_end_usec: int = 0
var memory_static_available := false
var measurement_baseline: Dictionary = {}
var post_cleanup_snapshot: Dictionary = {}


func _ready() -> void:
	total_start_usec = Time.get_ticks_usec()
	if not _parse_arguments():
		return

	actor_container.name = "Actors"
	leak_container.name = "IntentionalLeaks"
	transient_container.name = "TransientNodes"
	add_child(actor_container)
	add_child(leak_container)
	add_child(transient_container)

	rng.seed = FIXED_SEED
	_spawn_actors()

	for warmup_index in range(1, WARMUP_FRAMES + 1):
		_run_workload(warmup_index, false)
		await get_tree().process_frame

	_clear_warmup_state()
	await get_tree().process_frame
	await get_tree().process_frame

	var baseline_memory := float(Performance.get_monitor(Performance.MEMORY_STATIC))
	memory_static_available = OS.is_debug_build() and baseline_memory > 0.0
	measurement_baseline = _capture_snapshot()
	measurement_start_usec = Time.get_ticks_usec()

	for frame_index in range(1, SAMPLE_FRAMES + 1):
		var workload_start_usec := Time.get_ticks_usec()
		_run_workload(frame_index, true)
		var workload_time_usec := Time.get_ticks_usec() - workload_start_usec
		samples.append(_capture_sample(frame_index, workload_time_usec))
		await get_tree().process_frame

	measurement_end_usec = Time.get_ticks_usec()
	_cleanup_for_evidence()
	await get_tree().process_frame
	await get_tree().process_frame
	post_cleanup_snapshot = _capture_snapshot()
	var scenario_duration_ms := float(Time.get_ticks_usec() - total_start_usec) / 1000.0
	var result := _build_result(scenario_duration_ms)
	var final_path := _resolve_output_path()
	if final_path.is_empty() or not _write_json_atomically(final_path, result):
		await _final_teardown()
		_fatal("Failed to write benchmark result", 3)
		return

	print("BENCHMARK_RESULT=%s" % final_path)
	await _final_teardown()
	get_tree().quit(0)


func _parse_arguments() -> bool:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--scenario="):
			scenario = argument.trim_prefix("--scenario=")
		elif argument.begins_with("--run-id="):
			run_id = argument.trim_prefix("--run-id=")
		elif argument.begins_with("--output="):
			output_argument = argument.trim_prefix("--output=")

	if not scenario in VALID_SCENARIOS:
		_fatal("Missing or invalid --scenario. Expected one of: %s" % [", ".join(VALID_SCENARIOS)], 2)
		return false
	if run_id.is_empty():
		var timestamp := Time.get_datetime_string_from_system(true, false).replace(":", "").replace("-", "")
		run_id = "%s-%s-%s" % [scenario, timestamp, OS.get_process_id()]
	if not _is_safe_run_id(run_id):
		_fatal("--run-id may contain only letters, digits, dot, underscore, and hyphen", 2)
		return false
	return true


func _is_safe_run_id(value: String) -> bool:
	if value.is_empty():
		return false
	for index in value.length():
		var character := value.substr(index, 1)
		if not character.to_lower() in "abcdefghijklmnopqrstuvwxyz0123456789._-":
			return false
	return true


func _spawn_actors() -> void:
	for actor_index in ACTOR_COUNT:
		var actor := BenchmarkTestActor.new()
		actor.configure(actor_index, rng)
		actor_container.add_child(actor)
		actors.append(actor)


func _run_workload(frame_index: int, measured: bool) -> void:
	for actor in actors:
		if is_instance_valid(actor):
			actor.simulate_step(frame_index)

	if scenario == "node_leak":
		var temporary_node := Node2D.new()
		temporary_node.name = "Temporary_%04d" % frame_index
		if measured and frame_index % LEAK_INTERVAL_FRAMES == 0:
			leak_container.add_child(temporary_node)
		else:
			transient_container.add_child(temporary_node)
			temporary_node.queue_free()
	elif scenario == "cpu_spike":
		_run_cpu_spike(frame_index)


func _run_cpu_spike(frame_index: int) -> void:
	var local_checksum := workload_checksum
	for outer_index in CPU_OUTER_ITERATIONS:
		for inner_index in CPU_INNER_ITERATIONS:
			var value := float((outer_index + 1) * (inner_index + 3) + frame_index)
			local_checksum += sin(value * 0.001) * cos(value * 0.0007) + sqrt(fmod(value, 97.0) + 1.0)
	workload_checksum = fmod(local_checksum, 1000000000.0)


func _clear_warmup_state() -> void:
	# Warmup never intentionally retains nodes, but explicitly clear any queued transients.
	for child in transient_container.get_children():
		child.queue_free()


func _cleanup_for_evidence() -> void:
	# Intentional leak nodes remain alive until after post-cleanup evidence and JSON output.
	for actor in actors:
		if is_instance_valid(actor):
			actor.queue_free()
	actors.clear()
	for child in transient_container.get_children():
		child.queue_free()


func _final_teardown() -> void:
	for child in leak_container.get_children():
		child.queue_free()
	for child in transient_container.get_children():
		child.queue_free()
	for child in actor_container.get_children():
		child.queue_free()
	await get_tree().process_frame
	await get_tree().process_frame


func _capture_sample(frame_index: int, workload_time_usec: int) -> Dictionary:
	var memory_value = null
	if memory_static_available:
		memory_value = int(Performance.get_monitor(Performance.MEMORY_STATIC))
	return {
		"frame": frame_index,
		"elapsed_measurement_usec": Time.get_ticks_usec() - measurement_start_usec,
		"workload_time_usec": workload_time_usec,
		"process_time_ms": float(Performance.get_monitor(Performance.TIME_PROCESS)) * 1000.0,
		"physics_process_time_ms": float(Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)) * 1000.0,
		"memory_static_bytes": memory_value,
		"object_count": int(Performance.get_monitor(Performance.OBJECT_COUNT)),
		"node_count": int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)),
		"orphan_node_count": int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)),
		"owned_actor_count": actor_container.get_child_count(),
		"retained_node_count": leak_container.get_child_count(),
	}


func _capture_snapshot() -> Dictionary:
	var memory_value = null
	if memory_static_available:
		memory_value = int(Performance.get_monitor(Performance.MEMORY_STATIC))
	return {
		"memory_static_bytes": memory_value,
		"object_count": int(Performance.get_monitor(Performance.OBJECT_COUNT)),
		"node_count": int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)),
		"orphan_node_count": int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)),
		"owned_actor_count": actor_container.get_child_count(),
		"retained_node_count": leak_container.get_child_count(),
	}


func _build_result(scenario_duration_ms: float) -> Dictionary:
	var workload_values := _sample_values("workload_time_usec")
	var process_values := _sample_values("process_time_ms")
	var physics_values := _sample_values("physics_process_time_ms")
	var memory_values := _sample_values("memory_static_bytes", true)
	var object_values := _sample_values("object_count")
	var node_values := _sample_values("node_count")
	var orphan_values := _sample_values("orphan_node_count")
	var actor_values := _sample_values("owned_actor_count")
	var retained_values := _sample_values("retained_node_count")
	var memory_tolerance = null
	if memory_static_available:
		memory_tolerance = maxi(MEMORY_ABSOLUTE_TOLERANCE_BYTES, int(float(measurement_baseline.memory_static_bytes) * MEMORY_RELATIVE_TOLERANCE))

	var timing_summary := {
		"workload_time_usec": _timing_stats(workload_values),
		"process_time_ms": _timing_stats(process_values),
		"physics_process_time_ms": _timing_stats(physics_values),
	}
	var count_summary := {
		"memory_static_bytes": _series_stats(memory_values),
		"object_count": _series_stats(object_values),
		"node_count": _series_stats(node_values),
		"orphan_node_count": _series_stats(orphan_values),
		"owned_actor_count": _series_stats(actor_values),
		"retained_node_count": _series_stats(retained_values),
	}
	var measurement_duration_ms := float(measurement_end_usec - measurement_start_usec) / 1000.0
	var result := {
		"schema_version": 1,
		"scenario": scenario,
		"run_id": run_id,
		"godot_version": Engine.get_version_info().get("string", Engine.get_version_info().get("major", "unknown")),
		"seed": FIXED_SEED,
		"warmup_frames": WARMUP_FRAMES,
		"sample_frames": SAMPLE_FRAMES,
		"sampling_interval_frames": 1,
		"percentile_definition": PERCENTILE_DEFINITION,
		"metric_availability": {
			"memory_static_bytes": {
				"available": memory_static_available,
				"debug_only": true,
				"reason": "available when running a debug build with a positive MEMORY_STATIC monitor value" if memory_static_available else "runtime is not a debug build or MEMORY_STATIC did not report a positive value",
			},
		},
		"environment": _environment_metadata(),
		"scenario_config": {
			"actor_count": ACTOR_COUNT,
			"leak_interval_frames": LEAK_INTERVAL_FRAMES,
			"cpu_outer_iterations": CPU_OUTER_ITERATIONS,
			"cpu_inner_iterations": CPU_INNER_ITERATIONS,
		},
		"tolerances": {
			"healthy_object_count_growth": OBJECT_COUNT_TOLERANCE,
			"healthy_memory_growth_bytes": memory_tolerance,
			"memory_absolute_floor_bytes": MEMORY_ABSOLUTE_TOLERANCE_BYTES,
			"memory_relative_fraction": MEMORY_RELATIVE_TOLERANCE,
		},
		"measurement_baseline": measurement_baseline,
		"post_cleanup": post_cleanup_snapshot,
		"samples": samples,
		"summary": {
			"timing": timing_summary,
			"counts": count_summary,
			"post_cleanup_deltas": _snapshot_deltas(measurement_baseline, post_cleanup_snapshot),
			"retained_nodes": int(post_cleanup_snapshot.retained_node_count),
			"measurement_duration_ms": measurement_duration_ms,
			"scenario_duration_ms": scenario_duration_ms,
			"workload_checksum": workload_checksum,
		},
		# Common headline fields keep individual files convenient to inspect.
		"p95_process_time_ms": timing_summary.process_time_ms.p95,
		"p95_workload_time_usec": timing_summary.workload_time_usec.p95,
		"peak_node_count": count_summary.node_count.peak,
		"retained_nodes": int(post_cleanup_snapshot.retained_node_count),
		"scenario_duration_ms": scenario_duration_ms,
	}
	return result


func _environment_metadata() -> Dictionary:
	var version_info := Engine.get_version_info()
	return {
		"godot_version_info": version_info,
		"debug_build": OS.is_debug_build(),
		"os_name": OS.get_name(),
		"os_version": OS.get_version(),
		"distribution_name": OS.get_distribution_name(),
		"processor_name": OS.get_processor_name(),
		"processor_count": OS.get_processor_count(),
		"display_driver": DisplayServer.get_name(),
		"headless": DisplayServer.get_name() == "headless",
		"utc_started_at": Time.get_datetime_string_from_system(true, false),
		"benchmark_arguments": [
			"--scenario=%s" % scenario,
			"--run-id=%s" % run_id,
			"--output=%s" % ("<provided>" if not output_argument.is_empty() else "<default>"),
		],
	}


func _sample_values(key: String, skip_null := false) -> Array:
	var values: Array = []
	for sample in samples:
		var value = sample.get(key)
		if value == null and skip_null:
			continue
		values.append(value)
	return values


func _timing_stats(values: Array) -> Dictionary:
	if values.is_empty():
		return {"mean": null, "p50": null, "p95": null, "max": null}
	var total := 0.0
	var maximum := float(values[0])
	for value in values:
		total += float(value)
		maximum = maxf(maximum, float(value))
	return {
		"mean": total / values.size(),
		"p50": _nearest_rank(values, 0.50),
		"p95": _nearest_rank(values, 0.95),
		"max": maximum,
	}


func _series_stats(values: Array) -> Dictionary:
	if values.is_empty():
		return {"initial": null, "final": null, "peak": null, "delta": null}
	var peak_value := float(values[0])
	for value in values:
		peak_value = maxf(peak_value, float(value))
	return {
		"initial": values[0],
		"final": values[-1],
		"peak": peak_value,
		"delta": float(values[-1]) - float(values[0]),
	}


func _nearest_rank(values: Array, percentile: float) -> float:
	var ordered := values.duplicate()
	ordered.sort()
	var rank := clampi(int(ceil(percentile * ordered.size())), 1, ordered.size())
	return float(ordered[rank - 1])


func _snapshot_deltas(initial: Dictionary, final: Dictionary) -> Dictionary:
	var deltas := {}
	for key in ["memory_static_bytes", "object_count", "node_count", "orphan_node_count", "owned_actor_count", "retained_node_count"]:
		if initial.get(key) == null or final.get(key) == null:
			deltas[key] = null
		else:
			deltas[key] = float(final[key]) - float(initial[key])
	return deltas


func _resolve_output_path() -> String:
	var requested := output_argument
	if requested.is_empty():
		requested = "res://results/%s.json" % run_id
	elif requested.ends_with("/") or requested.ends_with("\\"):
		requested += "%s.json" % run_id
	elif not requested.to_lower().ends_with(".json"):
		requested = requested.path_join("%s.json" % run_id)
	return ProjectSettings.globalize_path(requested)


func _write_json_atomically(final_path: String, result: Dictionary) -> bool:
	var parent_directory := final_path.get_base_dir()
	var mkdir_error := DirAccess.make_dir_recursive_absolute(parent_directory)
	if mkdir_error != OK and mkdir_error != ERR_ALREADY_EXISTS:
		push_error("Could not create result directory %s (error %s)" % [parent_directory, mkdir_error])
		return false
	if FileAccess.file_exists(final_path):
		push_error("Refusing to overwrite existing result: %s" % final_path)
		return false
	var temporary_path := "%s.tmp.%s" % [final_path, OS.get_process_id()]
	var file := FileAccess.open(temporary_path, FileAccess.WRITE)
	if file == null:
		push_error("Could not open temporary result: %s" % FileAccess.get_open_error())
		return false
	file.store_string(JSON.stringify(result, "  "))
	file.flush()
	file.close()
	var rename_error := DirAccess.rename_absolute(temporary_path, final_path)
	if rename_error != OK:
		push_error("Could not rename temporary result (error %s)" % rename_error)
		DirAccess.remove_absolute(temporary_path)
		return false
	return true


func _fatal(message: String, exit_code: int) -> void:
	push_error(message)
	get_tree().quit(exit_code)
