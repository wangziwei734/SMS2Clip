import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from SMS2Clip.config import Config
from SMS2Clip.gui import SMS2ClipApp
from SMS2Clip.history import HistoryStore


def write_test_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "server": "https://ntfy.sh",
                "topic": "test-topic",
                "state_file": "state.json",
                "log_file": "logs/test.log",
                "language": "zh-CN",
                "auto_copy_code": True,
            }
        ),
        encoding="utf-8",
    )


class GuiSmokeTests(unittest.TestCase):
    def test_app_constructs_recognizes_text_and_switches_language(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            write_test_config(config_path)
            app = SMS2ClipApp(config_path)
            try:
                app.withdraw()
                app.update_idletasks()
                app._recognize_test()
                self.assertIn("482913", app.test_result_var.get())
                self.assertEqual(app.connection_settings_content.winfo_manager(), "")
                self.assertEqual(
                    app.settings_toggle_button.cget("text"), "查看连接设置"
                )
                app._toggle_connection_settings()
                app.update_idletasks()
                self.assertEqual(
                    app.connection_settings_content.winfo_manager(), "pack"
                )
                self.assertEqual(
                    app.settings_toggle_button.cget("text"), "收起连接设置"
                )
                app._toggle_connection_settings()
                app.update_idletasks()
                self.assertEqual(app.connection_settings_content.winfo_manager(), "")
                self.assertTrue(app.auto_copy_code_var.get())
                app.auto_copy_code_var.set(False)
                app._on_auto_copy_change()
                self.assertFalse(app.auto_copy_code)
                self.assertFalse(Config.load(config_path).auto_copy_code)
                self.assertIn(app.startup_mode_var.get(), app._startup_mode_labels())
                with (
                    patch("SMS2Clip.gui.enable_startup") as enable_startup,
                    patch("SMS2Clip.gui.messagebox.askyesno", return_value=True),
                    patch.object(app, "_service_pid", return_value=1234),
                    patch.object(app, "after") as after,
                ):
                    app.startup_mode_var.set(app._t("startup.service"))
                    app._on_startup_mode_change()
                self.assertEqual(app.startup_mode, "service")
                after.assert_called_once_with(100, app._exit_app)
                self.assertEqual(
                    app.startup_hint_var.get(), app._t("startup.hint_service")
                )
                self.assertIn("--service", enable_startup.call_args.args[0])
                app._toggle_language()
                app.update_idletasks()
                self.assertEqual(app.language, "en")
                self.assertIn("Connection", app.notebook.tab(0, "text"))
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()

    def test_service_mode_exit_leaves_background_listener_running(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            write_test_config(config_path)
            app = SMS2ClipApp(config_path)
            app.withdraw()
            app.startup_mode = "service"
            exited = False
            try:
                with patch.object(app, "_stop_service") as stop_service:
                    app._exit_app()
                    exited = True
                stop_service.assert_not_called()
            finally:
                if not exited:
                    if app.tray_icon is not None:
                        app.tray_icon.stop()
                    app.destroy()

    def test_opening_manager_auto_starts_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            app = SMS2ClipApp(config_path)
            app.withdraw()
            try:
                with (
                    patch.object(app, "_service_pid", return_value=None),
                    patch.object(app, "_start_service") as start_service,
                ):
                    app._auto_start_if_needed()
                start_service.assert_called_once_with()
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()

    def test_existing_listener_is_not_started_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            app = SMS2ClipApp(config_path)
            app.withdraw()
            try:
                with (
                    patch.object(app, "_service_pid", return_value=1234),
                    patch.object(app, "_start_service") as start_service,
                ):
                    app._auto_start_if_needed()
                start_service.assert_not_called()
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()

    def test_auto_copy_change_restarts_a_running_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            write_test_config(config_path)
            app = SMS2ClipApp(config_path)
            app.withdraw()
            try:
                app.auto_copy_code_var.set(False)
                with (
                    patch.object(app, "_save_settings"),
                    patch.object(app, "_service_pid", return_value=1234),
                    patch.object(app, "_stop_service") as stop_service,
                    patch.object(app, "after") as after,
                ):
                    app._on_auto_copy_change()
                stop_service.assert_called_once_with()
                after.assert_called_once_with(500, app._start_service)
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()

    def test_save_connection_settings_restarts_running_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            write_test_config(config_path)
            app = SMS2ClipApp(config_path)
            app.withdraw()
            try:
                with (
                    patch.object(app, "_save_settings") as save_settings,
                    patch.object(app, "_service_pid", return_value=1234),
                    patch.object(app, "_stop_service") as stop_service,
                    patch.object(app, "after") as after,
                ):
                    app._save_connection_settings()
                save_settings.assert_called_once_with()
                stop_service.assert_called_once_with()
                after.assert_called_once_with(500, app._start_service)
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()

    def test_history_tab_shows_full_message_and_copies_detected_code(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            write_test_config(config_path)
            store = HistoryStore(Path(directory) / "history.json")
            store.add("通知\n您的快递已到达", None, "plain", "2026-10-30 10:00:00")
            store.add("短信\n验证码为 482913", "482913", "code", "2026-10-30 10:01:00")

            app = SMS2ClipApp(config_path)
            app.withdraw()
            try:
                app._refresh_history(force=True)
                rows = app.history_tree.get_children()
                self.assertEqual(len(rows), 2)

                app.history_tree.selection_set(rows[0])
                app._on_history_select()
                self.assertIn("验证码为 482913", app.history_detail.get("1.0", "end"))
                self.assertEqual(str(app.history_copy_button.cget("state")), "normal")

                with (
                    patch.object(app, "clipboard_clear"),
                    patch.object(app, "clipboard_append") as append,
                    patch.object(app, "update_idletasks"),
                ):
                    app._copy_history_code()
                append.assert_called_once_with("482913")

                app.history_tree.selection_set(rows[1])
                app._on_history_select()
                self.assertIn("您的快递已到达", app.history_detail.get("1.0", "end"))
                self.assertEqual(str(app.history_copy_button.cget("state")), "disabled")
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()

    def test_silent_mode_starts_service_then_closes_current_manager(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            write_test_config(config_path)
            app = SMS2ClipApp(config_path)
            app.withdraw()
            try:
                with (
                    patch.object(app, "_save_settings"),
                    patch("SMS2Clip.gui.enable_startup"),
                    patch("SMS2Clip.gui.messagebox.askyesno", return_value=True),
                    patch.object(app, "_service_pid", side_effect=[None, 1234]),
                    patch.object(app, "_start_service") as start_service,
                    patch.object(app, "after") as after,
                ):
                    app.startup_mode_var.set(app._t("startup.service"))
                    app._on_startup_mode_change()
                start_service.assert_called_once_with()
                after.assert_called_once_with(100, app._exit_app)
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()

    def test_cancel_silent_mode_confirmation_keeps_manager_open(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            write_test_config(config_path)
            app = SMS2ClipApp(config_path)
            app.withdraw()
            previous_mode = "manager"
            app.startup_mode = previous_mode
            try:
                with (
                    patch("SMS2Clip.gui.messagebox.askyesno", return_value=False),
                    patch("SMS2Clip.gui.enable_startup") as enable_startup,
                    patch.object(app, "_start_service") as start_service,
                    patch.object(app, "after") as after,
                ):
                    app.startup_mode_var.set(app._t("startup.service"))
                    app._on_startup_mode_change()
                self.assertEqual(app.startup_mode, previous_mode)
                self.assertEqual(
                    app.startup_mode_var.get(), app._startup_mode_label(previous_mode)
                )
                enable_startup.assert_not_called()
                start_service.assert_not_called()
                after.assert_not_called()
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()


if __name__ == "__main__":
    unittest.main()
