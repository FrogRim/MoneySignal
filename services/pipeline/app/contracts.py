from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyText = Annotated[str, Field(min_length=1)]


class SignalDecision(str, Enum):
    REJECT = "reject"
    BRIEFING = "briefing"
    INSTANT_PUSH = "instant_push"


class ErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_TIMEOUT = "upstream_timeout"
    UPSTREAM_UNAVAILABLE = "upstream_unavailable"
    ANALYSIS_FAILED = "analysis_failed"
    INTERNAL_ERROR = "internal_error"


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str = Field(min_length=1)
    retryable: bool
    failed_agents: list[str] = Field(default_factory=list)
    trace_id: str = Field(min_length=1)


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


class AssetView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    market: str = Field(min_length=1)


class BrokerDeeplinkHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    broker: str = Field(min_length=1)
    symbol: str = Field(min_length=1)


class AgentVote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str = Field(min_length=1)
    stance: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    ref: str = Field(min_length=1)


class BrainGateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class BrainSignalCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    asset: AssetView
    signal_strength: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    reasons: list[NonEmptyText] = Field(min_length=2)
    risks: list[NonEmptyText] = Field(min_length=1)
    watch_action: str = Field(min_length=1)
    broker_deeplink_hint: BrokerDeeplinkHint
    agent_votes: list[AgentVote] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef]


class BrainEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: SignalDecision
    gate: BrainGateSummary
    signal_card: BrainSignalCard | None

    @model_validator(mode="after")
    def validate_signal_card_presence(self) -> "BrainEvaluationResult":
        if self.decision == SignalDecision.REJECT:
            if self.signal_card is not None:
                raise ValueError("signal_card must be null when decision is reject")
            return self

        if self.signal_card is None:
            raise ValueError(
                "signal_card is required when decision is briefing or instant_push",
            )

        return self


class SignalDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    decision: SignalDecision
    title: str = Field(min_length=1)
    asset: AssetView
    signal_strength: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    reasons: list[NonEmptyText] = Field(min_length=1)
    risks: list[NonEmptyText] = Field(min_length=1)
    watch_action: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    published_at: datetime
    broker_deeplink_hint: BrokerDeeplinkHint | None = None
    agent_votes: list[AgentVote] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class StoredSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal: SignalDetail
    source_candidate_id: str = Field(min_length=1)


class FeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SignalDetail]


class SignalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal: SignalDetail


class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    UNAUTHENTICATED = "unauthenticated"


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SessionStatus


class RebuildFeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processedCandidates: int = Field(ge=0)
    publishedSignals: int = Field(ge=0)
    rejectedCandidates: int = Field(ge=0)
