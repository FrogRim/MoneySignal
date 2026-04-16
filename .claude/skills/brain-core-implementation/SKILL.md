---
name: brain-core-implementation
description: MoneySignal Agent Brain의 foundation 구현 스킬. `services/brain` 초기화, ADR/defaults, `app/config.py`, FastAPI health, input/output contracts, gate, confidence, tone policy 작업이면 반드시 사용한다. Phase 0-3 작업 전용이다.
---

# Brain Core Implementation

## 목적
MoneySignal Agent Brain의 기초 계층을 작고 검증 가능한 단위로 구현한다. 이 스킬은 spec에 잠긴 foundation을 먼저 만들고, 이후 runtime/API 단계가 흔들리지 않게 contract와 deterministic rule을 고정하는 데 목적이 있다.

## 언제 활성화할까
다음 작업이면 이 스킬을 사용한다.
- `services/brain/` 최초 bootstrap
- `ADR-001-v1-defaults.md` 작성/수정
- `app/config.py` 설정 추가
- `contracts/input.py`, `contracts/output.py` 구현
- `gate/service.py`, `scoring/confidence.py`, `policies/tone.py` 구현
- health / contract / unit test 추가

다음 작업에는 이 스킬이 아니다.
- prompt registry, templates, runtime fan-out
- error contracts / HTTP handlers / API wiring
- golden fixtures 전용 QA

## 작업 순서
1. spec, plan, task breakdown을 먼저 읽고 현재 slice가 어느 Task인지 고정한다.
2. config/ADR → bootstrap → contracts → deterministic core 순서를 지킨다.
3. threshold, timeout, concurrency 같은 정책값은 `app/config.py`로 올린다.
4. 구현과 테스트를 같은 slice에서 끝낸다. 테스트 없이 다음 파일로 넘어가지 않는다.
5. handoff 전에 `_workspace/brain/01_core_status.md`를 갱신한다.

## 구현 원칙
- `contracts/`를 public source of truth로 유지한다.
- reject/briefing/instant_push 계약을 ad hoc dict로 흩뜨리지 않는다.
- live provider, network dependency, fake external integration을 추가하지 않는다.
- direct buy/sell wording을 허용하지 않는다.
- spec에 없는 필드/추상화/헬퍼를 과하게 만들지 않는다.

## 기본 검증 명령
작업 범위에 맞는 최소 검증부터 실행한다.

```bash
uv run pytest tests/integration/test_health.py -q
uv run pytest tests/contracts/test_input_contract.py tests/contracts/test_output_contract.py -q
uv run pytest tests/unit/test_gate_service.py tests/unit/test_confidence.py tests/unit/test_tone_policy.py -q
uv run mypy app
uv run ruff check .
```

## handoff 형식
`_workspace/brain/01_core_status.md`에 아래를 남긴다.
- 이번 slice에서 바뀐 파일
- 남은 TODO
- runtime/API가 의존하는 contract 또는 config key
- QA가 먼저 봐야 하는 경계면
- 실행한 검증 명령과 결과

## 완료 기준
- foundation 관련 테스트가 통과한다.
- threshold가 코드에 하드코딩되지 않는다.
- reject/null semantics와 approved card required fields가 contract에 반영된다.
- 다음 단계 담당자가 status 파일만 읽어도 이어서 작업할 수 있다.
