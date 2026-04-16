from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Coroutine, cast

from pydantic import ValidationError

from app.agents import (
    run_chart_agent,
    run_editor_agent,
    run_flow_agent,
    run_news_agent,
    run_risk_agent,
)
from app.config import BrainSettings, get_settings
from app.contracts.input import CandidateEventRequest
from app.contracts.output import (
    AgentVote,
    BrokerDeeplinkHint,
    EvaluateSignalSuccessResponse,
    EvidenceRef,
    SignalCard,
    SignalDecision,
)
from app.gate.service import GateService
from app.policies.tone import (
    TonePolicyViolation,
    ensure_allowed_text,
    ensure_allowed_texts,
)
from app.prompts.registry import get_prompt_spec
from app.runtime.parallel import ParallelAgentSpec, run_bounded_parallel
from app.scoring.confidence import score_agent_votes

_SPECIALIST_AGENT_NAMES = ("news", "chart", "flow", "risk")
_MINIMUM_SPECIALIST_SUCCESSES = 3


@dataclass
class AnalysisFailedError(RuntimeError):
    failed_agents: list[str]
    message: str

    def __str__(self) -> str:
        return self.message


class EvaluateSignalService:
    def __init__(self, settings: BrainSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._gate_service = GateService(settings=self._settings)

    async def evaluate(
        self,
        candidate_event: CandidateEventRequest,
    ) -> EvaluateSignalSuccessResponse:
        gate_score = _read_gate_score(candidate_event)
        gate_result = self._gate_service.evaluate(score=gate_score)

        if gate_result.decision == SignalDecision.REJECT:
            return EvaluateSignalSuccessResponse(
                decision=gate_result.decision,
                gate=gate_result.gate,
                signal_card=None,
            )

        parallel_result = await run_bounded_parallel(
            self._build_specialist_specs(candidate_event),
            concurrency_limit=self._settings.specialist_concurrency_limit,
            minimum_successes_required=_MINIMUM_SPECIALIST_SUCCESSES,
        )

        if not _minimum_coverage_met(parallel_result.successes):
            raise AnalysisFailedError(
                failed_agents=parallel_result.failed_agents,
                message="minimum specialist coverage not met",
            )

        specialist_findings = _build_specialist_findings(parallel_result.successes)
        try:
            editor_output = await run_editor_agent(
                candidate_event,
                specialist_findings=specialist_findings,
                settings=self._settings,
            )
            signal_card = _build_signal_card(
                candidate_event=candidate_event,
                decision=gate_result.decision,
                specialist_successes=parallel_result.successes,
                editor_output=editor_output,
            )
        except (TonePolicyViolation, ValidationError, ValueError) as exc:
            raise AnalysisFailedError(
                failed_agents=[*parallel_result.failed_agents, "editor"],
                message="editor output failed validation",
            ) from exc

        return EvaluateSignalSuccessResponse(
            decision=gate_result.decision,
            gate=gate_result.gate,
            signal_card=signal_card,
        )

    def _build_specialist_specs(
        self,
        candidate_event: CandidateEventRequest,
    ) -> list[ParallelAgentSpec]:
        return [
            ParallelAgentSpec(
                agent_name="news",
                run=_build_news_runner(candidate_event, self._settings),
                timeout_ms=get_prompt_spec("news", settings=self._settings).timeout_ms,
            ),
            ParallelAgentSpec(
                agent_name="chart",
                run=_build_chart_runner(candidate_event, self._settings),
                timeout_ms=get_prompt_spec("chart", settings=self._settings).timeout_ms,
            ),
            ParallelAgentSpec(
                agent_name="flow",
                run=_build_flow_runner(candidate_event, self._settings),
                timeout_ms=get_prompt_spec("flow", settings=self._settings).timeout_ms,
            ),
            ParallelAgentSpec(
                agent_name="risk",
                run=_build_risk_runner(candidate_event, self._settings),
                timeout_ms=get_prompt_spec("risk", settings=self._settings).timeout_ms,
            ),
        ]


def _read_gate_score(candidate_event: CandidateEventRequest) -> float:
    return float(candidate_event.metadata.gate_score)


def _minimum_coverage_met(successes: dict[str, object]) -> bool:
    successful_agents = set(successes)
    return (
        len(successful_agents) >= _MINIMUM_SPECIALIST_SUCCESSES
        and "risk" in successful_agents
        and bool(successful_agents & {"news", "chart", "flow"})
    )


def _build_news_runner(
    candidate_event: CandidateEventRequest,
    settings: BrainSettings,
) -> Callable[[], Coroutine[Any, Any, object]]:
    async def run() -> object:
        return await run_news_agent(candidate_event, settings=settings)

    return run


def _build_chart_runner(
    candidate_event: CandidateEventRequest,
    settings: BrainSettings,
) -> Callable[[], Coroutine[Any, Any, object]]:
    async def run() -> object:
        return await run_chart_agent(candidate_event, settings=settings)

    return run


def _build_flow_runner(
    candidate_event: CandidateEventRequest,
    settings: BrainSettings,
) -> Callable[[], Coroutine[Any, Any, object]]:
    async def run() -> object:
        return await run_flow_agent(candidate_event, settings=settings)

    return run


def _build_risk_runner(
    candidate_event: CandidateEventRequest,
    settings: BrainSettings,
) -> Callable[[], Coroutine[Any, Any, object]]:
    async def run() -> object:
        return await run_risk_agent(candidate_event, settings=settings)

    return run


def _build_specialist_findings(
    specialist_successes: dict[str, object],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for agent_name in _SPECIALIST_AGENT_NAMES:
        result = specialist_successes.get(agent_name)
        if not isinstance(result, dict):
            continue
        findings.append(
            {
                "agent": agent_name,
                "summary": result["summary"],
                "stance": result["stance"],
                "confidence": result["confidence"],
            },
        )
    return findings


def _build_signal_card(
    *,
    candidate_event: CandidateEventRequest,
    decision: SignalDecision,
    specialist_successes: dict[str, object],
    editor_output: dict[str, object],
) -> SignalCard:
    agent_votes = _build_agent_votes(specialist_successes)
    reasons_raw = cast(list[object], editor_output["reasons"])
    risks_raw = cast(list[object], editor_output["risks"])
    title = ensure_allowed_text(str(editor_output["title"]))
    summary = ensure_allowed_text(str(editor_output["summary"]))
    reasons = ensure_allowed_texts([str(reason) for reason in reasons_raw])
    risks = ensure_allowed_texts([str(risk) for risk in risks_raw])
    watch_action = ensure_allowed_text(str(editor_output["watch_action"]))

    return SignalCard(
        id=_signal_card_id(candidate_event.candidate_id),
        title=title,
        asset=candidate_event.asset,
        signal_strength=_signal_strength(decision),
        summary=summary,
        reasons=reasons,
        risks=risks,
        watch_action=watch_action,
        broker_deeplink_hint=BrokerDeeplinkHint(
            broker="toss_securities",
            symbol=candidate_event.asset.symbol,
        ),
        agent_votes=agent_votes,
        confidence=score_agent_votes(agent_votes),
        evidence_refs=_build_evidence_refs(candidate_event),
    )


def _build_agent_votes(specialist_successes: dict[str, object]) -> list[AgentVote]:
    votes: list[AgentVote] = []
    for agent_name in _SPECIALIST_AGENT_NAMES:
        result = specialist_successes.get(agent_name)
        if not isinstance(result, dict):
            continue
        votes.append(
            AgentVote(
                agent=agent_name,
                stance=result["stance"],
                confidence=result["confidence"],
            ),
        )
    return votes


def _build_evidence_refs(candidate_event: CandidateEventRequest) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    event_ref = candidate_event.metadata.event_ref
    if event_ref:
        refs.append(EvidenceRef(type="market_event", ref=event_ref))

    for item in candidate_event.news_items:
        news_id = item.get("id")
        if isinstance(news_id, str) and news_id:
            refs.append(EvidenceRef(type="news", ref=news_id))

    return refs


def _signal_card_id(candidate_id: str) -> str:
    if candidate_id.startswith("cand_"):
        return candidate_id.replace("cand_", "sig_", 1)
    return f"sig_{candidate_id}"


def _signal_strength(decision: SignalDecision) -> str:
    if decision == SignalDecision.INSTANT_PUSH:
        return "strong"
    return "watch"
