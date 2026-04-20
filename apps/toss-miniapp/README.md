# MoneySignal Toss Miniapp

`apps/toss-miniapp`은 Apps in Toss WebView 안에서 MoneySignal의 제품 surface를 렌더링하는 React + TypeScript miniapp입니다. v1에서는 신호 목록, 상세, 도움말, empty/error/session 상태를 명확하고 review-safe한 UX로 제공하는 데 집중합니다.

## 역할

이 miniapp은 아래 화면을 제공합니다.

- 홈 신호 목록
- 신호 상세
- empty state
- error state with retry
- 도움말 / 서비스 안내
- session-expired / unauthenticated 안내

## 실행

### 1. 의존성 설치

```bash
npm install
```

### 2. 개발 서버 실행

```bash
npm run dev
```

### 3. 기본 검증

```bash
npm run test
npm run build
npm run lint
```

## 환경 변수

| 환경 변수 | 기본값 | 설명 |
|---|---|---|
| `VITE_PIPELINE_BASE_URL` | 비어 있음 | miniapp이 읽을 Pipeline base URL |

예시:

```bash
VITE_PIPELINE_BASE_URL=http://127.0.0.1:8010 npm run dev
```

## 현재 구현 화면

### 홈
- 목적 소개 hero
- 신호 목록
- 도움말 진입
- 닫기 버튼

### 상세
- 이유
- 리스크
- 다음에 볼 포인트
- confidence / agent vote
- 목록으로 돌아가기

### 예외 상태
- empty state
- error + retry
- expired session
- unauthenticated session

## host bridge 계약

Apps in Toss 또는 embedding host가 아래 bridge를 주입할 수 있습니다.

```ts
type MoneySignalHost = {
  close?: () => void;
  reenterSession?: () => void;
};
```

규칙:
- `close`가 없으면 닫기 버튼은 disabled 상태입니다.
- `reenterSession`이 없으면 세션 재진입 CTA는 disabled 상태입니다.
- miniapp은 host bridge가 없는 로컬 개발 환경에서도 안전하게 렌더링되어야 합니다.

## review / staging 기준

review/staging에서는 아래를 고정하는 것을 권장합니다.

- light mode only
- 첫 진입 즉시 popup/bottom sheet 없음
- 홈에서 앱 목적이 1분 안에 이해 가능
- 뒤로가기/닫기 경로 항상 명확
- CTA는 `신호 자세히 보기`, `다시 불러오기`, `토스에서 다시 열기`처럼 목적이 분명한 문구 사용

## 검증 기준

다음 항목을 통과해야 제출 빌드 후보로 봅니다.

- 목록/상세/도움말/empty/error/session 상태 렌더링
- host bridge 유무에 따른 안전한 버튼 동작
- 라이트 모드만 노출
- mobile WebView 폭에서도 레이아웃 유지
- console error 없이 로드

## 관련 문서

- 제품 MVP: `../../docs/product/apps-in-toss-mvp.md`
- miniapp 스펙: `../../docs/superpowers/specs/moneysignal-miniapp-spec.md`
- 검수 체크리스트: `../../docs/product/review-checklist.md`
- 리뷰 제출 런북: `../../docs/runbooks/review-submission-runbook.md`
