# Spec: MoneySignal Agent Brain (A)

## Assumptions
1. This spec covers **A. Agent Brain (FastAPI & Logic)** only, not the full MoneySignal MVP.
2. The Agent Brain consumes **normalized candidate events** from the Data Pipeline rather than collecting raw market/news feeds itself.
3. The primary output unit is a **Rich Signal Card** in JSON.
4. The product tone is **opinionated but non-directive**: explain what matters, why it matters, and what to watch next without issuing direct buy/sell commands.
5. The final product surface is an **Apps in Toss miniapp**, while this service itself is an independent backend service.

## Objective
Build a FastAPI-based decision engine that turns normalized market events into beginner-friendly, explainable investment signal cards.

The Agent Brain exists to:
- filter market noise through a hybrid gate,
- combine multiple specialist agent perspectives,
- produce a trustworthy opinionated signal in plain language,
- and hand off a stable JSON contract that the MoneySignal frontend can render immediately.

Primary user:
- beginner investors who find direct trading decisions intimidating,
- and want concise reasoning, confidence, risks, and next-watch actions instead of raw quant outputs.

## Tech Stack
- Python 3.12
- FastAPI
- Pydantic
- uv
- pytest
- pytest-asyncio
- httpx
- Ruff
- mypy

## Commands
```bash
# dependency sync
uv sync

# local dev server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# unit + integration tests
uv run pytest -q

# contract tests only
uv run pytest tests/contracts -q

# async parallel verification
uv run pytest tests/integration/test_parallel_agents.py -q

# error-path verification
uv run pytest tests/integration/test_error_paths.py -q

# lint
uv run ruff check .

# format
uv run ruff format .

# type check
uv run mypy app

# sample evaluation run
uv run python scripts/run_sample_evaluation.py
```

## Project Structure
```text
services/brain/
├─ app/
│  ├─ main.py                    # FastAPI entrypoint
│  ├─ config.py                  # env/config management
│  ├─ api/
│  │  └─ v1/
│  │     └─ signals.py           # public HTTP endpoints
│  ├─ contracts/
│  │  ├─ input.py                # candidate event request schemas
│  │  ├─ output.py               # Rich Signal card response schemas
│  │  └─ errors.py               # structured API error response schemas
│  ├─ gate/
│  │  └─ service.py              # dual-threshold gate logic
│  ├─ prompts/
│  │  ├─ registry.py             # prompt version registry and agent prompt metadata
│  │  ├─ builders.py             # normalized input -> prompt context assembly
│  │  └─ templates/
│  │     ├─ news.md
│  │     ├─ chart.md
│  │     ├─ flow.md
│  │     ├─ risk.md
│  │     └─ editor.md
│  ├─ agents/
│  │  ├─ news_agent.py
│  │  ├─ chart_agent.py
│  │  ├─ flow_agent.py
│  │  ├─ risk_agent.py
│  │  └─ editor_agent.py
│  ├─ orchestrators/
│  │  └─ evaluate_signal.py      # gate -> specialist fan-out -> editor -> final card
│  ├─ runtime/
│  │  └─ parallel.py             # bounded async fan-out, timeouts, cancellation helpers
│  ├─ scoring/
│  │  └─ confidence.py           # agreement/confidence calculations
│  ├─ errors/
│  │  ├─ codes.py                # domain error taxonomy
│  │  └─ handlers.py             # HTTP/domain error mapping
│  └─ policies/
│     └─ tone.py                 # opinion-style tone and forbidden phrases
├─ scripts/
│  └─ run_sample_evaluation.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  │  └─ golden/
│  └─ contracts/
└─ docs/
   └─ adrs/
```

## Architecture
The Agent Brain uses a **hybrid gate + multi-agent consensus** architecture.

