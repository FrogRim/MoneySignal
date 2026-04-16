# ADR-001: Lock v1 defaults for MoneySignal Agent Brain

- Status: Accepted
- Date: 2026-04-16
- Deciders: Agent Brain foundation slice
- Related spec: `docs/superpowers/specs/2026-04-16-moneysignal-agent-brain-spec.md`
- Related plan: current approved implementation plan for this repository

## Context
The approved Agent Brain spec leaves five open questions that would otherwise leak ambiguity into contracts, fixtures, and later implementation phases:

1. provider strategy
2. briefing threshold
3. instant-push threshold
4. `evidence_refs` normalization shape
5. `broker_deeplink_hint` shape
6. fixture scope

Phase 0 exists to lock these defaults before service bootstrap, contracts, gate logic, or API work begins.

## Decision

### 1. Provider strategy
v1 uses a provider-agnostic runtime boundary with deterministic stubbed adapters as the only default implementation in the repository.

Locked defaults:
- `provider_strategy = "stubbed"`
- `default_provider = "stub"`
- specialist model key default: `stub-specialist-v1`
- editor model key default: `stub-editor-v1`

Implications:
- Phase 0-6 implementation remains deterministic and does not make live network calls.
- agent/orchestrator code may read provider/model keys from config, but v1 execution uses stubbed outputs and fixtures only.
- live provider selection is deferred to a later ADR after contracts, tests, and golden fixtures are stable.

This follows the approved plan guidance to keep provider adapters stubbed and deterministic in the first implementation pass.

### 2. Initial gate thresholds
v1 threshold defaults are:
- briefing threshold: `0.55`
- instant-push threshold: `0.80`

Decision mapping:
- score `< briefing_threshold` -> `reject`
- score `>= briefing_threshold` and `< instant_push_threshold` -> `briefing`
- score `>= instant_push_threshold` -> `instant_push`

Rules:
- thresholds live in `app/config.py`
- business logic must read thresholds from config rather than hardcoding numeric values
- v1 calibration is intentionally conservative for `instant_push`

### 3. `evidence_refs` normalization shape
v1 locks `evidence_refs` to the minimal public shape already implied by the spec sample:

```json
{ "type": "market_event | news | flow", "ref": "string" }
```

Normalization rules:
- `type` is one of `market_event`, `news`, or `flow`
- `ref` is the upstream stable identifier for that evidence item
- no extra nested payload, URL, score, or provider metadata is included in the public contract for v1
- items preserve source order from validated inputs/fixtures
- items should be unique by `(type, ref)` within one signal card
- the service must never fabricate a reference when a backing source identifier is unavailable

v1 consequence for upstream and fixtures:
- candidate-event fixtures and stub agent outputs must carry stable source IDs for every evidence item that will appear in `evidence_refs`
- if a source cannot provide a stable ID, it must not be emitted as evidence in v1

### 4. `broker_deeplink_hint` shape
v1 locks `broker_deeplink_hint` to the minimal hint object below:

```json
{ "broker": "toss_securities", "symbol": "string" }
```

Rules:
- `broker` is fixed to `toss_securities` in v1
- `symbol` is the rendered asset symbol from the evaluated candidate
- no executable URL, account identifier, order payload, or action verb is included
- this remains a navigation hint only and must not cross into brokerage execution behavior

This aligns with the spec boundary that forbids extending deeplinks into executable brokerage actions without prior review.

### 5. Fixture scope
v1 fixtures start with KR assets only.

Locked default:
- `fixture_scope = "KR_ONLY"`

Implications:
- deterministic test fixtures, sample payloads, and golden outputs focus on KR symbols and KR market conventions first
- US asset fixtures are deferred until after contract stabilization and the first end-to-end green path is complete
- public contracts must still stay market-extensible, but Phase 0 defaults and initial fixtures are KR only

## Rationale
- The spec explicitly forbids CI dependence on live external model calls, so stubbed deterministic adapters are the safest v1 default.
- The response examples already show minimal `evidence_refs` and `broker_deeplink_hint` shapes; locking the minimal form avoids speculative public fields.
- Thresholds must be config-driven because later calibration is expected.
- KR-only fixtures reduce early scope while preserving the public contract shape needed for later expansion.

## Consequences

### Positive
- Later phases can implement contracts and gate logic against a fixed default policy.
- Runtime and API work can depend on stable public shapes for `evidence_refs` and `broker_deeplink_hint`.
- Tests remain deterministic and do not require provider credentials or network access.

### Trade-offs
- Live provider wiring remains intentionally unresolved for v1 execution.
- Threshold values are initial defaults, not product-calibrated truth.
- US coverage is postponed until after the first stable contract and API slice.

## Implementation notes
- `services/brain/app/config.py` is the only source for threshold, concurrency, timeout, and default provider/model keys.
- Follow-up phases must not add public fields to `evidence_refs` or `broker_deeplink_hint` without a new ADR or explicit spec change.
- Follow-up phases must not bypass the stubbed default with a live provider in tests.
