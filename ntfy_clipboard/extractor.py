"""Extract a likely 4- or 6-digit verification code from an SMS message."""

from __future__ import annotations

import re
import unicodedata


_KEYWORDS = (
    r"验证码",
    r"校验码",
    r"动态码",
    r"确认码",
    r"激活码",
    r"安全码",
    r"登录码",
    r"短信码",
    r"一次性密码",
    r"verification\s+code",
    r"security\s+code",
    r"passcode",
    r"otp",
    r"(?<![a-z])code(?![a-z])",
)
_KEYWORD_RE = re.compile(r"(?:" + "|".join(_KEYWORDS) + r")", re.IGNORECASE)
_KEYWORD_BEFORE_RE = re.compile(
    r"(?:" + "|".join(_KEYWORDS) + r")\s*(?:为|是|is|:)?\s*$",
    re.IGNORECASE,
)
_CANDIDATE_RE = re.compile(r"(?<!\d)(\d{4,6})(?!\d)")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[\s-]?)?1[3-9]\d[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_DATE_OR_TIME_RE = re.compile(
    r"(?<!\d)(?:19|20)\d{2}\s*(?:年|[-/.])\s*\d{1,2}\s*(?:月|[-/.])\s*\d{1,2}(?!\d)"
)
_AMOUNT_SUFFIX_RE = re.compile(
    r"^\s*(?:元|块|圆|%|％|折|岁|克|千克|公斤|米|公里|人|个|次|单|号|条|天|小时|分钟|秒)"
)
_ORDER_PREFIX_RE = re.compile(
    r"(?:订单号|订单编号|流水号|编号|快递单号|运单号|物流单号|快递号|商品编号|会员号|卡号|取件码|提货码|手机号|电话|金额|价格|日期|时间|序号)\s*[:：]?\s*$"
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"(?<=\d)[ \t\u00a0-]+(?=\d)", "", normalized)


def _is_in_phone_number(text: str, start: int, end: int) -> bool:
    return any(
        match.start() <= start and end <= match.end()
        for match in _PHONE_RE.finditer(text)
    )


def _score_candidate(text: str, match: re.Match[str]) -> int:
    code = match.group(1)
    start, end = match.span(1)
    before = text[max(0, start - 24) : start]
    after = text[end : end + 12]

    keyword_before = bool(_KEYWORD_BEFORE_RE.search(before))
    keyword_nearby = bool(_KEYWORD_RE.search(before[-16:])) or bool(
        _KEYWORD_RE.search(after[:12])
    )

    score = 10 if len(code) == 6 else 5
    if keyword_before:
        score += 100
    elif keyword_nearby:
        score += 40

    if (
        re.fullmatch(r"(?:19|20)\d{2}", code)
        and not keyword_before
        and not keyword_nearby
    ):
        score -= 80

    if _ORDER_PREFIX_RE.search(before):
        score -= 60

    if _AMOUNT_SUFFIX_RE.search(after):
        score -= 60

    if _is_in_phone_number(text, start, end):
        score -= 200

    if _DATE_OR_TIME_RE.search(text[max(0, start - 8) : min(len(text), end + 8)]):
        score -= 100

    return score


def extract_verification_code(text: str) -> str | None:
    """Return the most likely verification code, or ``None`` if none is plausible."""

    if not text:
        return None

    normalized = _normalize(text)
    candidates = list(_CANDIDATE_RE.finditer(normalized))
    if not candidates:
        return None

    scored = [
        (candidate, _score_candidate(normalized, candidate)) for candidate in candidates
    ]
    scored = [(candidate, score) for candidate, score in scored if score > 0]
    if not scored:
        return None

    best_candidate, _ = max(scored, key=lambda item: (item[1], -item[0].start()))
    return best_candidate.group(1)
