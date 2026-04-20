# MoneySignal Pipeline

`services/pipeline`는 MoneySignal miniapp이 직접 읽는 제품용 read API를 제공하는 FastAPI 서비스입니다. v1에서는 deterministic fixture replay를 기준으로 Brain evaluate 결과를 feed/detail read model로 변환하고, review/demo 환경에서 같은 흐름을 반복 재생할 수 있도록 설계되어 있습니다.

## 역할

이 서비스는 아래 책임을 가집니다.

- candidate fixture 또는 정규화된 입력 로드
- Brain `POST /v1/signals/evaluate` 호출
- 허용된 신호 결과를 feed store에 반영
- miniapp용 `GET /session`, `GET /feed`, `GET /signals/{id}` 제공
- review/demo 환경에서 deterministic fixture replay 유지

## 빠른 시작

### 1. 의존성 동기화

```bash
uv sync
```

### 2. 개발 서버 실행

```bash
uv run uvicorn app.main:app --reload --port 8010
```

### 3. 기본 확인

```bash
curl http://127.0.0.1:8010/session
curl http://127.0.0.1:8010/feed
```

## 주요 명령어

| 명령어 | 설명 |
|---|---|
| `uv run pytest -q` | 전체 테스트 실행 |
| `uv run ruff check .` | lint 검사 |
| `uv run mypy app` | strict type check |
| `uv run uvicorn app.main:app --reload --port 8010` | 로컬 API 서버 실행 |

## API 개요

### `GET /session`
현재 miniapp 세션 상태를 반환합니다.

응답:

```json
{"status":"active"}
```

가능한 상태:
- `active`
- `expired`
- `unauthenticated`

### `GET /feed`
miniapp 홈에서 렌더링할 수 있는 render-ready 신호 목록을 반환합니다.

### `GET /signals/{id}`
miniapp 상세 화면에서 렌더링할 수 있는 render-ready 신호 하나를 반환합니다.

### `POST /internal/rebuild-feed`
fixture 또는 source 입력을 기준으로 feed를 재생성합니다.

규칙:
- `local`, `demo`, `development`, `test` 환경에서는 내부 토큰 없이 허용됩니다.
- `production`에서는 `x-pipeline-internal-token`이 필요합니다.

## 환경 변수

| 환경 변수 | 기본값 | 설명 |
|---|---|---|
| `PIPELINE_ENV` | `production` | 실행 환경. `local`, `demo`, `development`, `test`에서는 내부 rebuild를 자동 허용 |
| `PIPELINE_BRAIN_BASE_URL` | 비어 있음 | Brain base URL. 비어 있으면 fixture의 stubbed Brain output 사용 |
| `PIPELINE_INTERNAL_REBUILD_TOKEN` | 비어 있음 | production에서 `/internal/rebuild-feed` 호출 시 필요한 내부 토큰 |
| `PIPELINE_FEED_STORE_PATH` | `~/.moneysignal/pipeline/feed-store.json` | feed store 파일 경로 |
| `PIPELINE_SESSION_STATUS` | `active` | miniapp session 상태 override |
| `PIPELINE_CORS_ALLOW_ORIGINS` | 비어 있음 | miniapp이 호출할 수 있도록 허용할 origin 목록(`,` 구분) |

## review / staging 기준

review/staging 환경에서는 아래를 고정하는 것을 권장합니다.

- `PIPELINE_ENV=demo`
- `PIPELINE_BRAIN_BASE_URL`는 review 대상 Brain으로 명시하거나 비워 두고 fixture stub 사용
- `PIPELINE_SESSION_STATUS=active`를 기본값으로 두고, 만료 시나리오 리허설 시에만 `expired` 또는 `unauthenticated`로 변경
- review walkthrough 직전 `POST /internal/rebuild-feed`로 feed를 재생성

## 검증 기준

다음 항목을 통과해야 miniapp 연결 대상으로 사용할 수 있습니다.

- `/session`이 expected status를 반환한다.
- `/feed`가 render-ready 목록을 반환한다.
- `/signals/{id}`가 render-ready detail을 반환한다.
- Brain runtime failure가 fake success로 섞이지 않는다.
- review/demo에서 fixture replay 결과가 재현 가능하다.

## 관련 문서

- 제품 MVP: `../../docs/product/apps-in-toss-mvp.md`
- Pipeline 스펙: `../../docs/superpowers/specs/moneysignal-data-pipeline-spec.md`
- 리뷰 제출 런북: `../../docs/runbooks/review-submission-runbook.md`
- 출시 런북: `../../docs/runbooks/production-launch-runbook.md`
