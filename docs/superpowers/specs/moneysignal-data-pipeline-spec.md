# Spec: MoneySignal Data Pipeline (B)

## Assumptions
1. This spec covers **B. Data Pipeline** only.
2. Pipeline owns candidate generation, Brain evaluation orchestration, and the product-facing read model.
3. Pipeline sends normalized candidate events to `services/brain` using the existing `CandidateEventRequest` contract.
4. The Toss Miniapp does **not** call Brain evaluate directly; it reads Pipeline feed/detail APIs.
5. v1 prioritizes deterministic fixture replay and reviewability over large-scale market coverage.

## Objective
Build a service that turns market/news/flow fixtures or normalized source inputs into a read-friendly product surface for the Toss Miniapp.

The Data Pipeline exists to:
- generate or ingest candidate events,
- normalize them into the Brain input contract,
- call the Brain evaluation API,
- persist accepted signal results into a read model,
- and expose feed/detail APIs that the miniapp can render directly.

## Primary responsibilities
- Candidate generation
- Candidate normalization
- Brain evaluate orchestration
- Result persistence / replay
- Feed/detail read API
- Deterministic demo/review fixture playback

## Out of scope
- Rich UI rendering
- Direct user/session UX concerns
- Replacing Brain contract with ad hoc shapes
- Large-scale distributed processing in v1
- Payment / billing / promotion features

## Proposed tech stack
- Python 3.12
- FastAPI
- Pydantic
- uv
- pytest
- httpx
- Ruff
- mypy

## Project structure
```text
services/pipeline/
├─ app/
│  ├─ main.py
│  ├─ contracts.py
│  ├─ services/
│  │  ├─ generate_candidates.py
│  │  ├─ evaluate_candidates.py
│  │  └─ feed_store.py
│  ├─ api/
│  │  ├─ feed.py
│  │  └─ signals.py
│  └─ fixtures/
├─ tests/
└─ README.md
```

## Contract strategy

### Input to Brain
Pipeline must generate `CandidateEventRequest`-compatible payloads.

Rules:
- candidate payloads are normalized before Brain call
- source-specific raw shapes do not leak into Brain
- fixture replay must produce the same candidate payloads every run

### Output from Brain
Pipeline consumes `EvaluateSignalSuccessResponse` and `ErrorEnvelope`.

Rules:
- `reject` is stored or filtered as a normal business outcome, not an exception
- `briefing` and `instant_push` are eligible for feed/detail read models
- Brain runtime failures stay as structured operational failures

## Product-facing read APIs

### `GET /feed`
Returns a list of render-ready briefing/interest items for the miniapp home.

### `GET /signals/{id}`
Returns one render-ready signal detail.

### Optional `GET /briefings`
If briefing history is separated from current feed.

Rules:
- read APIs are optimized for miniapp rendering
- the miniapp should not need to reshape Brain raw output in complex ways
- data should remain traceable back to Brain signal/evidence IDs

## Data model principles
- preserve signal identity (`signal_card.id`)
- preserve asset identity
- preserve summary / reasons / risks / watch_action
- preserve confidence and agent_votes
- preserve evidence references for traceability
- add only read-model metadata that Brain should not own
  - published_at
  - feed section
  - sort key
  - read model status

## v1 execution model
- start with deterministic fixtures and replayable candidate generation
- allow simple synchronous Brain evaluation first
- prefer one service owning generation + evaluation + read APIs before introducing queues
- optimize only after end-to-end correctness is proven

## Testing strategy

### Unit tests
Cover:
- candidate normalization
- Brain request payload construction
- read model transformation
- feed sorting / filtering rules

### Integration tests
Cover:
- Brain evaluate call with stubbed or local backend
- fixture replay end-to-end
- `/feed` and `/signals/{id}` responses
- reject vs accepted signal persistence behavior

### Verification commands
```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy app
uv run uvicorn app.main:app --reload
```

## Boundaries

### Always do
- normalize inputs before Brain call
- preserve Brain identifiers and evidence references
- keep demo/review scenarios replayable
- document product-facing read contracts clearly

### Ask first
- changing Brain public contracts
- adding persistent infra that materially changes rollout complexity
- adding live market coverage beyond agreed v1 scope

### Never do
- bypass Brain and fabricate signal cards in Pipeline
- hide Brain execution failures as fake business successes
- let raw source payloads leak directly to miniapp consumers

## Success criteria
1. Pipeline can generate Brain-compatible candidate events.
2. Pipeline can call Brain and persist accepted signal results.
3. Miniapp can render `/feed` and `/signals/{id}` without hand-made mock data.
4. Demo and review environments can replay deterministic scenarios.
5. Contract drift between Pipeline and Brain is caught by tests.
