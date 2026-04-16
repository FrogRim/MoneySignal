from __future__ import annotations

from collections import Counter

from app.contracts.output import AgentStance, AgentVote

_DOMINANT_STANCE_BONUS_SCALE = 0.055
_POSITIVE_SIGNAL_BONUS_SCALE = 0.07
_MAX_CONFIDENCE_SCORE = 0.96


def score_agent_votes(agent_votes: list[AgentVote]) -> float:
    if not agent_votes:
        raise ValueError("at least one agent vote is required")

    average_confidence = sum(vote.confidence for vote in agent_votes) / len(agent_votes)
    stance_counts = Counter(vote.stance for vote in agent_votes)
    dominant_ratio = max(stance_counts.values()) / len(agent_votes)
    positive_ratio = sum(
        1 for vote in agent_votes if vote.stance == AgentStance.POSITIVE
    ) / len(agent_votes)
    score = average_confidence + (
        dominant_ratio * _DOMINANT_STANCE_BONUS_SCALE
    ) + (positive_ratio * _POSITIVE_SIGNAL_BONUS_SCALE)
    return round(min(score, _MAX_CONFIDENCE_SCORE), 2)
