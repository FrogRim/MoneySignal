# MoneySignal Apps in Toss MVP

## 목표

MoneySignal의 v1 목표는 **초보 투자자도 이해할 수 있는 투자 신호 경험**을 Apps in Toss 안에서 제공하는 것입니다. 핵심은 "거래를 강요하는 앱"이 아니라, **무슨 일이 있었고 왜 중요한지, 무엇을 다음에 보면 되는지**를 짧고 신뢰감 있게 보여주는 것입니다.

최종 제품 surface는 **Apps in Toss WebView miniapp**이고, 현재 저장소는 그 목표를 달성하기 위해 아래 세 축으로 나뉩니다.

- **A. Agent Brain** — 후보 이벤트를 평가해 `reject` / `briefing` / `instant_push`를 판단
- **B. Data Pipeline** — 후보 이벤트 생성, Brain 호출, 결과 저장, feed/detail read model 제공
- **C. Toss Miniapp** — Apps in Toss 안에서 목록/상세/도움말을 렌더링

## 현재 기준선

현재 기준으로 실제 구현이 많이 진행된 영역은 `services/brain`입니다.

- FastAPI 기반 evaluate API 존재
- success envelope / error envelope contract 고정
- request ID / security header / explicit CORS / trusted host / rate limit까지 하드닝 완료
- README와 ADR로 기본값이 문서화됨

반면 v1 제품 출시 관점에서 아직 필요한 영역은 아래와 같습니다.

- `services/pipeline/` 신설
- `apps/toss-miniapp/` 신설
- review / launch용 상위 문서와 runbook 정리

## MVP 범위

### 포함
- 신호 목록(브리핑 중심) 화면
- 신호 상세 화면
- empty state / error state / retry
- 이유 / 리스크 / 다음 관찰 포인트 노출
- Brain 결과를 읽기 쉬운 제품 surface로 바꾸는 Pipeline read API
- Toss 로그인 경계와 세션 만료 UX 정의
- Apps in Toss 검수 대응용 문서/체크리스트/런북

### 제외
- Toss Pay / IAP
- 프로모션 푸시
- 고급 개인화
- 멀티마켓 대규모 확장
- 복잡한 추천 실험 플랫폼

## 대표 사용자 흐름

### 1. 홈 진입
1. 사용자가 Apps in Toss에서 MoneySignal miniapp을 연다.
2. 앱은 즉시 팝업/바텀시트를 띄우지 않는다.
3. 홈에서 오늘의 브리핑/관심 신호 목록을 보여준다.

### 2. 신호 상세 보기
1. 사용자가 목록에서 신호를 누른다.
2. 상세 화면에서 아래 정보를 확인한다.
   - 왜 이 신호가 떴는지
   - 어떤 리스크가 있는지
   - 다음에 무엇을 보면 되는지
   - confidence / agent vote / evidence ref
3. 사용자는 뒤로가기 또는 닫기로 자연스럽게 이탈할 수 있다.

### 3. 예외 상황
- 읽을 신호가 없으면 empty state를 보여준다.
- API 오류면 에러 설명과 재시도 경로를 준다.
- 세션 만료 시 로그인 재진입 경로를 명확히 보여준다.

## 아키텍처 원칙

### A. Brain은 평가 엔진 역할에 집중한다
- 입력: `CandidateEventRequest`
- 출력: `EvaluateSignalSuccessResponse` 또는 `ErrorEnvelope`
- 제품용 feed/detail read API를 직접 맡지 않는다.

### B. Pipeline은 제품 surface를 만든다
- 후보 이벤트를 생성/정규화한다.
- Brain evaluate를 호출한다.
- 결과를 저장하거나 replay 가능한 read model로 만든다.
- Miniapp이 읽을 `/feed`, `/signals/{id}` 계열 API를 제공한다.

### C. Miniapp은 Toss 제약 안에서 신뢰 UX를 만든다
- WebView-first
- 라이트 모드 전용
- TDS 기반 UI 우선
- 모호하지 않은 CTA와 명확한 닫기/뒤로가기

## 앱인토스 검수 제약

MoneySignal v1은 아래 제약을 제품 규칙으로 채택합니다.

- Toss 로그인만 사용
- 라이트 모드만 지원
- 진입 즉시 팝업/바텀시트 금지
- 뒤로가기/닫기 경로 필수
- CTA는 목적이 분명해야 함
- TDS 기반 UI 우선
- 번들 크기 100MB 이하 유지

## launch blocker

아래 항목이 비어 있으면 검수/출시 직전 상태로 볼 수 없습니다.

- `services/pipeline/` 구현
- `apps/toss-miniapp/` 구현
- Toss 로그인/세션 경계 정의
- 목록/상세/빈 상태/에러 상태 완성
- review checklist / submission runbook / launch runbook 완성
- staging / review 환경 정리

## 관련 문서

- 시스템 아키텍처 ADR: `../adrs/ADR-001-apps-in-toss-system-architecture.md`
- 앱인토스 검수 체크리스트: `./review-checklist.md`
- 리뷰 제출 런북: `../runbooks/review-submission-runbook.md`
- 출시 런북: `../runbooks/production-launch-runbook.md`
- Agent Brain 스펙: `../superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- Data Pipeline 스펙: `../superpowers/specs/moneysignal-data-pipeline-spec.md`
- Toss Miniapp 스펙: `../superpowers/specs/moneysignal-miniapp-spec.md`
