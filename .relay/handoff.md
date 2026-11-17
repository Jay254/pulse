# Handoff

Current state of the project for the next agent. Overwrite (don't append) when you finish a task.

## State
`Item` model, `canonical_url()`, the HN collector (`pulse.collectors.hn.fetch_top`), and the arXiv collector (`pulse.collectors.arxiv.fetch_recent`) exist; no storage or digest yet.

## In flight
Nothing.

## Next up
See open issues. Planned order: RSS collector → SQLite storage → daily digest.

## Gotchas
- Python ≥3.12, managed with `uv`.
- Collectors take an optional `httpx.Client`; tests use `httpx.MockTransport` (no network).
- arXiv titles are whitespace-collapsed; a paper with more than one author is stored as `"First et al."`. The abstract HTML link is the item URL, not the PDF.
