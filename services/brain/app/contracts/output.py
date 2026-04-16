from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts.input import AssetInput

NonEmptyText = Annotated[str, Field(min_length=1)]


class SignalDecision(str, Enum):
    REJECT = "reject"
    BRIEFING = "briefing"
    INSTANT_PUSH = "instant_push"


class GateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(pattern=r"^(market_event|news|flow)$")
    ref: str = Field(min_length=1)


class BrokerDeeplinkHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    broker: str = Field(pattern=r"^toss_securities$")
    symbol: str = Field(min_length=1)


class AgentStance(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"


class AgentVote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str = Field(min_length=1)
    stance: AgentStance
    confidence: float = Field(ge=0.0, le=1.0)


class SignalCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    asset: AssetInput
    signal_strength: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    reasons: list[NonEmptyText] = Field(min_length=2)
    risks: list[NonEmptyText] = Field(min_length=1)
    watch_action: str = Field(min_length=1)
    broker_deeplink_hint: BrokerDeeplinkHint
    agent_votes: list[AgentVote] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef]


class EvaluateSignalSuccessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: SignalDecision
    gate: GateSummary
    signal_card: SignalCard | None

    @model_validator(mode="after")
    def validate_signal_card_presence(self) -> "EvaluateSignalSuccessResponse":
        if self.decision == SignalDecision.REJECT:
            if self.signal_card is not None:
                raise ValueError("signal_card must be null when decision is reject")
            return self

        if self.signal_card is None:
            raise ValueError(
                "signal_card is required when decision is briefing or instant_push",
            )

        return self
