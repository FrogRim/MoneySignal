from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel

from app.config import BrainSettings
from app.contracts.input import CandidateEventRequest
from app.prompts.registry import PromptSpec, get_prompt_spec


@dataclass(frozen=True)
class BuiltPrompt:
    spec: PromptSpec
    prompt: str


def build_prompt(
    agent_name: str,
    candidate_event: CandidateEventRequest,
    specialist_findings: list[dict[str, object]] | None = None,
    settings: BrainSettings | None = None,
) -> BuiltPrompt:
    spec = get_prompt_spec(agent_name, settings=settings)
    template = spec.load_template()
    prompt = template.format(
        agent_name=spec.agent_name,
        candidate_id=candidate_event.candidate_id,
        asset_name=candidate_event.asset.name,
        asset_symbol=candidate_event.asset.symbol,
        asset_market=candidate_event.asset.market,
        trigger_type=candidate_event.trigger_type,
        event_ts=_serialize_datetime(candidate_event.event_ts),
        focus_text=_focus_text(agent_name),
        market_snapshot_json=_to_json(candidate_event.market_snapshot),
        news_items_json=_to_json(
            candidate_event.news_items[: spec.max_context_items],
        ),
        flow_snapshot_json=_to_json(candidate_event.flow_snapshot),
        theme_context_json=_to_json(
            candidate_event.theme_context[: spec.max_context_items],
        ),
        metadata_json=_to_json(candidate_event.metadata),
        specialist_findings_json=_to_json(
            (specialist_findings or [])[: spec.max_context_items],
        ),
    )
    return BuiltPrompt(spec=spec, prompt=prompt)


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def _to_json(value: object) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _focus_text(agent_name: str) -> str:
    focus_by_agent = {
        "news": "recent news flow and whether it changes the event meaning",
        "chart": "technical strength or weakness around price and volume",
        "flow": "investor flow and participation persistence",
        "risk": "downside scenarios and what could invalidate the setup",
        "editor": "synthesize specialist findings into beginner-friendly wording",
    }
    return focus_by_agent[agent_name]
