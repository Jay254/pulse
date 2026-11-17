# Handoff

Conventions and gotchas every agent must know before working here. Keep this short and true:
add a line when you introduce a convention, remove lines that no longer hold. Current progress
lives in the open issues and in `.relay/log/`.

## Conventions
- Python 3.13 (see `.python-version`), managed with `uv`.
- Collectors live in `src/pulse/collectors/<source>.py`, expose one public `fetch_*` function,
  return `list[Item]`, and accept an optional `httpx.Client`.
- Tests use `httpx.MockTransport` and saved fixtures in `tests/fixtures/`; no network access.

## Gotchas
- arXiv titles are whitespace-collapsed; a paper with more than one author is stored as
  `"First et al."`. The item URL is the abstract page, not the PDF.
