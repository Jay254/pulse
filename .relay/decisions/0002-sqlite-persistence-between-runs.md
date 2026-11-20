# 0002: SQLite database persists on a `data` branch

**Context:** the digest workflow runs on a fresh runner each day. The store must remember which
items were already sent, or every digest would repeat items.

**Decision:** the workflow keeps `pulse.db` on an orphan `data` branch. Each run fetches it,
runs `pulse digest`, commits the new digest to `main`, then force-pushes the database to `data`
as a single commit, so the branch never holds more than one copy.

**Options considered:**
- Actions cache: free and simple, but entries are evicted after 7 days without access and can
  be purged under storage pressure. A lost cache silently resends old items.
- Artifact: expires (90 days by default) and needs an API call to download the previous run's
  artifact. Fragile for a store that must live indefinitely.
- `data` branch (chosen): durable, visible and downloadable from GitHub, needs only
  `contents: write`, and works with the repo's existing token. Costs: the file is binary, so
  there is no useful diff, and force-pushing one commit keeps the repo small but drops history.

**Reason:** durability matters more than history. If the database is ever lost, the worst case
is one digest of repeated items. Keep `data` out of `main` so the working tree stays clean.
Runs are serialized by a `concurrency` group so two runs cannot overwrite each other.
Branch protection on `main` must allow `github-actions[bot]` to push the digest commit.
