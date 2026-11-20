# #17 Give each source slots in the digest and skip old items

Agent: claude
Date: 2026-11-20

- Did: added `select()` in `digest.py`. It drops items older than `MAX_AGE` (3 days, by `published_at` then `first_seen_at`), gives each source its `SLOTS` (4 hn, 3 arxiv, 3 rss), and fills empty slots from the best remaining items. `run_digest` uses it and takes an optional `now`.
- Files: `src/pulse/digest.py`, `tests/test_digest.py`
- Tests: added for the cutoff, slot allocation, filling, shared items, and the limit; existing digest tests now pass `now`.
- Why: `rank` stays the per-source ordering so a learned ranker can replace it. An item counts once, under `Item.source` (its first source).
- Next: when `limit` is below the slot total, slots are served in `SLOTS` order (hn first).
