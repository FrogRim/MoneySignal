from __future__ import annotations

from app.agents._stubbed import execute_stubbed_agent
from app.config import BrainSettings
from app.contracts.input import CandidateEventRequest


async def run_flow_agent(
    candidate_event: CandidateEventRequest,
    *,
    settings: BrainSettings | None = None,
) -> dict[str, object]:
    return await execute_stubbed_agent(
        "flow",
        candidate_event,
        settings=settings,
    )
