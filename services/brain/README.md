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
| `uv run pytest tests/integration/test_signals_api.py -q` | success envelope / OpenAPI 검증 |
| `uv run pytest tests/integration/test_error_paths.py -q` | structured error path 검증 |
| `uv run pytest tests/contracts -q` | contract 검증 |
| `uv run ruff check .` | lint 검사 |
| `uv run mypy app` | strict type check |
| `uv run uvicorn app.main:app --reload` | 로컬 API 서버 실행 |

## API 개요

### `GET /health`

서비스 기본 상태 확인용 endpoint입니다.

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

#### 실패 응답 (`422`, `503`, `500`)

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
| `422` | `invalid_request` | request validation 실패 |
| `503` | `analysis_failed` | 최소 specialist coverage 미달 또는 분석 실패 |
| `503` | `upstream_timeout` | upstream timeout |
| `503` | `upstream_unavailable` | upstream connection failure |
| `500` | `internal_error` | 예기치 않은 내부 예외 |

클라이언트 규칙:
- `reject`는 실패가 아니라 정상 결과로 처리합니다.
- 실행 실패는 `decision`이 아니라 `error.code`로 분기합니다.
- `503`은 단일 의미가 아니므로 반드시 `error.code`까지 확인해야 합니다.

## 아키텍처 개요

### 1. HTTP layer
- 파일: `app/main.py`
- 역할: route 정의, OpenAPI surface, structured error handler
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
- 역할: threshold, timeout, concurrency, provider default를 환경 변수 기반으로 로드

## 현재 v1 기본값

- `briefing_threshold = 0.55`
- `instant_push_threshold = 0.80`
- `specialist_concurrency_limit = 4`
- `per_agent_timeout_ms = 3000`
- `provider_strategy = "stubbed"`
- `fixture_scope = "KR_ONLY"`

## 관련 문서

- 제품 스펙: `../../docs/superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- ADR-001: `docs/adrs/ADR-001-v1-defaults.md`
- ADR-002: `docs/adrs/ADR-002-evaluate-signal-api-surface.md`

## 주의할 점

- v1은 deterministic stubbed runtime 기준입니다.
- runtime failure를 가짜 `reject`로 포장하면 안 됩니다.
- public error shape는 provider-native 오류 형식으로 오염되면 안 됩니다.
- contract 변경 시 테스트만이 아니라 ADR/README도 함께 갱신해야 합니다.
