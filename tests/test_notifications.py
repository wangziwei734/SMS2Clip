import unittest
from unittest.mock import patch

from windows_toasts import ToastActivatedEventArgs

from SMS2Clip.notifications import (
    APP_AUMID,
    APP_DISPLAY_NAME,
    ToastNotifier,
    register_toast_identity,
)


class FakeToaster:
    def __init__(self):
        self.toasts = []
        self.cleared = False

    def show_toast(self, toast):
        self.toasts.append(toast)

    def clear_toasts(self):
        self.cleared = True


class ToastNotifierTests(unittest.TestCase):
    def make_notifier(self):
        toaster = FakeToaster()
        clipboard_values = []
        messages = []
        notifier = ToastNotifier(
            language="zh-CN",
            toaster=toaster,
            clipboard_setter=clipboard_values.append,
            message_shower=lambda title, text: messages.append((title, text)),
        )
        return notifier, toaster, clipboard_values, messages

    def test_notification_shows_full_sms_with_copy_button(self):
        notifier, toaster, _, _ = self.make_notifier()

        notifier.notify_message("验证码为 123456，5分钟内有效。", "123456")

        self.assertEqual(len(toaster.toasts), 1)
        sms_toast = toaster.toasts[0]
        self.assertEqual(sms_toast.text_fields[0], "收到短信")
        self.assertIn("123456", sms_toast.text_fields[1])
        self.assertEqual(sms_toast.actions[0].content, "复制")

    def test_copy_button_copies_code_without_replacing_full_sms_notification(self):
        notifier, toaster, clipboard_values, _ = self.make_notifier()
        notifier.notify_message("验证码为 123456", "123456")

        sms_toast = toaster.toasts[0]
        sms_toast.on_activated(ToastActivatedEventArgs(arguments="copy_code"))

        self.assertEqual(clipboard_values, ["123456"])
        self.assertEqual(len(toaster.toasts), 1)
        self.assertEqual(toaster.toasts[0].text_fields[0], "收到短信")

    def test_clicking_notification_body_opens_full_message(self):
        notifier, toaster, _, messages = self.make_notifier()
        notifier.notify_message("完整短信内容 123456", "123456")

        toaster.toasts[0].on_activated(ToastActivatedEventArgs(arguments=""))

        self.assertEqual(messages, [("完整短信", "完整短信内容 123456")])

    def test_message_without_code_only_shows_sms_toast_without_copy_button(self):
        notifier, toaster, _, _ = self.make_notifier()

        notifier.notify_message("您的快递已到达", None)

        self.assertEqual(len(toaster.toasts), 1)
        self.assertEqual(toaster.toasts[0].text_fields[0], "收到短信")
        self.assertEqual(toaster.toasts[0].actions, [])

    def test_full_message_dialog_requests_foreground_without_topmost(self):
        notifier, _, _, _ = self.make_notifier()

        with patch(
            "SMS2Clip.notifications.ctypes.windll.user32.MessageBoxW",
            return_value=1,
        ) as message_box:
            notifier._show_message_box("完整短信", "验证码为 123456")

        flags = message_box.call_args.args[3]
        self.assertTrue(flags & 0x00010000)
        self.assertFalse(flags & 0x00040000)

    def test_default_toaster_uses_sms2clip_notification_identity(self):
        with (
            patch(
                "SMS2Clip.notifications.register_toast_identity"
            ) as register_identity,
            patch("SMS2Clip.notifications.InteractableWindowsToaster") as toaster_type,
            patch("SMS2Clip.notifications.sys.platform", "win32"),
        ):
            ToastNotifier()

        register_identity.assert_called_once_with()
        toaster_type.assert_called_once_with(APP_DISPLAY_NAME, APP_AUMID)

    def test_toast_identity_registers_start_menu_shortcut(self):
        with patch(
            "SMS2Clip.notifications._register_start_menu_shortcut"
        ) as register_shortcut:
            register_toast_identity()

        register_shortcut.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
