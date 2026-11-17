# Handoff

Current state of the project for the next agent. Overwrite (don't append) when you finish a task.

## State
`Item` model, `canonical_url()`, and the HN collector (`pulse.collectors.hn.fetch_top`) exist; no storage or digest yet.

## In flight
Nothing.

## Next up
See open issues. Planned order: arXiv collector → RSS collector → SQLite storage → daily digest.

## Gotchas
- Python ≥3.12, managed with `uv`.
- Collectors take an optional `httpx.Client`; tests use `httpx.MockTransport` (no network).
