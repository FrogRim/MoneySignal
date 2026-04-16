---
name: brain-api-error-surface
description: MoneySignal Agent Brain의 API/error surface 구현 스킬. `contracts/errors.py`, `errors/codes.py`, `errors/handlers.py`, `api/v1/signals.py`, `POST /v1/signals/evaluate`, success/error envelope wiring 작업이면 반드시 사용한다. Phase 5 전용이다.
---

# Brain API Error Surface

## 목적
MoneySignal Agent Brain의 public HTTP surface를 spec대로 고정한다. 이 스킬은 reject success와 runtime failure를 분리하고, structured error envelope가 fake market result로 오염되지 않게 만드는 데 목적이 있다.

## 언제 활성화할까
다음 작업이면 이 스킬을 사용한다.
- `contracts/errors.py` 구현
- error taxonomy / handler mapping 구현
- `POST /v1/signals/evaluate` route 구현
- `app/main.py` router + handler 등록
- `tests/integration/test_error_paths.py`
- `tests/integration/test_signals_api.py`

다음 작업에는 이 스킬이 아니다.
- contracts/gate/tone 같은 deterministic core 정의
- prompt registry/runtime/orchestrator 자체 구현
- final golden QA only

## 작업 순서
1. `_workspace/brain/01_core_status.md`, `_workspace/brain/02_runtime_status.md`를 먼저 읽는다.
2. error contract와 domain error code를 먼저 잠근다.
3. handler에서 HTTP status / payload mapping을 구현한다.
4. route는 thin하게 연결한다.
5. reject는 success envelope + `signal_card: null`, runtime failure는 error envelope 규칙을 테스트로 잠근다.
6. handoff 전에 `_workspace/brain/03_api_status.md`를 갱신한다.

## 구현 원칙
- success envelope와 error envelope를 섞지 않는다.
- invalid request는 validation boundary에서 끝낸다.
- runtime failure를 reject처럼 포장하지 않는다.
- `failed_agents`, `retryable`, `trace_id` shape를 일관되게 유지한다.
- orchestration 로직을 API handler로 끌어올리지 않는다.

## 기본 검증 명령
```bash
uv run pytest tests/integration/test_error_paths.py -q
uv run pytest tests/integration/test_signals_api.py -q
uv run pytest tests/contracts -q
uv run mypy app
uv run ruff check .
```

## handoff 형식
`_workspace/brain/03_api_status.md`에 아래를 남긴다.
- route wiring 요약
- status code ↔ error code 매핑 표
- reject/briefing/instant_push 검증 결과
- major error class 검증 결과
- README/sample runner에 반영할 API notes
- 실행한 검증 명령과 결과

## 완료 기준
- valid request는 success envelope를 돌려준다.
- reject일 때만 `signal_card`가 null이다.
- invalid_request / upstream_timeout / upstream_unavailable / analysis_failed / internal_error가 구조화된 error envelope로 반환된다.
- error-path tests가 runtime failure와 validation failure를 구분해 증명한다.
