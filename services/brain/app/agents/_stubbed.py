from __future__ import annotations

from app.config import BrainSettings
from app.contracts.input import CandidateEventRequest
from app.prompts.builders import build_prompt


async def execute_stubbed_agent(
    agent_name: str,
    candidate_event: CandidateEventRequest,
    *,
    specialist_findings: list[dict[str, object]] | None = None,
    settings: BrainSettings | None = None,
) -> dict[str, object]:
    built_prompt = build_prompt(
        agent_name,
        candidate_event,
        specialist_findings=specialist_findings,
        settings=settings,
    )
    payload = _load_stub_agent_output(candidate_event, agent_name)
    validated = built_prompt.spec.response_model.model_validate(payload)
    return validated.model_dump(mode="python")


def _load_stub_agent_output(
    candidate_event: CandidateEventRequest,
    agent_name: str,
) -> dict[str, object]:
    payload = candidate_event.metadata.stub_agent_outputs.get(agent_name)
    if payload is None:
        raise ValueError(f"missing stub output for {agent_name}")

    return payload
