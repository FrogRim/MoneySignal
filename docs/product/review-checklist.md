# MoneySignal Apps in Toss 검수 체크리스트

## 목적

이 문서는 MoneySignal miniapp이 Apps in Toss 검수에서 확인될 핵심 항목을 구현과 연결하기 위한 체크리스트입니다. 체크리스트는 "검수 직전 확인" 용도뿐 아니라, 구현 과정에서 scope를 잃지 않기 위한 기준선으로도 사용합니다.

## 제품/UX

- [ ] 진입 즉시 팝업/바텀시트를 띄우지 않는다.
- [ ] 홈 진입 후 사용자는 1분 안에 앱의 목적을 이해할 수 있다.
- [ ] 뒤로가기와 닫기 경로가 화면 수준에서 명확하다.
- [ ] CTA 문구가 모호하지 않다.
  - 예: `신호 자세히 보기`, `브리핑 확인하기`, `다시 불러오기`
- [ ] empty state가 존재한다.
- [ ] error state와 retry 경로가 존재한다.
- [ ] 세션 만료 상태와 재진입 UX가 정의되어 있다.

## 디자인 / 플랫폼

- [ ] 라이트 모드만 지원한다.
- [ ] TDS 기반 UI를 우선 사용한다.
- [ ] 텍스트 대비와 터치 영역이 기본 접근성 기준을 충족한다.
- [ ] Safe Area를 고려한 레이아웃이다.
- [ ] 앱 번들 크기가 100MB 이하이다.

## 인증 / 정책

- [ ] Toss 로그인만 사용한다.
- [ ] 서드파티 로그인 경로가 없다.
- [ ] Toss Pay / IAP는 이번 범위에서 제외되어 있거나, 필요 시 별도 검수 준비가 되어 있다.
- [ ] 프로모션 푸시 의존 기능이 없다.

## 백엔드 / 계약

- [ ] Brain의 success/error contract가 문서와 테스트로 고정되어 있다.
- [ ] Pipeline이 Brain input contract를 깨지 않는다.
- [ ] Miniapp이 hand-made mock JSON이 아니라 read API를 읽는다.
- [ ] request ID와 structured error가 운영 추적에 활용 가능하다.

## 운영 / 제출

- [x] reviewer walkthrough 문서가 있다.
- [ ] 테스트 계정/테스트 데이터 준비가 되어 있다.
- [ ] staging 또는 review 환경 URL이 준비되어 있다.
- [x] production launch runbook이 있다.
- [x] rollback trigger와 절차가 정의되어 있다.
- [x] review / staging 환경 변수 매트릭스가 문서화되어 있다.

## 제출 직전 확인

- [ ] 홈 → 목록 → 상세 → 뒤로가기 흐름이 자연스럽다.
- [ ] 첫 진입에서 불필요한 방해 요소가 없다.
- [ ] 핵심 카피가 의견형/가이드형 톤을 유지하면서 직접적인 매수/매도 명령으로 보이지 않는다.
- [ ] 에러가 나도 내부 예외나 민감한 구현 세부사항을 노출하지 않는다.
- [ ] 문서(README / spec / ADR / runbook)가 현재 구현과 어긋나지 않는다.