1. A normalized candidate event is received from the Data Pipeline.
2. A dual-threshold gate decides whether the event should be rejected, included in briefing output, or escalated to instant-push quality.
3. If the gate passes, specialist agents (`news`, `chart`, `flow`, `risk`) run concurrently under bounded async execution with per-agent timeouts.
4. A prompt registry selects the versioned template, prompt builder, timeout budget, and expected response schema for each agent.
5. The orchestrator validates specialist outputs, aggregates votes/confidence, and enforces minimum specialist coverage before editor synthesis.
6. The editor agent converts the validated consensus into a beginner-friendly signal card.
7. The API returns either a success envelope (gate + signal card) or a structured error envelope.

## Prompt Management
Prompt handling is part of the product contract, not an implementation detail.

Rules:
1. Every specialist and editor prompt is stored as a **versioned asset** under `app/prompts/templates/`.
2. `app/prompts/registry.py` is the single source of truth for:
   - `agent_name`
   - `template_version`
   - `response_model`
   - `model_key`
   - `timeout_ms`
   - `max_context_items`
3. `app/prompts/builders.py` is responsible for converting normalized candidate-event data into prompt context. Agent classes must not assemble ad hoc prompt strings inline.
4. Prompt outputs must target typed structured responses. If the response cannot be validated into the expected schema, that is treated as an execution failure, not a soft success.
5. Prompt changes require test updates so prompt structure and required instructions remain reviewable over time.

## Async Execution Model
Specialist analysis is expected to be parallel by default.

Rules:
1. `news`, `chart`, `flow`, and `risk` agents execute concurrently via `asyncio.TaskGroup` or an equivalent helper in `app/runtime/parallel.py`.
2. Concurrency must be bounded and configurable to avoid unbounded provider fan-out.
3. Each specialist has its own timeout budget; the editor runs only after specialist collection completes.
4. Minimum coverage for v1 is:
   - at least **3 successful specialist outputs**,
   - including `risk`,
   - and at least one of `news`, `chart`, or `flow`.
5. If minimum coverage is not met, the endpoint returns `analysis_failed` instead of fabricating a weak card.
6. Parallelism must be proven by integration tests that show wall-clock execution time is lower than the sum of sequential stub delays.

## API Contract
### Endpoint
```http
POST /v1/signals/evaluate
```

### Request shape
```json
{
  "candidate_id": "cand_20260416_001",
  "asset": {
    "symbol": "005930",
    "name": "삼성전자",
    "market": "KR"
  },
  "trigger_type": "price_volume_breakout",
  "event_ts": "2026-04-16T09:12:00+09:00",
  "market_snapshot": {},
  "news_items": [],
  "flow_snapshot": {},
  "theme_context": [],
  "metadata": {}
}
```

### Success response shape
```json
{
  "decision": "reject | briefing | instant_push",
  "gate": {
    "score": 0.82,
    "reason": "high multi-agent agreement with strong event relevance"
  },
  "signal_card": {
    "id": "sig_20260416_001",
    "title": "삼성전자에 강한 관심 신호가 포착됐어요",
    "asset": {
      "symbol": "005930",
      "name": "삼성전자",
      "market": "KR"
    },
    "signal_strength": "strong",
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
      { "agent": "chart", "stance": "positive", "confidence": 0.78 },
      { "agent": "news", "stance": "positive", "confidence": 0.81 },
      { "agent": "flow", "stance": "neutral", "confidence": 0.55 },
      { "agent": "risk", "stance": "cautious", "confidence": 0.64 }
    ],
    "confidence": 0.76,
    "evidence_refs": [
      { "type": "market_event", "ref": "evt_123" },
      { "type": "news", "ref": "news_456" }
    ]
  }
}
```

### Error response shape
```json
{
  "error": {
    "code": "invalid_request | upstream_timeout | upstream_unavailable | analysis_failed | internal_error",
    "message": "human-readable summary",
    "retryable": true,
    "failed_agents": ["news", "flow"],
    "trace_id": "req_20260416_001"
  }
}
```

