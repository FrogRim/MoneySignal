---
name: moneysignal-agent-brain-orchestrator
description: MoneySignal Agent Brain 구현 전체를 조율하는 오케스트레이터. `services/brain`을 처음 만들거나, 여러 phase를 병렬/순차로 나눠 구현하거나, custom agents를 사용해 end-to-end로 진행할 때 반드시 사용한다. brain-core-engineer, brain-runtime-engineer, brain-api-engineer, brain-qa-inspector를 의존 순서대로 호출한다.
---

# MoneySignal Agent Brain Orchestrator

MoneySignal Agent Brain 구현을 위한 상위 조율 스킬이다.

## 실행 모드: 서브 에이전트

현재 런타임에서는 `Agent` 도구로 custom agent들을 단계적으로 호출하는 방식이 가장 직접적이다. 논리 구조는 팀 기반 분업이지만, 실제 실행은 **staged pipeline + fan-out/fan-in sub-agents**로 수행한다.

## 에이전트 구성

| 에이전트 | 역할 | 권장 스킬 | 주 산출물 |
|---------|------|----------|-----------|
| `brain-core-engineer` | Phase 0-3 foundation | `brain-core-implementation` | `_workspace/brain/01_core_status.md` |
| `brain-runtime-engineer` | Phase 4 prompt/runtime/orchestrator | `brain-prompt-runtime` | `_workspace/brain/02_runtime_status.md` |
| `brain-api-engineer` | Phase 5 error/API surface | `brain-api-error-surface` | `_workspace/brain/03_api_status.md` |
| `brain-qa-inspector` | phase별/final QA | `brain-incremental-qa` | `_workspace/brain/qa_*.md` |

## 워크플로우

### Phase 1: 준비
1. spec, plan, task breakdown을 읽는다.
2. 현재 목표 task 범위를 정한다.
3. 필요하면 `_workspace/brain/` 상태 파일 경로를 준비한다.
4. shared task list를 최신 상태로 맞춘다.

### Phase 2: foundation 구현
1. `Agent` 도구로 `brain-core-engineer`를 `model: "opus"`로 호출한다.
2. prompt에는 다음을 반드시 포함한다.
   - 현재 구현할 task 번호
   - 읽어야 할 spec/plan/task breakdown 경로
   - 수정 가능한 파일 목록
   - 실행해야 할 최소 검증 명령
3. foundation 작업이 끝나면 `_workspace/brain/01_core_status.md`를 읽어 결과를 확인한다.
4. 곧바로 `brain-qa-inspector`를 호출해 foundation QA를 수행한다.

### Phase 3: prompt/runtime 구현
1. `brain-runtime-engineer`를 `model: "opus"`로 호출한다.
2. 입력으로 `_workspace/brain/01_core_status.md`와 관련 contract/gate 파일을 함께 준다.
3. runtime 구현 후 `_workspace/brain/02_runtime_status.md`를 읽는다.
4. `brain-qa-inspector`로 runtime/orchestrator QA를 수행한다.

### Phase 4: API/error surface 구현
1. `brain-api-engineer`를 `model: "opus"`로 호출한다.
2. 입력으로 `_workspace/brain/01_core_status.md`, `_workspace/brain/02_runtime_status.md`를 함께 준다.
3. API 구현 후 `_workspace/brain/03_api_status.md`를 읽는다.
4. `brain-qa-inspector`로 API/error-path QA를 수행한다.

### Phase 5: 품질 안정화
1. golden fixtures/tests는 `brain-qa-inspector`가 우선 작성/검증한다.
2. sample runner / README / final doc polish는 현재 열린 변경 범위를 가장 많이 가진 구현 담당자에게 맡긴다. 보통 foundation 또는 API 담당자가 적합하다.
3. 마지막으로 `brain-qa-inspector`가 final QA를 수행한다.

## Agent 호출 규칙
- 모든 custom agent 호출에 `model: "opus"`를 명시한다.
- 독립 작업만 병렬 호출한다. 예: foundation 완료 후의 QA와 unrelated docs work 정도만 병렬화한다.
- runtime은 foundation handoff 전에는 시작하지 않는다.
- API는 runtime handoff 전에는 시작하지 않는다.
- QA는 각 phase 직후 바로 호출한다.

## 에러 핸들링
- sub-agent가 실패하면 같은 prompt를 그대로 반복하지 말고 실패 원인을 요약해 1회만 재시도한다.
- status 파일이 없으면 해당 phase 완료로 간주하지 않는다.
- QA가 boundary mismatch를 보고하면 producer/consumer 양쪽 파일을 다시 확인한 뒤 관련 구현 담당자를 재호출한다.
- tests/lint/typecheck 실패를 무시한 채 다음 phase로 넘기지 않는다.

## 테스트 시나리오

### 정상 흐름
1. foundation agent 실행
2. foundation QA 통과
3. runtime agent 실행
4. runtime QA 통과
5. API agent 실행
6. API QA 통과
7. final QA + docs/sample runner 정리
8. `uv run pytest -q`, `uv run ruff check .`, `uv run mypy app` 기준으로 마무리

### 에러 흐름
1. runtime QA가 contract mismatch 보고
2. producer/consumer 파일을 식별
3. `brain-runtime-engineer` 또는 `brain-core-engineer`를 재호출해 수정
4. 동일 범위 QA 재실행
5. PASS 전까지 다음 phase 진입 금지
