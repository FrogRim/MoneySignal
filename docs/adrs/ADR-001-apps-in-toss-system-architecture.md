# ADR-001: MoneySignal 제품 구조를 Brain + Pipeline + Toss Miniapp으로 분리한다

- Status: Accepted
- Date: 2026-04-19
- Deciders: MoneySignal launch planning slice
- Related spec: `docs/superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- Related doc: `docs/product/apps-in-toss-mvp.md`

## Context

현재 저장소에서 가장 완성도가 높은 영역은 `services/brain`입니다. 이 서비스는 후보 이벤트를 평가해 `reject`, `briefing`, `instant_push`를 반환하는 **Agent Brain** 역할을 잘 수행하고 있습니다. 하지만 앱인토스 검수와 출시를 목표로 하면, Brain만으로는 제품이 완성되지 않습니다.

빠진 영역은 크게 두 가지입니다.

1. 후보 이벤트를 생성하고 Brain을 호출한 뒤 제품이 읽을 수 있는 read model을 만드는 **Data Pipeline**
2. Apps in Toss WebView 안에서 목록/상세/도움말을 보여주는 **Toss Miniapp**

앱인토스 검수는 단순히 API가 존재하는지보다, 제품 surface가 Toss 제약 안에서 자연스럽고 안전하게 동작하는지를 봅니다. 따라서 Brain을 그대로 제품 API로 확장하는 것보다, 역할을 분리해 제품 표면을 별도 계층으로 두는 편이 더 안전합니다.

## Decision

MoneySignal v1 제품 구조를 아래 세 계층으로 분리합니다.

### 1. Brain은 평가 엔진으로 유지한다
- 위치: `services/brain`
- 책임: 후보 이벤트를 평가해 공개 contract에 맞는 결과를 반환
- 비책임: miniapp 전용 feed/detail API, UI 상태 조합, 제품용 read model 관리

### 2. Pipeline은 제품용 read surface를 소유한다
- 위치: `services/pipeline`
- 책임:
  - 후보 이벤트 생성/정규화
  - Brain evaluate 호출
  - 결과 저장 또는 replay 가능한 read model 구성
  - miniapp이 읽을 feed/detail API 제공

### 3. Toss Miniapp은 Apps in Toss surface를 소유한다
- 위치: `apps/toss-miniapp`
- 책임:
  - WebView-first UI
  - 목록/상세/도움말/에러/빈 상태 렌더링
  - Toss 제약을 반영한 네비게이션/카피/디자인

## Alternatives considered

### A. Miniapp이 Brain evaluate endpoint를 직접 호출한다
- 장점: 초기 연결이 단순해 보인다.
- 단점: Brain contract가 제품용 read API 요구에 끌려가고, Toss 세션/캐시/목록/상세 surface를 Brain이 떠안게 된다.
- 기각 이유: Brain의 역할이 evaluator에서 product API로 비대해진다.

### B. Brain 안에 feed/detail read API까지 같이 넣는다
- 장점: 서비스 수를 줄일 수 있다.
- 단점: 후보 이벤트 생성, read model, UI 요구사항이 Brain과 섞이면서 경계가 흐려진다.
- 기각 이유: 기존 Brain의 contract-first 구조와 책임 분리가 무너진다.

### C. 처음부터 대규모 분산 구조(큐/여러 워커/복수 저장소)로 간다
- 장점: 장기 확장성은 좋아 보인다.
- 단점: v1 검수 통과 전 단계에서 구현량과 운영 복잡도가 과도하게 커진다.
- 기각 이유: 지금 목표는 확장성 극대화가 아니라 검수 가능하고 출시 가능한 제품 완성이다.

## Consequences

### Positive
- Brain의 현재 hardening, contract, 테스트 자산을 그대로 재사용할 수 있다.
- Pipeline이 제품 친화적 read surface를 만들 수 있다.
- Miniapp은 Toss 제약에 집중한 UX 계층으로 설계할 수 있다.
- 검수/운영 문서를 계층별로 정리하기 쉬워진다.

### Trade-offs
- 서비스와 문서 수가 늘어난다.
- Pipeline이라는 중간 계층을 새로 구현해야 한다.
- 처음부터 end-to-end 검증 동선을 설계하지 않으면 계층 간 drift가 생길 수 있다.

## Consequences for implementation

- Brain 공개 contract 변경은 최소화한다.
- Pipeline은 Brain의 `CandidateEventRequest` / `EvaluateSignalSuccessResponse`를 기준으로 구현한다.
- Miniapp은 Brain raw endpoint가 아니라 Pipeline read API를 읽는다.
- 루트 README, 제품 문서, runbook은 Brain-only 설명에서 A/B/C 전체 구조 설명으로 확장한다.
