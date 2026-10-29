import unittest

from ntfy_clipboard.i18n import LANG_EN, LANG_ZH, normalize_language, tr


class I18nTests(unittest.TestCase):
    def test_normalizes_language_values(self):
        self.assertEqual(normalize_language("en-US"), LANG_EN)
        self.assertEqual(normalize_language("zh-CN"), LANG_ZH)
        self.assertEqual(normalize_language(None), LANG_ZH)

    def test_translates_status_and_tray_keys(self):
        self.assertEqual(tr(LANG_ZH, "status.running"), "正在监听")
        self.assertEqual(tr(LANG_EN, "status.running"), "Listening")
        self.assertEqual(tr(LANG_EN, "tray.open"), "Open manager")

    def test_shortcut_instructions_warn_that_automation_is_off_by_default(self):
        self.assertIn("默认是关闭的", tr(LANG_ZH, "shortcut.instructions"))
        self.assertIn("off by default", tr(LANG_EN, "shortcut.instructions"))


if __name__ == "__main__":
    unittest.main()