### Contract rules
- `decision` is always one of `reject`, `briefing`, or `instant_push` for successful evaluations.
- `signal_card` may be `null` only when `decision == "reject"`.
- Approved cards must include:
  - at least 2 reasons,
  - at least 1 risk,
  - `agent_votes`,
  - `confidence`,
  - `evidence_refs`,
  - `watch_action`,
  - `broker_deeplink_hint`.
- Execution failures are never disguised as market `reject` results.
- Validation, upstream, and internal failures use the structured error envelope instead of the success envelope.
- The success contract is designed so the frontend can render output without additional enrichment.

## Error Handling
Error handling must preserve safety, traceability, and trust.

Rules:
1. Invalid request payloads return **422 / `invalid_request`**.
2. Upstream timeout or provider timeout returns **503 / `upstream_timeout`**.
3. Upstream dependency unavailability returns **503 / `upstream_unavailable`**.
4. If specialist execution completes without meeting minimum coverage, or if the editor output cannot be validated, return **503 / `analysis_failed`**.
5. Unexpected internal failures return **500 / `internal_error`**.
6. Failed specialist names must be recorded and surfaced in the error envelope where relevant.
7. The service must not silently swallow agent failures, invent evidence, or convert runtime failures into fake cards.

## Code Style
Design priorities:
- contract clarity,
- traceability of judgment,
- separation of responsibilities,
- prompt version control,
- and explicit failure handling.

Rules:
1. Public request/response shapes are defined in `contracts/`, not ad hoc dicts.
2. API handlers stay thin; orchestration lives in orchestrators and services.
3. Tone policy is explicit in code, not left entirely to prompts.
4. Prompt templates live under `prompts/templates/` and are referenced through a registry, not embedded inline inside agent classes.
5. Each function should do one step of work.
6. Prefer explicit names like `gate_score`, `candidate_event`, `prompt_version`, `failed_agents`, and `signal_evaluation`.
7. Prefer structured outputs over string parsing wherever possible.

### Style example
```python
from enum import Enum
from pydantic import BaseModel


class SignalDecision(str, Enum):
    REJECT = "reject"
    BRIEFING = "briefing"
    INSTANT_PUSH = "instant_push"


class GateResult(BaseModel):
    decision: SignalDecision
    score: float
    reason: str


class EvaluateSignalService:
    def __init__(self, gate_service, analysis_orchestrator):
        self._gate_service = gate_service
        self._analysis_orchestrator = analysis_orchestrator

    async def evaluate(self, candidate_event) -> dict:
        gate_result = self._gate_service.evaluate(candidate_event)

        if gate_result.decision == SignalDecision.REJECT:
            return {
                "decision": gate_result.decision,
                "gate": gate_result.model_dump(),
                "signal_card": None,
            }

        signal_card = await self._analysis_orchestrator.build_signal_card(
            candidate_event=candidate_event,
            gate_result=gate_result,
        )

        return {
            "decision": gate_result.decision,
            "gate": gate_result.model_dump(),
            "signal_card": signal_card,
        }
```

Naming and formatting:
- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Prefer `async def` for IO or orchestration paths
- Do not inline provider prompts inside agent methods
- Do not parse unstructured free-form strings when a typed response model is available

## Testing Strategy
### Frameworks
- pytest
- pytest-asyncio
- httpx
- Ruff
- mypy

### Test levels
#### Unit tests
Location:
```text
tests/unit/
```

Cover:
- gate threshold logic,
- confidence scoring,
- tone policy filters,
- prompt registry and prompt builders,
- error-code classification and handler mapping,
- vote aggregation,
- signal strength mapping.

#### Integration tests
Location:
```text
tests/integration/
```

Cover:
- `POST /v1/signals/evaluate`,
- reject / briefing / instant_push paths,
- gate -> orchestrator -> response assembly flow,
- async parallel specialist execution,
- per-agent timeout handling,
- minimum-coverage failure handling,
- editor validation failure handling.

