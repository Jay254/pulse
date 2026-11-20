# 0002: Database and digests persist on a `data` branch

**Context:** the digest workflow runs on a fresh runner each day. The store must remember which
items were already sent, or every digest would repeat items.

**Decision:** the workflow keeps `pulse.db` and the `digests/` folder on an orphan `data`
branch. Each run restores that branch into `state/`, runs `pulse digest`, then force-pushes the
updated files to `data` as a single commit, so the branch never holds more than one copy of the
database. `main` holds only code and is never written by the workflow.

**Options considered:**
- Actions cache: free and simple, but entries are evicted after 7 days without access and can
  be purged under storage pressure. A lost cache silently resends old items.
- Artifact: expires (90 days by default) and needs an API call to download the previous run's
  artifact. Fragile for a store that must live indefinitely.
- `data` branch (chosen): durable, visible and downloadable from GitHub, needs only
  `contents: write`, and works with the repo's existing token. Costs: the file is binary, so
  there is no useful diff, and force-pushing one commit keeps the repo small but drops history.

**Reason:** durability matters more than history. If the database is ever lost, the worst case
is one digest of repeated items. Runs are serialized by a `concurrency` group so two runs
cannot overwrite each other.
Writing digests to `main` was rejected: branch protection requires a PR and passing CI for every
change, and daily bot commits would fill the history. Read digests on the `data` branch.
