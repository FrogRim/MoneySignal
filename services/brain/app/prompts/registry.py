from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from app.config import BrainSettings, get_settings
from app.contracts.output import AgentStance

PromptResponseModel: TypeAlias = type[BaseModel]
NonEmptyText = Annotated[str, Field(min_length=1)]
_TEMPLATE_VERSION = "v1"
_SPECIALIST_MAX_CONTEXT_ITEMS = 5
_EDITOR_MAX_CONTEXT_ITEMS = 6


class SpecialistPromptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    stance: AgentStance
    confidence: float = Field(ge=0.0, le=1.0)


class EditorPromptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    reasons: list[NonEmptyText] = Field(min_length=2)
    risks: list[NonEmptyText] = Field(min_length=1)
    watch_action: str = Field(min_length=1)


@dataclass(frozen=True)
class PromptSpec:
    agent_name: str
    template_version: str
    response_model: PromptResponseModel
    model_key: str
    timeout_ms: int
    max_context_items: int
    template_path: Path

    def load_template(self) -> str:
        return self.template_path.read_text(encoding="utf-8")


def get_prompt_registry(
    settings: BrainSettings | None = None,
) -> dict[str, PromptSpec]:
    resolved_settings = settings or get_settings()
    templates_dir = Path(__file__).resolve().parent / "templates"

    registry = {
        "news": PromptSpec(
            agent_name="news",
            template_version=_TEMPLATE_VERSION,
            response_model=SpecialistPromptResponse,
            model_key=resolved_settings.specialist_model_key,
            timeout_ms=resolved_settings.per_agent_timeout_ms,
            max_context_items=_SPECIALIST_MAX_CONTEXT_ITEMS,
            template_path=templates_dir / "news.md",
        ),
        "chart": PromptSpec(
            agent_name="chart",
            template_version=_TEMPLATE_VERSION,
            response_model=SpecialistPromptResponse,
            model_key=resolved_settings.specialist_model_key,
            timeout_ms=resolved_settings.per_agent_timeout_ms,
            max_context_items=_SPECIALIST_MAX_CONTEXT_ITEMS,
            template_path=templates_dir / "chart.md",
        ),
        "flow": PromptSpec(
            agent_name="flow",
            template_version=_TEMPLATE_VERSION,
            response_model=SpecialistPromptResponse,
            model_key=resolved_settings.specialist_model_key,
            timeout_ms=resolved_settings.per_agent_timeout_ms,
            max_context_items=_SPECIALIST_MAX_CONTEXT_ITEMS,
            template_path=templates_dir / "flow.md",
        ),
        "risk": PromptSpec(
            agent_name="risk",
            template_version=_TEMPLATE_VERSION,
            response_model=SpecialistPromptResponse,
            model_key=resolved_settings.specialist_model_key,
            timeout_ms=resolved_settings.per_agent_timeout_ms,
            max_context_items=_SPECIALIST_MAX_CONTEXT_ITEMS,
            template_path=templates_dir / "risk.md",
        ),
        "editor": PromptSpec(
            agent_name="editor",
            template_version=_TEMPLATE_VERSION,
            response_model=EditorPromptResponse,
            model_key=resolved_settings.editor_model_key,
            timeout_ms=resolved_settings.per_agent_timeout_ms,
            max_context_items=_EDITOR_MAX_CONTEXT_ITEMS,
            template_path=templates_dir / "editor.md",
        ),
    }
    return registry


def get_prompt_spec(
    agent_name: str,
    settings: BrainSettings | None = None,
) -> PromptSpec:
    registry = get_prompt_registry(settings=settings)
    try:
        return registry[agent_name]
    except KeyError as exc:
        raise ValueError(f"unsupported prompt agent: {agent_name}") from exc
