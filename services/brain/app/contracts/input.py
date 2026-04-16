from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonEmptyText = Annotated[str, Field(min_length=1)]


class AssetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    market: str = Field(min_length=1)


class CandidateEventMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_score: float
    event_ref: NonEmptyText | None = None
    stub_agent_outputs: dict[str, dict[str, object]]


class CandidateEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    asset: AssetInput
    trigger_type: str = Field(min_length=1)
    event_ts: datetime
    market_snapshot: dict[str, object]
    news_items: list[dict[str, object]]
    flow_snapshot: dict[str, object]
    theme_context: list[object]
    metadata: CandidateEventMetadata
