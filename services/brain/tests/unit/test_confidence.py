from __future__ import annotations

import pytest

from app.contracts.output import AgentStance, AgentVote
from app.scoring.confidence import score_agent_votes


def build_spec_fixture_votes() -> list[AgentVote]:
    return [
        AgentVote(agent="chart", stance="positive", confidence=0.78),
        AgentVote(agent="news", stance="positive", confidence=0.81),
        AgentVote(agent="flow", stance="neutral", confidence=0.55),
        AgentVote(agent="risk", stance="cautious", confidence=0.64),
    ]


def test_score_agent_votes_returns_deterministic_score_for_spec_fixture() -> None:
    result = score_agent_votes(build_spec_fixture_votes())

    assert result == 0.76


def test_score_agent_votes_returns_higher_score_for_unanimous_positive_votes() -> None:
    result = score_agent_votes(
        [
            AgentVote(agent="chart", stance="positive", confidence=0.90),
            AgentVote(agent="news", stance="positive", confidence=0.95),
        ],
    )

    assert result == 0.96


def test_score_agent_votes_rejects_empty_vote_list() -> None:
    with pytest.raises(ValueError, match="at least one agent vote"):
        score_agent_votes([])


def test_score_agent_votes_returns_lower_score_when_votes_disagree() -> None:
    unanimous_positive = score_agent_votes(
        [
            AgentVote(
                agent="chart",
                stance=AgentStance.POSITIVE,
                confidence=0.80,
            ),
            AgentVote(
                agent="news",
                stance=AgentStance.POSITIVE,
                confidence=0.80,
            ),
        ],
    )
    mixed_votes = score_agent_votes(
        [
            AgentVote(
                agent="chart",
                stance=AgentStance.POSITIVE,
                confidence=0.80,
            ),
            AgentVote(
                agent="news",
                stance=AgentStance.NEUTRAL,
                confidence=0.80,
            ),
        ],
    )

    assert mixed_votes < unanimous_positive
