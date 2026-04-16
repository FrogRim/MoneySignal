from __future__ import annotations

from app.agents._stubbed import execute_stubbed_agent
from app.config import BrainSettings
from app.contracts.input import CandidateEventRequest


async def run_editor_agent(
    candidate_event: CandidateEventRequest,
    *,
    specialist_findings: list[dict[str, object]],
    settings: BrainSettings | None = None,
) -> dict[str, object]:
    return await execute_stubbed_agent(
        "editor",
        candidate_event,
        specialist_findings=specialist_findings,
        settings=settings,
    )
