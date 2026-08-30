from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import workspace_paths


class WorkspacePathTests(unittest.TestCase):
    def test_existing_and_future_members_are_contained_and_relative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            existing = root / "results"
            existing.mkdir()

            resolved, relative = workspace_paths.resolve_workspace_member(
                root,
                "results/./capture.json",
                label="capture",
            )

            self.assertEqual(resolved, existing / "capture.json")
            self.assertEqual(relative, "results/capture.json")
            self.assertNotIn(str(root), relative)

    def test_windows_short_and_long_names_compare_by_identity(self) -> None:
        short_root = Path("C:/Users/RUNNER~1/AppData/Local/Temp/workspace")
        long_candidate = Path(
            "C:/Users/runneradmin/AppData/Local/Temp/workspace/results/capture.json"
        )
        long_root = long_candidate.parents[1]

        def samefile(left: os.PathLike[str], right: os.PathLike[str]) -> bool:
            return Path(left) == long_root and Path(right) == short_root

        with patch.object(Path, "exists", return_value=True):
            with patch.object(workspace_paths.os.path, "samefile", side_effect=samefile):
                self.assertTrue(
                    workspace_paths._is_workspace_ancestor(short_root, long_candidate)
                )

    def test_absolute_traversal_and_drive_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for supplied in (str(root), "../escape", "..\\escape", "C:\\escape"):
                with self.subTest(supplied=supplied):
                    with self.assertRaisesRegex(
                        workspace_paths.WorkspacePathError, "workspace-relative"
                    ):
                        workspace_paths.resolve_workspace_member(
                            root, supplied, label="member"
                        )

    def test_symlink_escape_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            container = Path(temporary)
            root = container / "workspace"
            outside = container / "outside"
            root.mkdir()
            outside.mkdir()
            link = root / "linked"
            try:
                os.symlink(outside, link, target_is_directory=True)
            except OSError:
                self.skipTest("directory symlinks are unavailable")

            with self.assertRaisesRegex(
                workspace_paths.WorkspacePathError, "remain inside"
            ):
                workspace_paths.resolve_workspace_member(
                    root.resolve(), "linked/proposal.json", label="proposal"
                )


if __name__ == "__main__":
    unittest.main()
