# Spec: MoneySignal Toss Miniapp (C)

## Assumptions
1. This spec covers **C. Toss Miniapp** only.
2. The final product surface is an **Apps in Toss WebView miniapp**.
3. The miniapp consumes product-facing read APIs from `services/pipeline`, not Brain evaluate directly.
4. The miniapp must satisfy Apps in Toss non-game constraints from day one.
5. v1 prioritizes trust, clarity, and review-safe UX over feature breadth.

## Objective
Build a WebView-first Toss miniapp that lets beginner investors understand current signals quickly through a small set of stable, review-friendly screens.

The miniapp exists to:
- show a list of current briefing-worthy signals,
- let users open a signal detail view,
- communicate reasons, risks, and what to watch next,
- handle empty/error/session-expired states gracefully,
- and pass Apps in Toss review without dark-pattern or policy violations.

## Primary screens
- Home / signal feed
- Signal detail
- Empty state
- Error state with retry
- Help / service explanation
- Session-expired / re-entry guidance

## UX principles
- opinionated but non-directive tone
- simple first-load understanding within 1 minute
- no immediate popup or bottom sheet on entry
- always-visible escape path (back or close)
- explicit CTA labels
- light mode only
- TDS-first UI

## Product rules

### Home feed
The home screen should show:
- current briefing items
- summary-level cards
- a clear path to signal details
- no misleading urgency language

### Signal detail
A signal detail should show:
- title and asset identity
- summary
- at least two reasons
- at least one risk
- watch action
- confidence
- agent votes
- evidence references or source-backed context

### Empty state
When no feed items exist:
- explain that there is no notable signal right now
- reinforce what the app will surface later
- do not frame emptiness as failure

### Error state
When API calls fail:
- show a plain-language explanation
- offer retry
- avoid leaking internal backend errors

### Session-expired state
When session/auth becomes invalid:
- explain re-entry in simple language
- route users back through the agreed Toss login path

## Apps in Toss constraints
- Toss login only
- light mode only
- TDS-based UI preferred
- no entry popup/bottom sheet
- no back-button hijacking
- no dead-end screen without close/exit path
- no ambiguous CTA text
- bundle size must stay within Apps in Toss limits

## Proposed app structure
```text
apps/toss-miniapp/
├─ src/
│  ├─ app/
│  ├─ pages/
│  │  ├─ FeedPage.tsx
│  │  ├─ SignalDetailPage.tsx
│  │  ├─ HelpPage.tsx
│  │  └─ SessionExpiredPage.tsx
│  ├─ components/
│  ├─ api/
│  ├─ mocks/
│  └─ styles/
├─ public/
├─ tests/
└─ README.md
```

## API integration strategy
The miniapp reads from Pipeline read APIs.

Expected endpoints:
- `GET /feed`
- `GET /signals/{id}`
- optional `GET /briefings`

Rules:
- the miniapp should not assemble product meaning from raw Brain evaluate responses
- API data should already be close to render-ready
- error handling should map structured failures into human-friendly UI states

## Copy rules
- keep the opinionated/guiding tone
- do not use direct buy/sell commands
- avoid vague buttons like `확인`, `계속` when a more specific label is available
- explain value in active, simple Korean

## Testing strategy

### Unit/component tests
Cover:
- signal card rendering
- empty state rendering
- error state rendering
- CTA labeling
- navigation-safe header rendering

### Integration tests
Cover:
- feed fetch and render
- detail fetch and render
- retry path from error state
- session-expired redirect state

### Manual verification
Cover:
- first entry has no popup/bottom sheet
- back and close behavior is always available
- light mode only
- layout works inside mobile WebView-like viewport

## Verification commands
```bash
npm install
npm run test
npm run build
npm run lint
```

## Boundaries

### Always do
- render reasons / risks / watch-next guidance clearly
- keep navigation escape paths obvious
- use explicit CTA copy
- design for Apps in Toss review first

### Ask first
- adding payment or monetization flows
- adding push-dependent product behavior
- adding major personalization surfaces
- changing the product tone away from the agreed opinionated/guiding style

### Never do
- dark mode support in v1
- immediate popup/bottom sheet on entry
- third-party login
- direct trade instruction language
- UI dead ends without exit path

## Success criteria
1. The miniapp renders the feed and signal detail from live read APIs.
2. A reviewer can understand the app purpose quickly from the first screen.
3. Empty/error/session states are defined and product-safe.
4. The miniapp respects Apps in Toss constraints from the initial implementation.
5. The UI remains lightweight and WebView-friendly.
