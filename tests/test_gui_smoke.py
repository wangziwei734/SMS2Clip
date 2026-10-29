import shutil
import tempfile
import unittest
from pathlib import Path

from ntfy_clipboard.gui import NtfyClipboardApp


class GuiSmokeTests(unittest.TestCase):
    def test_app_constructs_recognizes_text_and_switches_language(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            shutil.copyfile("config.json", config_path)
            app = NtfyClipboardApp(config_path)
            try:
                app.withdraw()
                app.update_idletasks()
                app._recognize_test()
                self.assertIn("482913", app.test_result_var.get())
                app._toggle_language()
                app.update_idletasks()
                self.assertEqual(app.language, "en")
                self.assertIn("Connection", app.notebook.tab(0, "text"))
            finally:
                if app.tray_icon is not None:
                    app.tray_icon.stop()
                app.destroy()


if __name__ == "__main__":
    unittest.main()
