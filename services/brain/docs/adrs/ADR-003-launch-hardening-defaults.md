# ADR-003: 런치 하드닝 기본값을 gateway-first로 고정

- Status: Accepted
- Date: 2026-04-19
- Deciders: Agent Brain launch hardening slice
- Related ADR: `services/brain/docs/adrs/ADR-001-v1-defaults.md`
- Related ADR: `services/brain/docs/adrs/ADR-002-evaluate-signal-api-surface.md`
- Related spec: `docs/superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- Related implementation: `services/brain/app/main.py`, `services/brain/app/config.py`

## Context
`services/brain`의 기존 baseline은 로컬 개발과 contract 검증에는 충분했지만, 실제 배포 경계로 노출하기에는 아래 공백이 있었다.

1. success path에는 request tracing이 없어 운영 추적성이 약했다.
2. security header가 framework 기본값에 의존하고 있었다.
3. direct browser/WebView 호출과 trusted gateway/backend 호출을 모두 지원해야 했지만, CORS 정책이 명시적으로 잠겨 있지 않았다.
4. trusted host와 request throttling이 없어 잘못된 boundary 설정을 빨리 차단하기 어려웠다.
5. launch/rollback 문서가 없어 운영자가 무엇을 확인해야 하는지 코드 밖에서 즉시 알기 어려웠다.

사용자 요구는 **양쪽 지원**이지만, 기본값은 더 안전한 **gateway-first**여야 했다.

## Decision

### 1. 배포 경계 기본 모드는 gateway-first다
- Brain은 direct browser/WebView 호출과 trusted gateway/backend 호출을 모두 지원한다.
- 그러나 기본값은 gateway/backend 경유를 우선한다.
- 따라서 CORS는 기본적으로 닫혀 있으며, direct 호출이 필요할 때만 explicit allowlist로 연다.
- Brain 자체에 별도 인증 시스템을 추가하지는 않는다.

### 2. 모든 응답에 request ID를 부여한다
- success와 failure 모두 `X-Request-ID` header를 가진다.
- error path에서는 `error.trace_id`가 같은 값을 반영한다.
- success body contract는 바꾸지 않고 transport header로만 tracing을 노출한다.

기본값:
- `BRAIN_REQUEST_ID_HEADER_NAME = x-request-id`

### 3. 보안 header는 명시적으로 고정한다
아래 header를 HTTP boundary에서 항상 설정한다.

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`

이 결정은 Brain이 HTML app가 아니라 JSON API surface라는 점을 전제로 한다.

### 4. CORS와 trusted hosts는 env allowlist로만 연다
기본값:
- `BRAIN_CORS_ALLOW_ORIGINS = ()`
- `BRAIN_CORS_ALLOW_CREDENTIALS = false`
- `BRAIN_TRUSTED_HOSTS = ()`

규칙:
- wildcard CORS는 허용하지 않는다.
- credential 허용은 allowlist origin이 있을 때만 의미가 있다.
- trusted host enforcement는 boundary가 분명한 환경에서만 켠다.

### 5. app-layer rate limiting은 best-effort 보호층으로 둔다
기본값:
- `BRAIN_RATE_LIMIT_ENABLED = false`
- `BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR = false`
- `BRAIN_RATE_LIMIT_TRUSTED_PROXY_CLIENTS = ()`
- `BRAIN_RATE_LIMIT_WINDOW_SECONDS = 60`
- `BRAIN_RATE_LIMIT_MAX_REQUESTS = 60`

규칙:
- 이 throttling은 process-local best-effort 보호층이다.
- 다중 인스턴스/다중 리전 환경의 글로벌 제어는 gateway나 upstream edge에서 담당한다.
- `X-Forwarded-For`는 기본적으로 신뢰하지 않으며, trusted proxy client allowlist에 포함된 upstream에서 들어온 요청일 때만 사용한다.
- direct browser/WebView exposure 시에는 app-layer limit를 보조 안전장치로 둘 수 있다.

## Alternatives considered

### A. direct browser/WebView를 기본 경로로 두고 CORS를 기본 개방
- 장점: 초기 연결이 단순해 보인다.
- 단점: origin 통제가 느슨해지고, gateway를 둘 수 있는 배포에서도 너무 넓은 기본값이 된다.
- 기각 이유: safer default 원칙에 어긋난다.

### B. gateway/backend 경유만 허용하고 direct 호출은 막기
- 장점: 경계가 단순해지고 CORS를 완전히 피할 수 있다.
- 단점: Toss WebView나 이후 direct integration 실험 유연성이 줄어든다.
- 기각 이유: 사용자 요구가 양쪽 지원이므로 너무 제한적이다.

### C. gateway에만 rate limiting을 두고 app 내부 throttling은 생략
- 장점: 중복 제어가 줄어든다.
- 단점: direct exposure나 gateway misconfiguration 시 최소 보호층이 사라진다.
- 기각 이유: app 내부에도 best-effort 안전장치가 있는 편이 launch-readiness에 유리하다.

## Consequences

### Positive
- gateway를 둘 수 있는 환경에서 더 안전한 기본값을 유지한다.
- direct browser/WebView exposure도 explicit config로 열 수 있다.
- request tracing이 success/error 전 경로에 생긴다.
- security/CORS/trusted-host/rate-limit 정책이 코드와 문서 양쪽에서 고정된다.

### Trade-offs
- direct 호출을 쓰려면 환경 변수 설정이 더 필요하다.
- app-layer throttling은 글로벌 quota가 아니므로 운영자가 그 한계를 이해해야 한다.
- trusted host allowlist를 잘못 설정하면 정상 요청도 400으로 막힐 수 있다.

## Verification
- `services/brain/tests/integration/test_health.py`
- `services/brain/tests/integration/test_signals_api.py`
- `services/brain/tests/integration/test_error_paths.py`
- `services/brain/README.md`
- `services/brain/docs/launch-runbook.md`
