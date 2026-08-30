extends SceneTree

const Reader := preload("res://addons/performance_budget_guardian/evidence_reader.gd")
const PASS_MARKER := "res://.godot/pbg_editor_main_screen_tests_passed.txt"

var _failed := false


func _init() -> void:
	call_deferred("_run_tests")


func _run_tests() -> void:
	var newer := Reader.parse_text("res://results/newer.json", JSON.stringify(_capture("2026-08-30T12:00:00Z", "newer")))
	var older := Reader.parse_text("res://results/older.json", JSON.stringify(_capture("2026-08-30T11:00:00Z", "older")))
	var invalid := Reader.parse_text("res://results/invalid.json", JSON.stringify(_capture("2026-02-31T12:00:00Z", "invalid")))
	var guardian := Reader.parse_text("res://.performance-guardian/guardian-report.json", JSON.stringify(_guardian_report()))
	var calibration := Reader.parse_text("res://.performance-guardian/calibration-report.json", JSON.stringify(_calibration_report()))
	_assert(newer.valid and older.valid, "valid captures were rejected")
	_assert(not invalid.valid, "invalid calendar timestamp was accepted")
	_assert(guardian.valid, "Guardian report was rejected: %s" % guardian.get("reason", "unknown"))
	if guardian.valid:
		_assert(guardian.failed_rules.size() == 1, "Guardian failure was not parsed")
		if guardian.failed_rules.size() == 1:
			_assert(guardian.failed_rules[0].relative_failed, "relative failure was not preserved")
	_assert(calibration.valid and calibration.status == "Proposal only", "calibration proposal was not labeled")
	_assert(not guardian.timestamped and not calibration.timestamped, "untimestamped report gained an invented time")
	var ordered: Array[Dictionary] = [guardian, older, calibration, newer, invalid]
	Reader.sort_evidence(ordered)
	_assert(ordered[0].run_id == "newer" and ordered[1].run_id == "older", "capture timestamp ordering failed")
	_assert(ordered[2].kind == "calibration_report" and ordered[3].kind == "guardian_report", "untimestamped report ordering failed")
	_assert(not ordered[4].valid, "invalid evidence was not placed last")
	_assert(not Reader.is_safe_project_path("C:/private/report.json"), "absolute path was accepted")
	_assert(not Reader.is_safe_project_path("res://results/../private.json"), "path traversal was accepted")
	if _failed:
		quit(1)
	else:
		var marker := FileAccess.open(PASS_MARKER, FileAccess.WRITE)
		if marker == null:
			push_error("could not write editor main-screen test marker")
			quit(1)
			return
		marker.store_string("passed")
		marker.close()
		print("PBG_EDITOR_MAIN_SCREEN_TESTS=passed")
		quit(0)


func _capture(timestamp: String, run_id: String) -> Dictionary:
	return {
		"result_type": "performance_budget_guardian_capture",
		"schema_version": 1,
		"addon": {"name": "Performance Budget Guardian", "version": "1.1.0"},
		"profile": "main_scene",
		"run_id": run_id,
		"godot_version": "4.5.1.stable.official.f62fdbde1",
		"ended_at_utc": timestamp,
		"metric_availability": {"memory_static_bytes": {"available": false}},
		"samples": [{"sample_index": 1}],
		"summary": {
			"timing": {"process_time_ms": {"p95": 1.0}},
			"counts": {"object_count": {"peak": 10}, "node_count": {"peak": 3}},
		},
		"known_limitations": ["Headless capture."],
	}


func _guardian_report() -> Dictionary:
	return {
		"schema_version": 2,
		"deterministic_status": "budget_failed",
		"validator": {"status": "passed"},
		"budget": {
			"status": "failed",
			"results": [{
				"budget_id": "process",
				"profile": "main_scene",
				"metric": "median_p95_process_time",
				"measured_value": 2.5,
				"maximum_value": 2.0,
				"unit": "ms",
				"status": "failed",
			}],
			"limitations": [],
		},
		"comparison": {
			"status": "failed",
			"results": [{
				"budget_id": "process",
				"profile": "main_scene",
				"metric": "median_p95_process_time",
				"unit": "ms",
				"baseline_value": 1.5,
				"candidate_value": 2.5,
				"delta": 1.0,
				"increase_percent": 66.6667,
				"absolute": {"maximum": 2.0, "status": "failed"},
				"relative": {"maximum_increase_percent": 20.0, "status": "failed"},
				"status": "failed",
			}],
		},
		"authoritative_exit_code": 1,
		"authoritative_exit_reason": "Validation passed, but one or more configured budgets failed.",
	}


func _calibration_report() -> Dictionary:
	return {
		"report_type": "performance_budget_calibration",
		"schema_version": 1,
		"status": "proposal_generated",
		"validator": {"status": "passed", "validated_file_count": 5},
		"calibration": {"proposal_authoritative": false},
		"recommendations": [{
			"budget_id": "process",
			"profile": "main_scene",
			"metric": "median_p95_process_time",
			"unit": "ms",
			"observed_value": 1.0,
			"proposed_maximum": 1.5,
			"relative_allowance_percent": 20.0,
		}],
		"limitations": [],
	}


func _assert(condition: bool, message: String) -> void:
	if condition:
		return
	_failed = true
	push_error(message)
