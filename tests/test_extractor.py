import unittest

from SMS2Clip.extractor import extract_verification_code


class VerificationCodeExtractorTests(unittest.TestCase):
    def test_extracts_six_digit_code_after_chinese_keyword(self):
        text = "【某银行】验证码为 482913，5分钟内有效。"
        self.assertEqual(extract_verification_code(text), "482913")

    def test_extracts_four_digit_code_after_chinese_keyword(self):
        self.assertEqual(extract_verification_code("校验码：7391。"), "7391")

    def test_normalizes_full_width_digits(self):
        self.assertEqual(extract_verification_code("验证码：１２３４５６"), "123456")

    def test_extracts_code_with_spaces_between_digits(self):
        self.assertEqual(extract_verification_code("验证码：123 456"), "123456")

    def test_extracts_code_with_hyphen_between_digits(self):
        self.assertEqual(extract_verification_code("校验码：12-34"), "1234")

    def test_extracts_standalone_six_digit_code(self):
        self.assertEqual(extract_verification_code("123456"), "123456")

    def test_extracts_standalone_four_digit_code(self):
        self.assertEqual(extract_verification_code("1234"), "1234")

    def test_does_not_extract_six_digits_from_seven_digit_number(self):
        self.assertIsNone(extract_verification_code("1234567"))

    def test_does_not_extract_four_digits_from_seven_digit_number(self):
        self.assertIsNone(extract_verification_code("1234567"))

    def test_does_not_extract_from_long_number_with_keyword(self):
        self.assertIsNone(extract_verification_code("验证码 1234567"))

    def test_extracts_google_code_with_prefix(self):
        self.assertEqual(extract_verification_code("G-123456"), "123456")

    def test_extracts_google_code_with_grouped_hyphens(self):
        self.assertEqual(extract_verification_code("G-123-456"), "123456")

    def test_extracts_google_code_from_full_email_text(self):
        text = "Your Google verification code is G-123-456. Don't share it."
        self.assertEqual(extract_verification_code(text), "123456")

    def test_does_not_extract_from_google_like_long_number(self):
        self.assertIsNone(extract_verification_code("G-1234-567"))

    def test_prefers_keyword_code_over_order_number(self):
        text = "验证码 246810，订单号 135790，请勿泄露。"
        self.assertEqual(extract_verification_code(text), "246810")

    def test_ignores_year_without_code_keyword(self):
        self.assertIsNone(extract_verification_code("您的订单将于2026年10月29日送达"))

    def test_ignores_phone_number_fragment(self):
        self.assertIsNone(extract_verification_code("联系电话 13812345678"))

    def test_ignores_phone_number_with_spaces(self):
        self.assertIsNone(extract_verification_code("联系电话 138 1234 5678"))

    def test_returns_none_when_no_plausible_code_exists(self):
        self.assertIsNone(extract_verification_code("您的快递已到达菜鸟驿站"))

    def test_ignores_tracking_number_without_code_keyword(self):
        self.assertIsNone(extract_verification_code("快递单号 123456，预计明天送达"))

    def test_ignores_amount_and_still_finds_code(self):
        text = "订单金额 1234 元，验证码 987654。"
        self.assertEqual(extract_verification_code(text), "987654")

    def test_supports_english_keyword(self):
        self.assertEqual(
            extract_verification_code("Your verification code is 654321."),
            "654321",
        )

    def test_does_not_return_a_fragment_of_a_longer_number(self):
        self.assertIsNone(extract_verification_code("流水号：123456789012345"))


if __name__ == "__main__":
    unittest.main()
