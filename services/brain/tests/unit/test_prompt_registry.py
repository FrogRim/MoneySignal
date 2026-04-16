from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import BrainSettings
from app.prompts.registry import (
    EditorPromptResponse,
    SpecialistPromptResponse,
    get_prompt_registry,
    get_prompt_spec,
)


def test_get_prompt_registry_defines_expected_agent_specs() -> None:
    registry = get_prompt_registry(settings=BrainSettings())

    assert set(registry) == {"news", "chart", "flow", "risk", "editor"}
    assert registry["news"].template_version == "v1"
    assert registry["news"].response_model is SpecialistPromptResponse
    assert registry["editor"].response_model is EditorPromptResponse
    assert registry["news"].model_key == "stub-specialist-v1"
    assert registry["editor"].model_key == "stub-editor-v1"
    assert registry["news"].timeout_ms == 3000
    assert registry["editor"].timeout_ms == 3000
    assert registry["news"].max_context_items == 5
    assert registry["editor"].max_context_items == 6


def test_get_prompt_spec_resolves_template_files_with_required_sections() -> None:
    for agent_name in ["news", "chart", "flow", "risk", "editor"]:
        spec = get_prompt_spec(agent_name, settings=BrainSettings())
        template = spec.load_template()

        assert spec.template_path.exists()
        assert "# Role" in template
        assert "# Candidate Event" in template
        assert "# Output Contract" in template
        assert "{candidate_id}" in template
        assert "{asset_name}" in template


def test_editor_template_keeps_specialist_findings_placeholder() -> None:
    spec = get_prompt_spec("editor", settings=BrainSettings())

    assert "{specialist_findings_json}" in spec.load_template()


def test_editor_prompt_response_requires_reasons_and_risks() -> None:
    with pytest.raises(ValidationError):
        EditorPromptResponse.model_validate(
            {
                "title": "삼성전자에 강한 관심 신호가 포착됐어요",
                "summary": "거래량과 뉴스 흐름이 함께 개선됐습니다.",
                "watch_action": "장 마감 전 수급이 유지되는지 확인해보세요.",
            },
        )


def test_editor_template_mentions_reasons_and_risks() -> None:
    spec = get_prompt_spec("editor", settings=BrainSettings())
    template = spec.load_template()

    assert "reasons" in template
    assert "risks" in template


def test_editor_prompt_response_rejects_blank_reason_or_risk_items() -> None:
    with pytest.raises(ValidationError):
        EditorPromptResponse.model_validate(
            {
                "title": "삼성전자에 강한 관심 신호가 포착됐어요",
                "summary": "거래량과 뉴스 흐름이 함께 개선됐습니다.",
                "reasons": ["", "정상 이유"],
                "risks": ["정상 리스크"],
                "watch_action": "장 마감 전 수급이 유지되는지 확인해보세요.",
            },
        )

    with pytest.raises(ValidationError):
        EditorPromptResponse.model_validate(
            {
                "title": "삼성전자에 강한 관심 신호가 포착됐어요",
                "summary": "거래량과 뉴스 흐름이 함께 개선됐습니다.",
                "reasons": ["정상 이유", "두 번째 이유"],
                "risks": [""],
                "watch_action": "장 마감 전 수급이 유지되는지 확인해보세요.",
            },
        )
