from __future__ import annotations

from datetime import UTC, datetime

from app.contracts import AssetView, SignalDecision, SignalDetail, StoredSignal
from app.services.feed_store import FileFeedStore, InMemoryFeedStore


def build_signal(*, signal_id: str, published_at: datetime) -> StoredSignal:
    return StoredSignal(
        signal=SignalDetail(
            id=signal_id,
            decision=SignalDecision.BRIEFING,
            title=f"{signal_id} title",
            asset=AssetView(symbol="005930", name="삼성전자", market="KR"),
            signal_strength="watch",
            summary=f"{signal_id} summary",
            reasons=["reason 1", "reason 2"],
            risks=["risk 1"],
            watch_action="watch this",
            confidence=0.76,
            published_at=published_at,
        ),
        source_candidate_id=f"cand_{signal_id}",
    )


def test_list_feed_returns_newest_signal_first() -> None:
    store = InMemoryFeedStore()
    older = build_signal(
        signal_id="sig_001",
        published_at=datetime(2026, 4, 19, 8, 0, tzinfo=UTC),
    )
    newer = build_signal(
        signal_id="sig_002",
        published_at=datetime(2026, 4, 19, 9, 0, tzinfo=UTC),
    )

    store.replace_signals([older, newer])

    feed = store.list_feed()

    assert [item.id for item in feed] == ["sig_002", "sig_001"]


def test_get_signal_returns_none_for_missing_id() -> None:
    store = InMemoryFeedStore()

    assert store.get_signal("sig_missing") is None


def test_file_feed_store_persists_and_reloads_signals(tmp_path) -> None:
    file_path = tmp_path / "feed-store.json"
    store = FileFeedStore(file_path)
    newer = build_signal(
        signal_id="sig_002",
        published_at=datetime(2026, 4, 19, 9, 0, tzinfo=UTC),
    )
    older = build_signal(
        signal_id="sig_001",
        published_at=datetime(2026, 4, 19, 8, 0, tzinfo=UTC),
    )

    store.replace_signals([older, newer])

    reloaded_store = FileFeedStore(file_path)

    assert [item.id for item in reloaded_store.list_feed()] == ["sig_002", "sig_001"]
    assert reloaded_store.get_signal("sig_001") is not None
