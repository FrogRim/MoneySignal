# MoneySignal Agent Brain Launch Runbook

## 목적
이 문서는 `services/brain`를 실제 배포 경계 뒤에 올릴 때 필요한 preflight, smoke check, monitoring, rollback 절차를 정리합니다.

핵심 원칙:
- Brain은 **양쪽 지원**(direct browser/WebView + trusted gateway/backend)을 하되, 기본값은 **gateway-first**입니다.
- app-layer rate limiting은 **best-effort** 보호층일 뿐이며, gateway throttling을 대체하지 않습니다.
- 문제를 `reject`로 숨기지 말고 `error.code`와 `X-Request-ID` 기준으로 운영합니다.

## 배포 전 preflight checklist

### 1. 코드 검증
아래 명령이 모두 통과해야 합니다.

```bash
uv run pytest -q
uv run ruff check .
uv run mypy app
uv build
```

### 2. 배포 경계 선택
이번 배포가 어느 경계인지 먼저 고릅니다.

#### A. gateway/backend 경유 배포 (권장 기본값)
권장 설정:
- `BRAIN_CORS_ALLOW_ORIGINS` 비움
- gateway에서 인증/인가/primary throttling 처리
- 필요 시 `BRAIN_TRUSTED_HOSTS`로 public host 고정
- app-layer rate limit은 보조 안전장치로만 사용

#### B. browser/WebView direct 배포
필수 검토:
- `BRAIN_CORS_ALLOW_ORIGINS`에 허용 origin 명시
- 필요 시 `BRAIN_TRUSTED_HOSTS` 설정
- `BRAIN_RATE_LIMIT_ENABLED=true` 고려
- gateway가 없더라도 운영자가 429 spike를 직접 모니터링할 수 있어야 함

### 3. 환경 변수 확인
최소 확인 항목:

| 변수 | 확인 포인트 |
|---|---|
| `BRAIN_REQUEST_ID_HEADER_NAME` | 기본값 유지 여부 (`x-request-id`) |
| `BRAIN_CORS_ALLOW_ORIGINS` | direct 호출이 필요한 경우에만 설정 |
| `BRAIN_CORS_ALLOW_CREDENTIALS` | 꼭 필요한 경우에만 `true` |
| `BRAIN_TRUSTED_HOSTS` | boundary가 분명할 때만 설정 |
| `BRAIN_RATE_LIMIT_ENABLED` | direct exposure 여부에 맞춰 활성화 |
| `BRAIN_RATE_LIMIT_WINDOW_SECONDS` | 너무 짧지 않은지 확인 |
| `BRAIN_RATE_LIMIT_MAX_REQUESTS` | 초기 사용자 수 대비 과도하게 낮지 않은지 확인 |

## 배포 직후 first-hour smoke checks

### 1. Health check
배포된 base URL을 환경 변수로 잡고 확인합니다.

```bash
curl "$BRAIN_BASE_URL/health"
```

확인 포인트:
- HTTP `200`
- body: `{"status":"ok"}`
- `X-Request-ID` header 존재
- 보안 header 존재

### 2. 성공 경로 smoke test
정상 fixture payload로 `POST /v1/signals/evaluate`를 한 번 호출합니다.

확인 포인트:
- HTTP `200`
- expected success envelope shape
- `X-Request-ID` header 존재
- direct 호출을 여는 환경이라면 allowed origin에서만 `Access-Control-Allow-Origin`이 붙는지 확인

### 3. 실패 경로 smoke test
최소 한 번은 boundary failure 또는 validation failure를 확인합니다.

권장 확인 케이스:
- invalid payload → `422 invalid_request`
- rate limit 초과(활성화된 환경) → `429 rate_limited`

확인 포인트:
- `error.code`가 기대와 일치하는지
- `X-Request-ID`와 `error.trace_id`가 같은지
- raw exception text가 노출되지 않는지

## Monitoring signals

### 반드시 보는 항목
- `/health` 실패율
- 전체 5xx 비율
- `503` 세부 code 비율
  - `analysis_failed`
  - `upstream_timeout`
  - `upstream_unavailable`
- `429 rate_limited` 비율
- p95 / p99 latency

### 추가로 보면 좋은 항목
- `400 invalid_request` 증가 추이
  - trusted host 설정이 잘못되었는지 빠르게 감지 가능
- `422 invalid_request` 증가 추이
  - client payload regression 감지에 유용
- allowed/disallowed origin 관련 CORS 이슈 리포트

## Rollback trigger

아래 상황이면 즉시 rollback 또는 config rollback을 검토합니다.

- health check 실패가 지속됨
- 전체 5xx 비율이 baseline 대비 의미 있게 증가함
- `upstream_timeout` 또는 `upstream_unavailable`이 급증함
- 정상 client에서 `400 invalid_request`가 다수 발생함
- 정상 client에서 `429 rate_limited`가 예상보다 빠르게 증가함
- direct 호출 환경에서 CORS misconfiguration으로 정상 origin 요청이 실패함

## Rollback steps

### 1. config rollback
문제가 hardening 설정에서 시작됐다면 먼저 설정을 되돌립니다.

예시:
- direct 호출이 아닌데 CORS를 열어둠 → `BRAIN_CORS_ALLOW_ORIGINS` 비움
- trusted host가 정상 host를 막음 → `BRAIN_TRUSTED_HOSTS` 수정 또는 비움
- rate limit이 너무 공격적임 → `BRAIN_RATE_LIMIT_ENABLED=false` 또는 window/max 상향

### 2. deploy rollback
config rollback으로 해결되지 않으면 이전 정상 배포로 되돌립니다.

원칙:
- app hardening rollback 후에도 `/health`와 대표 `POST /v1/signals/evaluate` smoke test를 다시 실행합니다.
- rollback 후에도 `X-Request-ID`와 structured error contract가 유지되는지 확인합니다.

### 3. incident note 남기기
최소한 아래를 기록합니다.
- 언제 감지했는지
- 어떤 지표가 먼저 흔들렸는지
- 어떤 config/deploy를 되돌렸는지
- 다음 배포 전에 무엇을 추가 검증해야 하는지

## 운영 메모
- multi-instance 환경에서는 app-layer rate limit 수치만으로 글로벌 quota를 해석하면 안 됩니다.
- direct browser/WebView exposure를 열수록 CORS, trusted host, 429 추적 중요도가 올라갑니다.
- Brain은 market result(`reject`)와 system failure를 섞지 않는 것이 핵심이므로, 운영 문서와 대시보드도 이 구분을 유지해야 합니다.
