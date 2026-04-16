---
name: brain-incremental-qa
description: MoneySignal Agent Brain의 단계별 QA 스킬. 구현 phase가 하나라도 끝났거나 완료 보고 전이라면 반드시 사용한다. contracts ↔ runtime ↔ handlers ↔ API response 경계면을 교차 검증하고, parallel/error/golden regressions를 잡는다.
---

# Brain Incremental QA

## 목적
MoneySignal Agent Brain을 마지막에 한 번만 보는 대신, phase마다 경계면 불일치를 조기에 잡는다. 이 스킬의 핵심은 존재 확인이 아니라 producer/consumer 교차 검증이다.

## 언제 활성화할까
다음 상황이면 이 스킬을 사용한다.
- foundation slice가 끝났을 때
- runtime/orchestrator slice가 끝났을 때
- API/error surface가 끝났을 때
- golden fixtures나 sample runner를 추가했을 때
- 사용자에게 "완료"라고 보고하기 직전

## 검증 원칙
1. producer와 consumer를 함께 읽는다.
2. 테스트가 없으면 PASS라고 말하지 않는다.
3. high-confidence issue만 보고한다.
4. FAIL / PASS / UNVERIFIED를 분리한다.
5. failing test를 삭제해서 green으로 만들지 않는다.

## 교차 검증 축
- `contracts/input.py` ↔ API request validation / orchestrator input
- `contracts/output.py` ↔ orchestrator assembly / API success response
- `contracts/errors.py` ↔ handlers / API error response
- `runtime/parallel.py` ↔ orchestrator failure propagation
- prompt registry usage ↔ agent implementation
- golden fixtures ↔ tone/risk/direct-trading wording rules

## 기본 검증 명령
필요한 범위만 골라 실행한다.

```bash
uv run pytest tests/contracts -q
uv run pytest tests/unit -q
uv run pytest tests/integration/test_parallel_agents.py -q
uv run pytest tests/integration/test_evaluate_signal_orchestrator.py -q
uv run pytest tests/integration/test_error_paths.py -q
uv run pytest tests/integration/test_signals_api.py -q
uv run pytest tests/integration/golden/test_signal_cards.py -q
uv run mypy app
uv run ruff check .
```

## 리포트 형식
phase별 리포트 파일에 아래를 남긴다.
- PASS
- FAIL
- UNVERIFIED
- 수정 요청: producer 파일, consumer 파일, 재현 근거, 추천 수정 방향

권장 경로:
- `_workspace/brain/qa_phase_01.md`
- `_workspace/brain/qa_phase_02.md`
- `_workspace/brain/qa_phase_03.md`
- `_workspace/brain/qa_final.md`

## 완료 기준
- major 경계면 mismatch가 없다.
- reject/null 규칙, error taxonomy, failed_agents propagation이 검증된다.
- parallel runtime이 실제로 병렬임이 timing evidence로 확인된다.
- golden checks가 direct-trading wording과 missing risk regression을 잡는다.
