# MoneySignal Agent Brain

`services/brain`는 candidate event를 받아 **신호 평가 결과**를 반환하는 FastAPI 서비스입니다. v1에서는 deterministic stubbed runtime을 사용하며, live provider 없이도 계약·오케스트레이션·API surface를 검증할 수 있도록 설계되어 있습니다.

## 역할

이 서비스는 입력 이벤트를 받아 아래 세 가지 결과 중 하나를 반환합니다.

- `reject`: 지금은 알림/브리핑을 보내지 않음
- `briefing`: 정기 브리핑에 포함할 관심 신호
- `instant_push`: 강한 합의가 형성된 즉시 알림 신호

## 빠른 시작

### 1. 의존성 동기화

```bash
uv sync
```

### 2. 개발 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

### 3. 헬스 체크

```bash
curl http://127.0.0.1:8000/health
```

예상 응답:

```json
{"status":"ok"}
```

## 주요 명령어

| 명령어 | 설명 |
|---|---|
| `uv run pytest -q` | 전체 테스트 실행 |
| `uv run pytest tests/integration/test_health.py -q` | health + request/security header 검증 |
| `uv run pytest tests/integration/test_signals_api.py -q` | success envelope / OpenAPI / CORS / rate limit 검증 |
| `uv run pytest tests/integration/test_error_paths.py -q` | structured error path + trace header 검증 |
| `uv run pytest tests/contracts -q` | contract 검증 |
| `uv run ruff check .` | lint 검사 |
| `uv run mypy app` | strict type check |
| `uv run uvicorn app.main:app --reload` | 로컬 API 서버 실행 |

## API 개요

### `GET /health`

서비스 기본 상태 확인용 endpoint입니다.

