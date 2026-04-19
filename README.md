# MoneySignal

MoneySignal은 초보 투자자에게 **정기 브리핑 + 강한 신호 즉시 알림**을 제공하는 투자 신호 서비스 저장소입니다. 현재 이 저장소는 제품 스펙, ADR, 그리고 `services/brain` 백엔드 서비스를 중심으로 구성되어 있습니다.

## 저장소 구성

```text
MoneySignal/
├─ docs/
│  └─ superpowers/specs/
│     └─ 2026-04-16-moneysignal-agent-brain-spec.md
├─ services/
│  └─ brain/
│     ├─ app/
│     ├─ docs/adrs/
│     ├─ tests/
│     ├─ pyproject.toml
│     └─ README.md
└─ README.md
```

## 현재 기준선 상태

- `services/brain`는 FastAPI 기반 Agent Brain 서비스입니다.
- v1 실행 전략은 **deterministic stubbed runtime**으로 고정되어 있습니다.
- 신호 판단 결과는 `reject`, `briefing`, `instant_push` 세 가지로 나뉩니다.
- public API는 success envelope와 structured error envelope를 분리합니다.

## 주요 문서

- 제품/서비스 스펙: `docs/superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- v1 기본값 ADR: `services/brain/docs/adrs/ADR-001-v1-defaults.md`
- signal evaluate API ADR: `services/brain/docs/adrs/ADR-002-evaluate-signal-api-surface.md`
- Brain 서비스 실행/검증 안내: `services/brain/README.md`

## 빠른 시작

현재 저장소에서 바로 실행 가능한 서비스는 `services/brain`입니다.

```bash
cd services/brain
uv sync
uv run uvicorn app.main:app --reload
```

기본 확인:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy app
```

## 서비스 방향

MoneySignal은 아래 방향을 기준으로 발전합니다.

- 초보 투자자도 이해할 수 있는 의견형/가이드형 톤
- 공통 추천으로 cold start를 줄이고, 개인화된 비서 느낌을 강화하는 혼합형 경험
- 토스 내 배포를 우선 고려한 제품 구조

## 구현 원칙

- 비즈니스 결과(`reject`)와 시스템 실패를 절대 섞지 않습니다.
- v1 테스트와 개발은 live provider 호출 없이 deterministic fixture/stub 기반으로 진행합니다.
- 공개 contract 변경은 코드 수정만이 아니라 ADR과 README에도 반영합니다.

## 다음으로 보면 좋은 곳

- Brain 오케스트레이션 흐름: `services/brain/app/orchestrators/evaluate_signal.py`
- HTTP entrypoint: `services/brain/app/main.py`
- 병렬 specialist runtime: `services/brain/app/runtime/parallel.py`
