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
