from __future__ import annotations

import re

FORBIDDEN_PATTERNS = (
    (r"buy[-\s]*now", "buy now"),
    (r"sell[-\s]*now", "sell now"),
    (r"buy\s+today", "buy today"),
    (r"sell\s+today", "sell today"),
    (r"buy\s+immediately", "buy immediately"),
    (r"sell\s+immediately", "sell immediately"),
    (r"지금\s*매수", "지금 매수"),
    (r"지금\s*매도", "지금 매도"),
    (r"매수하세요", "매수하세요"),
    (r"매도하세요", "매도하세요"),
)


class TonePolicyViolation(ValueError):
    pass


def ensure_allowed_text(text: str) -> str:
    for pattern, label in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise TonePolicyViolation(f"forbidden phrase detected: {label}")
    return text


def ensure_allowed_texts(texts: list[str]) -> list[str]:
    for text in texts:
        ensure_allowed_text(text)
    return texts
