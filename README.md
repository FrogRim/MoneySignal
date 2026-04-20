# MoneySignal

MoneySignal은 초보 투자자에게 **정기 브리핑 + 강한 신호 즉시 알림**을 제공하는 투자 신호 서비스 저장소입니다. 최종 제품 surface는 **Apps in Toss miniapp**이며, 현재 저장소는 그 목표를 향해 **A. Agent Brain**, **B. Data Pipeline**, **C. Toss Miniapp**의 세 축으로 확장되는 중입니다.

## 현재 상태 요약

| 축 | 역할 | 현재 상태 |
|---|---|---|
| A. Agent Brain | 후보 이벤트를 평가해 `reject` / `briefing` / `instant_push`를 반환 | 구현됨 |
| B. Data Pipeline | 후보 이벤트 fixture replay, Brain 호출, session/feed/detail read API 제공 | 구현됨 |
| C. Toss Miniapp | Apps in Toss WebView에서 신호 목록/상세/도움말/세션 상태를 제공 | 구현됨 |

현재 저장소는 Brain, Pipeline, Miniapp의 기본 수직 슬라이스를 모두 갖췄습니다. 남은 핵심 작업은 Apps in Toss 제출용 환경 고정, reviewer walkthrough 확정, 실제 Toss 로그인/호스트 브리지 연결, 운영 증거 수집입니다.

## 저장소 구성

```text
MoneySignal/
├─ apps/
│  └─ toss-miniapp/
├─ docs/
│  ├─ adrs/
│  ├─ product/
│  ├─ runbooks/
│  └─ superpowers/specs/
├─ infra/
│  └─ caddy/
├─ services/
│  ├─ brain/
│  └─ pipeline/
├─ docker-compose.yml
├─ README.md
└─ .gitignore
```

주요 디렉터리:

```text
services/brain/         # 평가 엔진 API
services/pipeline/      # fixture replay + Brain evaluate + read API
apps/toss-miniapp/      # Apps in Toss WebView miniapp
```

## 빠른 시작

현재 바로 실행 가능한 영역은 `services/brain`입니다.

```bash
cd services/brain
uv sync
uv run uvicorn app.main:app --reload
```

기본 검증:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy app
```

## 핵심 문서

### 제품 / 아키텍처
- Apps in Toss MVP 개요: `docs/product/apps-in-toss-mvp.md`
- 시스템 아키텍처 ADR: `docs/adrs/ADR-001-apps-in-toss-system-architecture.md`
- 앱인토스 검수 체크리스트: `docs/product/review-checklist.md`

### 스펙
- A. Agent Brain 스펙: `docs/superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- B. Data Pipeline 스펙: `docs/superpowers/specs/moneysignal-data-pipeline-spec.md`
- C. Toss Miniapp 스펙: `docs/superpowers/specs/moneysignal-miniapp-spec.md`

### 운영 / 검수
- 리뷰 제출 런북: `docs/runbooks/review-submission-runbook.md`
- review/staging 환경 매트릭스: `docs/runbooks/review-staging-env-matrix.md`
- 출시 런북: `docs/runbooks/production-launch-runbook.md`
- DigitalOcean + Compose 배포 런북: `docs/runbooks/digitalocean-compose-deploy.md`
- Brain 서비스 실행/검증 안내: `services/brain/README.md`
- Pipeline 서비스 실행/검증 안내: `services/pipeline/README.md`
- Toss Miniapp 실행/검증 안내: `apps/toss-miniapp/README.md`

## 제품 방향

MoneySignal은 아래 방향을 기준으로 발전합니다.

- 초보 투자자도 이해할 수 있는 의견형/가이드형 톤
- 공통 추천으로 cold start를 줄이고, 개인화된 비서 느낌을 강화하는 혼합형 경험
- **WebView-first Apps in Toss miniapp**를 우선 목표로 하는 제품 구조
- 강한 신호는 즉시 알림으로, 약한 신호는 브리핑으로 전달하는 하이브리드 모델

## 앱인토스 구현 원칙

- Toss 로그인만 사용합니다.
- 라이트 모드만 지원합니다.
- TDS 기반 UI를 우선합니다.
- 진입 즉시 팝업/바텀시트를 띄우지 않습니다.
- 뒤로가기/닫기 경로가 항상 명확해야 합니다.
- CTA는 모호하지 않게 작성합니다.
- 결제(Toss Pay / IAP)는 v1 검수 통과 이후 범위로 미룹니다.

## 구현 원칙

- 비즈니스 결과(`reject`)와 시스템 실패를 절대 섞지 않습니다.
- v1 개발/검증은 live provider 없이 deterministic fixture/stub 기반으로 진행합니다.
- 공개 contract 변경은 코드 수정만이 아니라 README/스펙/ADR에도 반영합니다.
- Brain은 평가 엔진 역할을 유지하고, 제품용 feed/detail surface는 Pipeline이 맡습니다.

## 다음으로 보면 좋은 곳

- Brain HTTP entrypoint: `services/brain/app/main.py`
- Brain 오케스트레이션 흐름: `services/brain/app/orchestrators/evaluate_signal.py`
- Brain 병렬 specialist runtime: `services/brain/app/runtime/parallel.py`
- Apps in Toss MVP 범위: `docs/product/apps-in-toss-mvp.md`
- Pipeline 역할 정의: `docs/superpowers/specs/moneysignal-data-pipeline-spec.md`
- Miniapp 역할 정의: `docs/superpowers/specs/moneysignal-miniapp-spec.md`