응답 body 외에 아래 HTTP 경계 보장도 함께 확인할 수 있습니다.
- `X-Request-ID` header
- 보안 header (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`)

### `POST /v1/signals/evaluate`

candidate event를 평가해 success envelope 또는 error envelope를 반환합니다.

#### 요청

요청 body는 `CandidateEventRequest` shape를 따릅니다.

핵심 필드:
- `candidate_id`
- `asset`
- `trigger_type`
- `event_ts`
- `market_snapshot`
- `news_items`
- `flow_snapshot`
- `theme_context`
- `metadata.gate_score`
- `metadata.event_ref`
- `metadata.stub_agent_outputs`

#### 성공 응답 (`200`)

성공 응답은 `EvaluateSignalSuccessResponse`입니다.

```json
{
  "decision": "briefing",
  "gate": {
    "score": 0.7,
    "reason": "event relevance passed the briefing threshold"
  },
  "signal_card": {
    "id": "sig_20260416_001",
    "title": "삼성전자에 관심 신호가 포착됐어요",
    "asset": {
      "symbol": "005930",
      "name": "삼성전자",
      "market": "KR"
    },
    "signal_strength": "watch",
    "summary": "가격 반등과 거래량 증가, 관련 업황 뉴스가 함께 나타났습니다.",
    "reasons": [
      "거래량이 평소 대비 크게 증가했습니다.",
      "관련 업황 뉴스가 동시에 유입됐습니다."
    ],
    "risks": [
      "단기 과열 후 되돌림 가능성이 있습니다."
    ],
    "watch_action": "오늘 장 마감 전 수급 흐름이 유지되는지 확인해보세요.",
    "broker_deeplink_hint": {
      "broker": "toss_securities",
      "symbol": "005930"
    },
    "agent_votes": [
      {"agent": "chart", "stance": "positive", "confidence": 0.78},
      {"agent": "news", "stance": "positive", "confidence": 0.81},
      {"agent": "flow", "stance": "neutral", "confidence": 0.55},
      {"agent": "risk", "stance": "cautious", "confidence": 0.64}
    ],
    "confidence": 0.76,
    "evidence_refs": [
      {"type": "market_event", "ref": "evt_123"},
      {"type": "news", "ref": "news_1"}
    ]
  }
}
```

규칙:
- `reject`는 정상 비즈니스 결과입니다.
- `reject`일 때만 `signal_card`는 `null`입니다.
- `briefing`과 `instant_push`는 반드시 `signal_card`를 포함합니다.
- 모든 성공 응답은 `X-Request-ID` header를 포함합니다.

#### 실패 응답 (`400`, `422`, `429`, `503`, `500`)

실패 응답은 `ErrorEnvelope`로 고정됩니다.

```json
{
  "error": {
    "code": "analysis_failed",
    "message": "minimum specialist coverage not met",
    "retryable": true,
    "failed_agents": ["flow"],
    "trace_id": "req_20260416_001"
  }
}
```

상태 코드/에러 코드 매핑:

| HTTP status | error.code | 설명 |
|---|---|---|
| `400` | `invalid_request` | trusted host 정책에 의해 host header가 거부됨 |
| `422` | `invalid_request` | request validation 실패 |
| `429` | `rate_limited` | API-layer best-effort rate limiting 초과 |
| `503` | `analysis_failed` | 최소 specialist coverage 미달 또는 분석 실패 |
| `503` | `upstream_timeout` | upstream timeout |
| `503` | `upstream_unavailable` | upstream connection failure |
| `500` | `internal_error` | 예기치 않은 내부 예외 |

클라이언트 규칙:
- `reject`는 실패가 아니라 정상 결과로 처리합니다.
- 실행 실패는 `decision`이 아니라 `error.code`로 분기합니다.
- `503`은 단일 의미가 아니므로 반드시 `error.code`까지 확인해야 합니다.
- 실패 응답에서는 `X-Request-ID` header와 `error.trace_id`가 같은 값이어야 합니다.

## HTTP 경계 하드닝 기본값

Brain은 브라우저/WebView direct 호출과 trusted gateway/backend 호출을 모두 지원하지만, 기본값은 **gateway-first**입니다.

기본 정책:
- 모든 응답에 `X-Request-ID`를 부여합니다.
- 보안 header를 framework 기본값에 맡기지 않고 명시적으로 설정합니다.
- CORS는 기본적으로 비활성화되어 있으며, 허용 origin을 명시한 경우에만 열립니다.
- credential 허용은 기본적으로 꺼져 있습니다.
- trusted host allowlist는 선택 사항이며, 지정 시 `Host` header를 검사합니다.
- `X-Forwarded-For`는 기본적으로 rate limit 식별에 사용하지 않으며, trusted proxy client allowlist가 있을 때만 사용합니다.
- app 내부 rate limiting은 **best-effort** 보호층이며, gateway 레벨 throttling을 대체하지 않습니다.

현재 보안 header 기본값:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`

## 환경 변수

| 환경 변수 | 기본값 | 설명 |
|---|---|---|
| `BRAIN_REQUEST_ID_HEADER_NAME` | `x-request-id` | 응답에 넣을 request ID header 이름 |
| `BRAIN_CORS_ALLOW_ORIGINS` | 비어 있음 | direct browser/WebView 호출을 열 origin allowlist (comma-separated) |
| `BRAIN_CORS_ALLOW_CREDENTIALS` | `false` | CORS credential 허용 여부 |
| `BRAIN_TRUSTED_HOSTS` | 비어 있음 | 허용할 host allowlist (comma-separated) |
| `BRAIN_RATE_LIMIT_ENABLED` | `false` | app-layer rate limiting 사용 여부 |
| `BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR` | `false` | trusted proxy 요청에서만 `X-Forwarded-For`를 client 식별값으로 사용할지 여부 |
| `BRAIN_RATE_LIMIT_TRUSTED_PROXY_CLIENTS` | 비어 있음 | `X-Forwarded-For`를 신뢰할 upstream proxy client IP allowlist (comma-separated) |
| `BRAIN_RATE_LIMIT_WINDOW_SECONDS` | `60` | rate limit window 크기 |
| `BRAIN_RATE_LIMIT_MAX_REQUESTS` | `60` | window 당 허용 요청 수 |
| `BRAIN_BRIEFING_THRESHOLD` | `0.55` | briefing 결정 최소 점수 |
| `BRAIN_INSTANT_PUSH_THRESHOLD` | `0.80` | instant push 결정 최소 점수 |
| `BRAIN_SPECIALIST_CONCURRENCY_LIMIT` | `4` | specialist 병렬 실행 상한 |
| `BRAIN_PER_AGENT_TIMEOUT_MS` | `3000` | per-agent timeout |

권장 배포 패턴:
- **gateway/backend 경유**: `BRAIN_CORS_ALLOW_ORIGINS`를 비워 두고 gateway 쪽 인증/throttle를 1차 경계로 둡니다. reverse proxy가 `X-Forwarded-For`를 재작성하는 환경에서만 `BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR=true`와 `BRAIN_RATE_LIMIT_TRUSTED_PROXY_CLIENTS`를 함께 설정합니다.
- **browser/WebView direct**: `BRAIN_CORS_ALLOW_ORIGINS`를 명시하고, 필요 시 `BRAIN_TRUSTED_HOSTS`와 `BRAIN_RATE_LIMIT_*`를 함께 설정합니다. direct 노출에서는 `BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR=false` 기본값을 유지합니다.

## 아키텍처 개요

### 1. HTTP layer
- 파일: `app/main.py`
- 역할: route 정의, request ID 부여, security/CORS/trusted-host/rate-limit 경계 처리, structured error handler
- 원칙: 오케스트레이션 로직을 여기로 끌어올리지 않음

### 2. Orchestrator
- 파일: `app/orchestrators/evaluate_signal.py`
- 역할: gate 판단 → specialist 병렬 실행 → editor 조합 → success response 생성
- 실패 시 `AnalysisFailedError`를 통해 API layer로 전달

### 3. Runtime
- 파일: `app/runtime/parallel.py`
- 역할: bounded concurrency, per-agent timeout, minimum success handling

### 4. Contracts
- 파일: `app/contracts/input.py`, `app/contracts/output.py`, `app/contracts/errors.py`
- 역할: request/success/error public shape 고정

### 5. Config
- 파일: `app/config.py`
- 역할: threshold, timeout, CORS, trusted hosts, rate limit, request ID defaults를 환경 변수 기반으로 로드

## 현재 v1 기본값

- `briefing_threshold = 0.55`
- `instant_push_threshold = 0.80`
- `specialist_concurrency_limit = 4`
- `per_agent_timeout_ms = 3000`
- `provider_strategy = "stubbed"`
- `fixture_scope = "KR_ONLY"`
- `request_id_header_name = "x-request-id"`
- `cors_allow_origins = ()`
- `cors_allow_credentials = false`
- `trusted_hosts = ()`
- `rate_limit_enabled = false`
- `rate_limit_window_seconds = 60`
- `rate_limit_max_requests = 60`

## 런치/운영 체크

런치 전후 운영 절차는 별도 runbook으로 관리합니다.

- preflight checklist
- first-hour smoke checks
- monitoring signal list
- rollback trigger / rollback steps

자세한 절차는 `docs/launch-runbook.md`를 참고하세요.

## 관련 문서

- 제품 스펙: `../../docs/superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- ADR-001: `docs/adrs/ADR-001-v1-defaults.md`
- ADR-002: `docs/adrs/ADR-002-evaluate-signal-api-surface.md`
- ADR-003: `docs/adrs/ADR-003-launch-hardening-defaults.md`
- 런치 런북: `docs/launch-runbook.md`

## 주의할 점

- v1은 deterministic stubbed runtime 기준입니다.
- runtime failure를 가짜 `reject`로 포장하면 안 됩니다.
- public error shape는 provider-native 오류 형식으로 오염되면 안 됩니다.
- app-layer rate limit은 process-local best-effort 보호이므로, 다중 인스턴스 환경에서는 gateway 레벨 제어가 우선입니다.
- contract 변경 시 테스트만이 아니라 ADR/README도 함께 갱신해야 합니다.
