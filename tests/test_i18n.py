import unittest

from SMS2Clip.i18n import LANG_EN, LANG_ZH, normalize_language, tr


class I18nTests(unittest.TestCase):
    def test_normalizes_language_values(self):
        self.assertEqual(normalize_language("en-US"), LANG_EN)
        self.assertEqual(normalize_language("zh-CN"), LANG_ZH)
        self.assertEqual(normalize_language(None), LANG_ZH)

    def test_startup_mode_labels(self):
        self.assertEqual(tr(LANG_ZH, "startup.manual"), "不自动启动")
        self.assertEqual(tr(LANG_ZH, "startup.manager"), "开机后在托盘运行")
        self.assertEqual(tr(LANG_ZH, "startup.service"), "开机后静默运行（无托盘）")
        self.assertIn("托盘图标", tr(LANG_ZH, "startup.hint_manager"))
        self.assertIn("保留后台监听", tr(LANG_ZH, "startup.hint_service"))
        self.assertEqual(tr(LANG_EN, "startup.service"), "Run silently after sign-in")
        self.assertIn(
            "listening in the background", tr(LANG_EN, "startup.hint_service")
        )

    def test_connection_settings_save_label(self):
        self.assertEqual(tr(LANG_ZH, "button.save_connection"), "保存连接设置")
        self.assertEqual(
            tr(LANG_EN, "button.save_connection"), "Save connection settings"
        )

    def test_connection_settings_toggle_labels(self):
        self.assertEqual(tr(LANG_ZH, "settings.show"), "查看连接设置")
        self.assertEqual(tr(LANG_ZH, "settings.hide"), "收起连接设置")
        self.assertEqual(tr(LANG_EN, "settings.show"), "Show connection settings")
        self.assertEqual(tr(LANG_EN, "settings.hide"), "Hide connection settings")

    def test_translates_status_and_tray_keys(self):
        self.assertEqual(tr(LANG_ZH, "status.running"), "正在监听")
        self.assertEqual(tr(LANG_EN, "status.running"), "Listening")
        self.assertEqual(tr(LANG_EN, "tray.open"), "Open manager")

    def test_shortcut_instructions_warn_that_automation_is_off_by_default(self):
        self.assertIn("默认是关闭的", tr(LANG_ZH, "shortcut.instructions"))
        self.assertIn("off by default", tr(LANG_EN, "shortcut.instructions"))

    def test_auto_copy_option_labels_match_product_wording(self):
        self.assertEqual(
            tr(LANG_ZH, "checkbox.auto_copy_code"),
            "收到 iPhone 短信时自动复制验证码",
        )
        self.assertEqual(
            tr(LANG_EN, "checkbox.auto_copy_code"),
            "Auto-copy verification code",
        )


if __name__ == "__main__":
    unittest.main()
