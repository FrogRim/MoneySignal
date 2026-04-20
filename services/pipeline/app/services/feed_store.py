from __future__ import annotations

import json
from pathlib import Path

from app.contracts import SignalDetail, StoredSignal


def _signals_by_id(signals: list[StoredSignal]) -> dict[str, StoredSignal]:
    return {stored_signal.signal.id: stored_signal for stored_signal in signals}


def _list_feed(signals_by_id: dict[str, StoredSignal]) -> list[SignalDetail]:
    ordered_signals = sorted(
        signals_by_id.values(),
        key=lambda stored_signal: stored_signal.signal.published_at,
        reverse=True,
    )
    return [stored_signal.signal for stored_signal in ordered_signals]


def _read_signals(file_path: Path) -> dict[str, StoredSignal]:
    if not file_path.exists():
        return {}

    raw_content = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw_content, list):
        raise ValueError("feed store payload must be a JSON array")

    signals = [StoredSignal.model_validate(item) for item in raw_content]
    return _signals_by_id(signals)


class InMemoryFeedStore:
    def __init__(self) -> None:
        self._signals_by_id: dict[str, StoredSignal] = {}

    def replace_signals(self, signals: list[StoredSignal]) -> None:
        self._signals_by_id = _signals_by_id(signals)

    def list_feed(self) -> list[SignalDetail]:
        return _list_feed(self._signals_by_id)

    def get_signal(self, signal_id: str) -> SignalDetail | None:
        stored_signal = self._signals_by_id.get(signal_id)
        if stored_signal is None:
            return None

        return stored_signal.signal


class FileFeedStore:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._signals_by_id = _read_signals(file_path)

    def replace_signals(self, signals: list[StoredSignal]) -> None:
        self._signals_by_id = _signals_by_id(signals)
        self._persist()

    def list_feed(self) -> list[SignalDetail]:
        return _list_feed(self._signals_by_id)

    def get_signal(self, signal_id: str) -> SignalDetail | None:
        stored_signal = self._signals_by_id.get(signal_id)
        if stored_signal is None:
            return None

        return stored_signal.signal

    def _persist(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            stored_signal.model_dump(mode="json")
            for stored_signal in self._signals_by_id.values()
        ]
        temp_path = self._file_path.with_suffix(f"{self._file_path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self._file_path)
