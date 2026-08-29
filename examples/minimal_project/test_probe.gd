extends SceneTree

const Probe := preload("res://addons/performance_budget_guardian/performance_probe.gd")


func _init() -> void:
	_assert(Probe.is_safe_identifier("main_scene"), "valid profile rejected")
	_assert(not Probe.is_safe_identifier("../escape"), "unsafe profile accepted")
	_assert(not Probe.is_safe_identifier("bad profile"), "spaced profile accepted")
	_assert(Probe.parse_nonnegative_integer("0") == 0, "zero warmup rejected")
	_assert(Probe.parse_nonnegative_integer("600") == 600, "valid frame count rejected")
	_assert(Probe.parse_nonnegative_integer("-1") == null, "negative frame count accepted")
	_assert(Probe.parse_nonnegative_integer("x") == null, "nonnumeric frame count accepted")
	_assert(Probe.is_safe_output_path("res://results"), "safe output rejected")
	_assert(not Probe.is_safe_output_path("../results"), "relative escape accepted")
	_assert(not Probe.is_safe_output_path("C:/private/results"), "absolute output accepted")
	_assert(not Probe.is_safe_output_path("res://results//nested"), "empty output segment accepted")
	_assert(Probe.is_safe_source_revision("feature/probe-v1"), "safe revision rejected")
	_assert(not Probe.is_safe_source_revision("../private"), "unsafe revision accepted")
	_assert(not Probe.is_safe_source_revision("feature//probe"), "empty revision segment accepted")

	var collision_path := "res://results/probe-collision-test.json"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://results"))
	var sentinel := FileAccess.open(collision_path, FileAccess.WRITE)
	sentinel.store_string("preserve-me")
	sentinel.close()
	var probe := Probe.new()
	_assert(not probe._write_json_atomically(collision_path, {"changed": true}), "collision was overwritten")
	_assert(FileAccess.get_file_as_string(collision_path) == "preserve-me", "collision content changed")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(collision_path))
	probe.free()
	print("PBG_HELPER_TESTS=passed")
	quit(0)


func _assert(condition: bool, message: String) -> void:
	if condition:
		return
	push_error(message)
	quit(1)
