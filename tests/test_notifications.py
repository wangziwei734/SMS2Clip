import unittest

from windows_toasts import ToastActivatedEventArgs, ToastDuration

from ntfy_clipboard.notifications import ToastNotifier


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
        scheduled = []
        notifier = ToastNotifier(
            language="zh-CN",
            toaster=toaster,
            clipboard_setter=clipboard_values.append,
            message_shower=lambda title, text: messages.append((title, text)),
            scheduler=lambda delay, callback: scheduled.append((delay, callback)),
        )
        return notifier, toaster, clipboard_values, messages, scheduled

    def test_shows_copied_toast_then_sms_toast(self):
        notifier, toaster, _, _, scheduled = self.make_notifier()

        notifier.notify_message("验证码为 123456，5分钟内有效。", "123456")

        self.assertEqual(len(toaster.toasts), 1)
        copied_toast = toaster.toasts[0]
        self.assertEqual(copied_toast.text_fields[0], "已复制验证码：123456")
        self.assertEqual(copied_toast.actions[0].content, "查看完整短信")
        self.assertEqual(copied_toast.duration, ToastDuration.Short)
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(scheduled[0][0], 8.0)

        scheduled[0][1]()

        self.assertEqual(len(toaster.toasts), 2)
        sms_toast = toaster.toasts[1]
        self.assertEqual(sms_toast.text_fields[0], "收到短信")
        self.assertIn("123456", sms_toast.text_fields[1])
        self.assertEqual(sms_toast.actions[0].content, "复制")

    def test_copy_button_copies_code_and_shows_confirmation(self):
        notifier, toaster, clipboard_values, _, scheduled = self.make_notifier()
        notifier.notify_message("验证码为 123456", "123456")
        scheduled[0][1]()

        sms_toast = toaster.toasts[1]
        sms_toast.on_activated(ToastActivatedEventArgs(arguments="copy_code"))

        self.assertEqual(clipboard_values, ["123456"])
        self.assertEqual(len(toaster.toasts), 3)
        self.assertEqual(toaster.toasts[-1].text_fields[0], "已复制验证码：123456")

    def test_view_full_button_opens_message_box(self):
        notifier, toaster, _, messages, _ = self.make_notifier()
        notifier.notify_message("完整短信内容 123456", "123456")
        copied_toast = toaster.toasts[0]

        copied_toast.on_activated(ToastActivatedEventArgs(arguments="view_full"))

        self.assertEqual(messages, [("完整短信", "完整短信内容 123456")])

    def test_message_without_code_only_shows_sms_toast(self):
        notifier, toaster, _, _, scheduled = self.make_notifier()

        notifier.notify_message("您的快递已到达", None)

        self.assertEqual(len(toaster.toasts), 1)
        self.assertEqual(toaster.toasts[0].actions, [])
        self.assertEqual(scheduled, [])


if __name__ == "__main__":
    unittest.main()
