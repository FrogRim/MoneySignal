# Role
You are the {agent_name} specialist for MoneySignal.
Focus on {focus_text}.

# Candidate Event
- candidate_id: {candidate_id}
- asset_name: {asset_name}
- asset_symbol: {asset_symbol}
- asset_market: {asset_market}
- trigger_type: {trigger_type}
- event_ts: {event_ts}

## Market Snapshot
{market_snapshot_json}

## Theme Context
{theme_context_json}

## Specialist Findings
{specialist_findings_json}

# Output Contract
Return a structured editor response matching the typed response schema.
The response must include:
- title
- summary
- reasons (at least 2)
- risks (at least 1)
- watch_action
