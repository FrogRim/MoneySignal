---
name: brain-prompt-runtime
description: MoneySignal Agent Brain의 prompt/runtime 구현 스킬. `app/prompts/*`, templates, bounded async parallel runtime, specialist agents, editor agent, orchestrator, minimum coverage, `test_parallel_agents.py` 작업이면 반드시 사용한다. Phase 4 전용이다.
---

# Brain Prompt Runtime

## 목적
Prompt registry와 bounded async runtime을 중심으로 MoneySignal Agent Brain의 multi-agent 실행층을 구현한다. 이 스킬은 inline prompt와 sequential fan-out 같은 품질 저하 패턴을 막고, registry/parallel/orchestrator를 테스트로 증명하는 데 목적이 있다.

## 언제 활성화할까
다음 작업이면 이 스킬을 사용한다.
- `app/prompts/registry.py`, `builders.py` 구현
- `app/prompts/templates/*.md` 작성/수정
- `app/runtime/parallel.py` 구현
- specialist/editor agent 구현
- `app/orchestrators/evaluate_signal.py` 구현
- `tests/integration/test_parallel_agents.py`
- `tests/integration/test_evaluate_signal_orchestrator.py`

다음 작업에는 이 스킬이 아니다.
- foundation/bootstrap/contracts 자체 정의
- HTTP handler / API route / error envelope wiring
- 최종 golden QA만 수행하는 작업

## 작업 순서
1. `_workspace/brain/01_core_status.md`와 contracts/gate/scoring/tone을 먼저 읽는다.
2. prompt registry와 templates를 먼저 잠근다.
3. builders를 추가해 candidate event -> prompt context 흐름을 만든다.
4. bounded parallel runtime을 구현하고 timeout/failure surface를 먼저 테스트한다.
5. specialist/editor agents를 fixture-backed 방식으로 연결한다.
6. orchestrator에서 gate-pass -> specialists -> minimum coverage -> editor -> final card 조립 순서를 구현한다.
7. handoff 전에 `_workspace/brain/02_runtime_status.md`를 갱신한다.

## 구현 원칙
- agent 클래스 안에 ad hoc prompt string을 만들지 않는다.
- registry가 `agent_name`, `template_version`, `response_model`, `model_key`, `timeout_ms`, `max_context_items`를 보유하는 단일 진실원이 되게 한다.
- timeout/validation/coverage failure를 soft success로 넘기지 않는다.
- v1은 deterministic fixture/stub 기반으로 유지한다.
- editor는 specialist collection이 성공한 뒤에만 실행한다.

## 기본 검증 명령
```bash
uv run pytest tests/unit/test_prompt_registry.py tests/unit/test_prompt_builders.py -q
uv run pytest tests/integration/test_parallel_agents.py -q
uv run pytest tests/integration/test_evaluate_signal_orchestrator.py -q
uv run mypy app
uv run ruff check .
```

## handoff 형식
`_workspace/brain/02_runtime_status.md`에 아래를 남긴다.
- registry/template coverage 현황
- timeout / concurrency / minimum coverage 가정
- orchestrator가 조립하는 success shape
- failed_agents가 채워지는 경로
- QA가 확인할 producer/consumer 경계면
- 실행한 검증 명령과 결과

## 완료 기준
- 모든 prompt가 registry를 통해 해석된다.
- specialist fan-out이 bounded parallelism으로 동작한다.
- minimum coverage 실패 시 fake card가 아니라 failure surface가 남는다.
- integration test가 parallelism과 disagreement visibility를 증명한다.
