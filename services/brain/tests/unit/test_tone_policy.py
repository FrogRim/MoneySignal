from __future__ import annotations

import pytest

from app.policies.tone import (
    TonePolicyViolation,
    ensure_allowed_text,
    ensure_allowed_texts,
)


def test_ensure_allowed_text_accepts_non_directive_opinion_style_copy() -> None:
    text = "삼성전자 흐름이 좋아 보이지만, 거래대금이 유지되는지 조금 더 지켜보세요."

    result = ensure_allowed_text(text)

    assert result == text


def test_ensure_allowed_text_rejects_direct_trading_phrase_case_insensitively() -> None:
    with pytest.raises(TonePolicyViolation, match="buy"):
        ensure_allowed_text("Momentum looks strong here. BUY NOW.")


@pytest.mark.parametrize(
    ("text", "pattern"),
    [
        ("Momentum still looks good, so buy-now.", "buy[-\\s]*now"),
        ("This could keep running, so buy today.", "buy\\s+today"),
        ("거래량이 붙고 있으니 지금  매수 해보세요.", "지금\\s*매수"),
        ("상승 추세가 이어지면 매수하세요.", "매수하세요"),
    ],
)
def test_ensure_allowed_text_rejects_directive_variants(
    text: str,
    pattern: str,
) -> None:
    with pytest.raises(TonePolicyViolation, match=pattern):
        ensure_allowed_text(text)


def test_ensure_allowed_texts_rejects_any_forbidden_text_in_collection() -> None:
    with pytest.raises(TonePolicyViolation, match="sell now"):
        ensure_allowed_texts(
            [
                "단기 변동성이 커질 수 있으니 추세를 계속 확인해보세요.",
                "Sell now if the volume fades.",
            ],
        )
