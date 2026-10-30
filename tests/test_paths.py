import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from SMS2Clip import paths


class PathsTests(unittest.TestCase):
    def test_source_mode_uses_project_config(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            with (
                patch.object(paths, "is_frozen", return_value=False),
                patch.object(paths, "app_dir", return_value=project),
            ):
                self.assertEqual(paths.default_config_path(), project / "config.json")

    def test_localcache_appdata_is_mapped_to_the_real_roaming_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            package_appdata = (
                base
                / "AppData"
                / "Local"
                / "Packages"
                / "OpenAI.Codex"
                / "LocalCache"
                / "Roaming"
            )
            with patch.dict(
                os.environ,
                {
                    "APPDATA": str(package_appdata),
                    "USERPROFILE": str(base),
                },
            ):
                self.assertEqual(
                    paths.app_data_dir(),
                    base / "AppData" / "Roaming" / "SMS2Clip",
                )
                self.assertEqual(
                    paths.start_menu_shortcut_path(),
                    base
                    / "AppData"
                    / "Roaming"
                    / "Microsoft"
                    / "Windows"
                    / "Start Menu"
                    / "Programs"
                    / "SMS2Clip.lnk",
                )

    def test_frozen_mode_uses_appdata_and_migrates_legacy_files(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            exe_dir = base / "exe"
            appdata = base / "appdata"
            exe_dir.mkdir()
            appdata.mkdir()
            (exe_dir / "config.json").write_text(
                '{"topic": "legacy"}', encoding="utf-8"
            )
            (exe_dir / "state.json").write_text(
                '{"last_id": "msg-1"}', encoding="utf-8"
            )

            with (
                patch.object(paths, "is_frozen", return_value=True),
                patch.object(paths, "app_dir", return_value=exe_dir),
                patch.dict(os.environ, {"APPDATA": str(appdata)}),
            ):
                target = paths.default_config_path()

            expected_dir = appdata / "SMS2Clip"
            self.assertEqual(target, expected_dir / "config.json")
            self.assertTrue(target.exists())
            self.assertTrue((expected_dir / "state.json").exists())
            self.assertIn("legacy", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