#### Contract tests
Location:
```text
tests/contracts/
```

Cover:
- request schema compatibility,
- success response schema stability,
- error envelope schema stability,
- `signal_card: null` behavior,
- required-field enforcement.

#### Golden tests
Location:
```text
tests/integration/golden/
```

Cover:
- representative signal card outputs,
- forbidden tone checks,
- mandatory risk presence,
- prevention of direct buy/sell language,
- prompt-sensitive wording regressions for the editor output.

### Test policy
- CI must not depend on live external LLM calls.
- Agent behavior is validated with deterministic fixtures, stubs, or recorded responses.
- Prompt registry/builders must have snapshot-style tests or equivalent assertions for required sections and placeholders.
- Async execution must have at least one timing-based verification test proving parallel fan-out.
- Error-path tests must cover timeout, unavailable upstream, invalid structured output, and minimum-coverage failure.
- Real-model evaluation belongs in `scripts/run_sample_evaluation.py`, not the default test suite.
- A PR is not ready unless these pass:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy app`

## Boundaries
### Always do
- Validate all public input and output with schemas.
- Version prompts in a registry and keep templates under source control.
- Record reject reasons in a structured way.
- Include at least one risk on approved cards.
- Preserve opinion-style wording instead of direct trading commands.
- Include `agent_votes`, `confidence`, and `evidence_refs` on approved cards.
- Surface failed agents and explicit error codes for execution failures.
- Run tests, lint, and type checks before considering work ready.

### Ask first
- Adding a new external model or LLM provider.
- Introducing a persistent database.
- Adding queueing or streaming infrastructure.
- Changing the B -> A input contract.
- Making a breaking change to the frontend-facing output schema.
- Changing minimum specialist coverage or concurrency limits in a way that affects product behavior.
- Extending deeplinks into executable brokerage actions.

### Never do
- Call order execution APIs.
- Generate direct investment instructions like “buy now” or “sell now”.
- Fabricate `evidence_refs` without source backing.
- Hide agent disagreement while overstating certainty.
- Delete failing tests just to make CI pass.
- Quietly absorb raw data collection responsibilities into A.
- Inline prompts in agent classes or let prompt versions drift without review.
- Convert execution failures into fake market rejects or partially fabricated cards.

## Success Criteria
1. Every approved event is returned as a schema-valid Rich Signal Card.
2. The gate distinguishes between briefing and instant-push using separate thresholds.
3. Each approved card includes at least two reasons and at least one risk.
4. Agent agreement and disagreement are visible via `agent_votes`.
5. Output tone remains opinionated and beginner-friendly without direct trade commands.
6. The frontend can consume the success response contract without downstream reshaping.
7. Each specialist/editor prompt is versioned in the registry and bound to a typed response schema.
8. Specialist analysis runs in bounded async parallel execution, and integration tests prove it is parallel rather than sequential.
9. Structured error responses distinguish validation, upstream timeout/unavailable, analysis failure, and unexpected internal failure.

## Open Questions
1. **Model strategy:** Which live LLM/provider stack will power the specialist agents and editor agent in v1 after the stubbed implementation phase?
2. **Threshold calibration:** What initial numeric gate thresholds define `briefing` vs `instant_push`?
3. **Evidence normalization:** What exact reference format will B provide for market events, news items, and flow evidence?
4. **Broker deeplink contract:** What exact deeplink schema should align with Toss Securities entry points?
5. **Coverage scope for fixtures:** Should v1 evaluation fixtures start with KR assets only, or include both KR and US assets from the beginning?

## Notes on Scope
This spec intentionally treats the Agent Brain as one subproject in a larger three-part system:
- A. Agent Brain (this document)
- B. Data Pipeline
- C. Frontend Skeleton / Trust UX

A is the decision engine. B supplies normalized candidate events. C renders and distributes the resulting signal cards.
