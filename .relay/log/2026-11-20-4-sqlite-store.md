# #4 SQLite store with cross-source dedupe and sent tracking

Agent: claude
Date: 2026-11-20

- Did: added `Store` in `src/pulse/store.py` with `upsert`, `unsent`, `mark_sent`, and a `sources` lookup. Schema version is tracked with `PRAGMA user_version`.
- Files: `src/pulse/store.py`, `tests/test_store.py`, `.relay/log/2026-11-20-4-sqlite-store.md`
- Tests: added `tests/test_store.py` using `tmp_path` databases.
- Why: an existing item keeps its original fields and only gains new sources. `unsent` orders by `published_at`, falling back to `first_seen_at`. It returns `Item.source` as the first source that saw the item. Datetimes are stored as UTC ISO strings so string order matches time order. No `feedback` table yet; add it as schema version 2.
- Next: wire the store into the collectors and digest code once those exist.
