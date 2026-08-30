from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addons/performance_budget_guardian"
FIXTURES = ROOT / "tests/fixtures/editor_dock"


class EditorMainScreenContractTests(unittest.TestCase):
    def test_plugin_uses_exact_godot_4_5_main_screen_lifecycle(self) -> None:
        source = (ADDON / "plugin.gd").read_text(encoding="utf-8")
        self.assertIn("EditorInterface.get_editor_main_screen().add_child(_main_screen)", source)
        self.assertIn("func _has_main_screen() -> bool:", source)
        self.assertIn('func _get_plugin_name() -> String:', source)
        self.assertIn('return "Guardian"', source)
        self.assertIn("func _get_plugin_icon() -> Texture2D:", source)
        self.assertIn("func _make_visible(visible: bool) -> void:", source)
        self.assertIn("parent.remove_child(_main_screen)", source)
        self.assertLess(source.index("parent.remove_child(_main_screen)"), source.index("_main_screen.free()"))
        for forbidden in (
            "add_control_to_dock",
            "remove_control_from_docks",
            "DOCK_SLOT_",
            "add_dock(",
            "remove_dock(",
            "set_main_screen_editor",
        ):
            self.assertNotIn(forbidden, source)
        self.assertFalse((ADDON / "performance_guardian_dock.gd").exists())

    def test_addon_version_and_read_only_boundary(self) -> None:
        manifest = (ADDON / "plugin.cfg").read_text(encoding="utf-8")
        probe = (ADDON / "performance_probe.gd").read_text(encoding="utf-8")
        main_screen = (ADDON / "performance_guardian_main_screen.gd").read_text(encoding="utf-8").lower()
        reader = (ADDON / "evidence_reader.gd").read_text(encoding="utf-8").lower()
        self.assertIn('version="1.2.0"', manifest)
        self.assertIn('ADDON_VERSION := "1.2.0"', probe)
        for forbidden in ("os.execute", "subprocess", "openai", "httpclient", "httprequest"):
            self.assertNotIn(forbidden, main_screen)
            self.assertNotIn(forbidden, reader)

    def test_schema_specific_ordering_never_uses_filesystem_time(self) -> None:
        reader = (ADDON / "evidence_reader.gd").read_text(encoding="utf-8")
        lowered = reader.lower()
        self.assertIn('data.get("ended_at_utc")', reader)
        self.assertIn('"timestamped": false', reader)
        for forbidden in ("get_modified_time", "mtime", "creation_time", "created_at"):
            self.assertNotIn(forbidden, lowered)

    def test_project_containment_scan_and_limits_are_explicit(self) -> None:
        reader = (ADDON / "evidence_reader.gd").read_text(encoding="utf-8")
        main_screen = (ADDON / "performance_guardian_main_screen.gd").read_text(encoding="utf-8")
        self.assertIn("MAX_EVIDENCE_FILES := 1000", reader)
        self.assertIn("MAX_EVIDENCE_BYTES := 8 * 1024 * 1024", reader)
        self.assertIn("directory.is_link(name)", reader)
        self.assertIn('FileDialog.ACCESS_RESOURCES', main_screen)
        self.assertIn('"res://results"', main_screen)
        self.assertIn('"res://.performance-guardian"', main_screen)

    def test_tracked_presentation_fixtures_cover_all_evidence_kinds(self) -> None:
        names = {
            "capture-newer.json",
            "capture-older.json",
            "capture-invalid-time.json",
            "guardian-report.json",
            "calibration-report.json",
        }
        self.assertEqual({path.name for path in FIXTURES.glob("*.json")}, names)
        loaded = {name: json.loads((FIXTURES / name).read_text(encoding="utf-8")) for name in names}
        self.assertEqual(loaded["capture-newer.json"]["ended_at_utc"], "2026-08-30T12:00:00Z")
        self.assertEqual(loaded["capture-older.json"]["ended_at_utc"], "2026-08-30T11:00:00Z")
        self.assertNotIn("ended_at_utc", loaded["guardian-report.json"])
        self.assertNotIn("generated_at_utc", loaded["calibration-report.json"])
        self.assertEqual(loaded["guardian-report.json"]["authoritative_exit_code"], 1)
        self.assertFalse(loaded["calibration-report.json"]["calibration"]["proposal_authoritative"])

    def test_main_screen_presents_failures_and_safe_project_evidence_actions(self) -> None:
        source = (ADDON / "performance_guardian_main_screen.gd").read_text(encoding="utf-8")
        self.assertIn("Failed deterministic rules", source)
        self.assertIn("Proposal only—not an enforced verdict.", source)
        self.assertIn("EditorInterface.get_file_system_dock().navigate_to_path", source)
        self.assertIn("DisplayServer.clipboard_set(_selected_path)", source)
        self.assertIn("MAX_VISIBLE_EVIDENCE := 20", source)


if __name__ == "__main__":
    unittest.main()
