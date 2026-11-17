# Progress log

Append-only. Newest entry at the bottom. One entry per finished task.

```
## YYYY-MM-DD — #<issue> <title>  (agent: claude | cursor | codex | human)
- Did: <what changed, 1–3 bullets>
- Files: <paths touched>
- Tests: <added/changed, pass/fail>
- Why: <key reasoning or tradeoff>
- Next: <follow-ups or open questions>
```

## 2026-11-17 — repo bootstrap  (agent: human)
- Did: created skeleton (package, `Item` model + `canonical_url`, CI, Claude workflow, agent notes).
- Files: everything.
- Tests: `tests/test_models.py` passes.
- Why: give agents a working, tested base and a shared place to leave notes.
- Next: issues #1–#5 (collectors → storage → digest).

## 2026-11-17 — #1 Hacker News collector  (agent: claude)
- Did: added `pulse.collectors.hn.fetch_top(limit, client)` mapping HN stories to `Item`; added `httpx`.
- Files: `src/pulse/collectors/`, `tests/collectors/test_hn.py`, `pyproject.toml`, `uv.lock`
- Tests: 4 new tests using `httpx.MockTransport` (normal, no url, dead/deleted/non-story, limit); all pass.
- Why: injectable `client` keeps tests offline; items are fetched sequentially for simplicity.
- Next: arXiv collector can copy this shape; consider concurrent item fetches if slow.
