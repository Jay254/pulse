# #5 Daily digest command and scheduled workflow

Agent: claude
Date: 2026-11-20

- Did: added the `pulse digest` command, `rank()` and markdown rendering in `src/pulse/digest.py`. The workflow `digest.yml` (04:00 UTC plus `workflow_dispatch`) is written but not committed by this agent.
- Files: `src/pulse/digest.py`, `src/pulse/cli.py`, `src/pulse/models.py`, `src/pulse/store.py`, `pyproject.toml`, `tests/test_digest.py`, `.relay/decisions/0002-sqlite-persistence-between-runs.md`
- Tests: added `tests/test_digest.py` with mocked collectors. Lint, format check, and tests pass locally. The workflow has not been run; trigger it with `workflow_dispatch` after merge.
- Why: `rank()` needs all sources per item, so `Item` gained a `sources` tuple (excluded from equality) that `Store.unsent` fills. Each extra source counts as 24 hours newer. A failing collector is logged and skipped. The database persists on a `data` branch (decision 0002).
- Next: the GitHub App cannot push to `.github/workflows/`, so `digest.yml` must be added by a human (content is in the issue comment). Then run `workflow_dispatch` to confirm. GitHub and X collectors are not wired in yet.
