# #5 Daily digest workflow

Agent: claude
Date: 2026-11-20

- Did: added `.github/workflows/digest.yml` (04:00 UTC plus `workflow_dispatch`). It restores
  the `data` branch, runs `pulse digest`, and force-pushes the database and digests back to
  `data` as one commit.
- Files: `.github/workflows/digest.yml`, `.relay/decisions/0002-sqlite-persistence-between-runs.md`,
  `.relay/handoff.md`, `.gitignore`
- Tests: no code change. A local `pulse digest` run wrote a 10 item digest from all sources.
- Why: committing digests to `main` fails under branch protection and fills the history, so
  digests move to `data` with the database.
- Next: strip HTML from item text; give each source slots in the digest and skip old items.
