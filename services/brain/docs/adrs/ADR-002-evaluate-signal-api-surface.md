# ADR-002: `/v1/signals/evaluate` 공개 API surface를 success/error 이원화로 고정

- Status: Accepted
- Date: 2026-04-19
- Deciders: Agent Brain API slice
- Related ADR: `services/brain/docs/adrs/ADR-001-v1-defaults.md`
- Related ADR: `services/brain/docs/adrs/ADR-003-launch-hardening-defaults.md`
- Related spec: `docs/superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- Related implementation: `services/brain/app/main.py`

## Context
MoneySignal Agent Brain의 첫 public HTTP endpoint는 candidate event를 받아 `reject`, `briefing`, `instant_push` 중 하나의 시장 판단을 반환한다.

여기서 가장 중요한 경계는 **시장 판단 실패**와 **시스템 실행 실패**를 절대 섞지 않는 것이다.

막아야 하는 문제는 아래와 같다.

1. `reject`를 에러처럼 다뤄서 정상 비즈니스 결과를 실패로 오해하는 문제
2. runtime failure를 가짜 `reject`로 포장해서 재시도 가능성과 장애 원인을 잃는 문제
3. provider나 내부 runtime의 오류 shape가 public API contract로 새어 나가는 문제
4. 예기치 않은 예외 메시지가 그대로 외부에 노출되는 문제
5. HTTP 경계 하드닝이 추가되면서 request tracing이나 throttling 같은 운영 정보가 기존 success/error 의미를 흔드는 문제

MoneySignal 클라이언트는 이 endpoint를 기준으로 알림/브리핑 후속 동작을 결정하므로, 응답 shape가 작고 안정적이며 기계적으로 분기 가능해야 한다.

## Decision

### 1. 성공 응답은 시장 결과만 표현한다
- `POST /v1/signals/evaluate`의 요청 본문은 `CandidateEventRequest`로 고정한다.
- HTTP `200` 응답은 항상 `EvaluateSignalSuccessResponse`를 사용한다.
- `decision` 값은 `reject`, `briefing`, `instant_push` 중 하나다.
- `reject`는 유효한 비즈니스 결과이며 에러가 아니다.
- `reject`일 때만 `signal_card = null`을 허용한다.
- `briefing`과 `instant_push`는 반드시 `signal_card`를 포함해야 한다.
- request tracing이 필요하더라도 success body에는 tracing field를 추가하지 않고, `X-Request-ID` header로만 노출한다.

### 2. 실패 응답은 항상 structured error envelope를 사용한다
Validation failure, runtime failure, boundary hardening failure, system failure는 success envelope를 절대 사용하지 않는다.

모든 실패 응답은 아래 shape를 갖는 `ErrorEnvelope`로 고정한다.

- `error.code`
- `error.message`
- `error.retryable`
- `error.failed_agents`
- `error.trace_id`

상태 코드와 에러 코드는 아래처럼 매핑한다.

| HTTP status | error.code | 의미 |
|---|---|---|
| 400 | `invalid_request` | trusted host 정책에 의해 host header가 거부됨 |
| 422 | `invalid_request` | FastAPI boundary에서 request validation 실패 |
| 429 | `rate_limited` | API-layer best-effort rate limiting 초과 |
| 503 | `analysis_failed` | 오케스트레이션 최소 커버리지 미달 또는 분석 실패 |
| 503 | `upstream_timeout` | 평가 도중 upstream timeout 발생 |
| 503 | `upstream_unavailable` | 평가 도중 upstream connection failure 발생 |
| 500 | `internal_error` | 예기치 않은 내부 예외 |

### 3. 운영 규칙은 `error.code`와 `X-Request-ID` 중심으로 고정한다
- 클라이언트는 `503`만 보고 처리하지 않고 반드시 `error.code`로 세부 분기한다.
- 모든 성공/실패 응답은 `X-Request-ID` header를 포함한다.
- 실패 응답에서는 `X-Request-ID`와 `error.trace_id`가 같은 값이어야 한다.
- 예기치 않은 내부 예외는 `internal server error`로 감싸고 raw exception text를 외부로 노출하지 않는다.
- route는 얇은 HTTP adapter로 유지하고, 오케스트레이션 로직은 `EvaluateSignalService`에 남긴다.

## Alternatives considered

### A. `reject`를 4xx/5xx 에러로 다루기
- 장점: 클라이언트가 성공/실패를 HTTP status만으로 단순 분기할 수 있다.
- 단점: `reject`는 시장 결과인데 실패처럼 보이게 되어 product semantics가 왜곡된다.
- 기각 이유: `reject`는 “문제가 생겼다”가 아니라 “지금은 보낼 신호가 없다”는 정상 결과이므로 에러 surface에 넣으면 안 된다.

### B. runtime failure를 가짜 `reject` success envelope로 포장하기
- 장점: 응답 shape를 하나로 통일할 수 있다.
- 단점: retryability, `failed_agents`, `trace_id`를 잃고 장애가 시장 판단처럼 보이게 된다.
- 기각 이유: 운영 관측성과 클라이언트 복구 전략을 망가뜨리므로 허용하지 않는다.

### C. provider-native error shape를 그대로 노출하기
- 장점: 내부 runtime이 가진 상세 원인을 그대로 전달할 수 있다.
- 단점: public contract가 내부 구현과 provider 선택에 종속되고, 이후 교체/확장이 어려워진다.
- 기각 이유: v1 public API는 provider-agnostic contract를 유지해야 하므로 내부 오류 shape를 외부 계약으로 승격하지 않는다.

### D. success body에도 `trace_id`를 넣기
- 장점: 모든 응답을 body만으로 추적할 수 있다.
- 단점: success contract가 운영용 field 때문에 불필요하게 커지고, product 의미와 transport metadata가 섞인다.
- 기각 이유: tracing은 header로 충분하며, success envelope는 시장 결과 표현에 집중해야 한다.

## Consequences

### Positive
- 클라이언트가 비즈니스 결과와 시스템 실패를 안정적으로 구분할 수 있다.
- OpenAPI에 성공/실패 shape가 명확히 선언되어 integration cost가 낮아진다.
- `retryable`, `failed_agents`, `trace_id`를 통해 운영 대응과 재시도 정책을 분리할 수 있다.
- `X-Request-ID` header를 통해 success path도 body contract를 바꾸지 않고 추적할 수 있다.
- API layer와 orchestration layer의 경계가 유지된다.

### Trade-offs
- `503` 하나에 여러 failure class가 공존하므로 클라이언트는 반드시 `error.code`까지 확인해야 한다.
- `400`/`422`가 모두 `invalid_request`를 사용하므로 클라이언트는 status와 message를 함께 봐야 할 수 있다.
- `429`는 app 내부 best-effort throttling 결과이며, 글로벌 gateway quota와 동일 의미는 아니다.
- 새로운 public error code나 envelope field를 추가하려면 spec 또는 후속 ADR이 필요하다.

## Verification
- `services/brain/tests/integration/test_health.py`
- `services/brain/tests/integration/test_signals_api.py`
- `services/brain/tests/integration/test_error_paths.py`
- `services/brain/tests/contracts/test_error_contract.py`
