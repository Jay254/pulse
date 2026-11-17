# #1 Hacker News collector

Agent: claude
Date: 2026-11-17

- Did: added `pulse.collectors.hn.fetch_top(limit, client)`, which maps HN stories to `Item`;
  added `httpx`.
- Files: `src/pulse/collectors/`, `tests/collectors/test_hn.py`, `pyproject.toml`, `uv.lock`.
- Tests: 4 new tests using `httpx.MockTransport` (normal story, no url, dead/deleted/non-story,
  limit); all pass.
- Why: an injectable `client` keeps tests offline; items are fetched sequentially for simplicity.
- Next: the arXiv collector can copy this shape; consider concurrent item fetches if slow.
