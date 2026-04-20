from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from httpx import AsyncBaseTransport, AsyncClient, ConnectError, TimeoutException
from pydantic import ValidationError

from app.contracts import (
    BrainEvaluationResult,
    ErrorEnvelope,
    FeedResponse,
    RebuildFeedResponse,
    SessionResponse,
    SessionStatus,
    SignalDetail,
    SignalResponse,
    StoredSignal,
)
from app.services.feed_store import FileFeedStore

app = FastAPI(title="MoneySignal Pipeline", version="0.1.0")
_FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "candidates.json"
_LOCAL_PIPELINE_ENVS = {"local", "demo", "development", "test"}


def feed_store_path() -> Path:
    configured_path = os.getenv("PIPELINE_FEED_STORE_PATH", "").strip()
    if configured_path:
        return Path(configured_path)

    return Path.home() / ".moneysignal" / "pipeline" / "feed-store.json"


_store = FileFeedStore(feed_store_path())


class BrainOperationalError(RuntimeError):
    pass


def pipeline_env() -> str:
    return os.getenv("PIPELINE_ENV", "production").strip().lower() or "production"


def internal_rebuild_token() -> str:
    return os.getenv("PIPELINE_INTERNAL_REBUILD_TOKEN", "").strip()


def brain_base_url() -> str:
    return os.getenv("PIPELINE_BRAIN_BASE_URL", "").strip().rstrip("/")


def build_brain_transport() -> AsyncBaseTransport | None:
    return None


def session_status() -> SessionStatus:
    raw_status = os.getenv("PIPELINE_SESSION_STATUS", "").strip().lower()
    if raw_status == SessionStatus.EXPIRED.value:
        return SessionStatus.EXPIRED
    if raw_status == SessionStatus.UNAUTHENTICATED.value:
        return SessionStatus.UNAUTHENTICATED
    return SessionStatus.ACTIVE


def allow_internal_rebuild(request_token: str | None) -> bool:
    env_name = pipeline_env()
    if env_name in _LOCAL_PIPELINE_ENVS:
        return True

    configured_token = internal_rebuild_token()
    if not configured_token or request_token is None:
        return False

    return compare_digest(request_token, configured_token)


@app.post("/internal/rebuild-feed", response_model=RebuildFeedResponse)
async def rebuild_feed(
    x_pipeline_internal_token: Annotated[str | None, Header()] = None,
) -> RebuildFeedResponse | JSONResponse:
    if not allow_internal_rebuild(x_pipeline_internal_token):
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "forbidden",
                    "message": "internal rebuild is not allowed",
                },
            },
        )
    fixtures = load_candidate_fixtures()
    published_signals: list[StoredSignal] = []
    rejected_candidates = 0

    for index, candidate_event in enumerate(fixtures):
        try:
            brain_result = await evaluate_candidate_event(candidate_event)
        except (ValidationError, BrainOperationalError):
            rejected_candidates += 1
            continue

        if brain_result.signal_card is None:
            rejected_candidates += 1
            continue

        published_signals.append(
            build_stored_signal(
                candidate_event=candidate_event,
                brain_result=brain_result,
                publish_order=index,
            ),
        )

    _store.replace_signals(published_signals)
    return RebuildFeedResponse(
        processedCandidates=len(fixtures),
        publishedSignals=len(published_signals),
        rejectedCandidates=rejected_candidates,
    )


@app.get("/session", response_model=SessionResponse)
def get_session() -> SessionResponse:
    return SessionResponse(status=session_status())


@app.get("/feed", response_model=FeedResponse)
def get_feed() -> FeedResponse:
    return FeedResponse(items=_store.list_feed())


@app.get("/signals/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: str) -> SignalResponse | JSONResponse:
    signal = _store.get_signal(signal_id)
    if signal is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "not_found",
                    "message": "signal not found",
                },
            },
        )

    return SignalResponse(signal=signal)


def load_candidate_fixtures() -> list[dict[str, Any]]:
    if not _FIXTURE_PATH.exists():
        return []

    raw_content = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw_content, list):
        raise ValueError("candidate fixtures must be a JSON array")

    validated: list[dict[str, Any]] = []
    for candidate in raw_content:
        if not isinstance(candidate, dict):
            raise ValueError("candidate fixture entries must be JSON objects")
        validated.append(candidate)

    return validated


async def evaluate_candidate_event(
    candidate_event: dict[str, Any],
) -> BrainEvaluationResult:
    base_url = brain_base_url()
    if base_url:
        try:
            async with AsyncClient(
                base_url=base_url,
                transport=build_brain_transport(),
            ) as client:
                response = await client.post(
                    "/v1/signals/evaluate",
                    json=candidate_event,
                )
        except TimeoutException as exc:
            raise BrainOperationalError("brain evaluation timed out") from exc
        except ConnectError as exc:
            raise BrainOperationalError("brain evaluation unavailable") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BrainOperationalError("brain returned invalid JSON") from exc

        if response.is_error:
            error = ErrorEnvelope.model_validate(payload).error
            raise BrainOperationalError(
                f"brain evaluation failed: {error.code.value}"
            )

        return BrainEvaluationResult.model_validate(payload)

    metadata = candidate_event.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("candidate_event.metadata must be an object")

    stub_agent_outputs = metadata.get("stub_agent_outputs")
    if not isinstance(stub_agent_outputs, dict):
        raise ValueError(
            "candidate_event.metadata.stub_agent_outputs must be an object",
        )

    brain_result = stub_agent_outputs.get("brain")
    if not isinstance(brain_result, dict):
        raise RuntimeError("brain stub output is not configured for this candidate")

    return BrainEvaluationResult.model_validate(brain_result)


def build_stored_signal(
    *,
    candidate_event: dict[str, Any],
    brain_result: BrainEvaluationResult,
    publish_order: int,
) -> StoredSignal:
    signal_card = brain_result.signal_card
    if signal_card is None:
        raise ValueError("signal_card is required to build a stored signal")

    event_ts = datetime.fromisoformat(str(candidate_event["event_ts"]))
    published_at = event_ts.astimezone(UTC) + timedelta(microseconds=publish_order)
    signal = SignalDetail.model_validate(
        {
            "id": signal_card.id,
            "decision": brain_result.decision,
            "title": signal_card.title,
            "asset": signal_card.asset,
            "signal_strength": signal_card.signal_strength,
            "summary": signal_card.summary,
            "reasons": signal_card.reasons,
            "risks": signal_card.risks,
            "watch_action": signal_card.watch_action,
            "confidence": signal_card.confidence,
            "published_at": published_at,
            "broker_deeplink_hint": signal_card.broker_deeplink_hint,
            "agent_votes": signal_card.agent_votes,
            "evidence_refs": signal_card.evidence_refs,
        },
    )
    return StoredSignal(
        signal=signal,
        source_candidate_id=str(candidate_event["candidate_id"]),
    )
