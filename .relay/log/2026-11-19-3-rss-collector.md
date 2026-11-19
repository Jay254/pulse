# #3 RSS/Atom collector driven by feeds.toml

Agent: claude
Date: 2026-11-19

- Did: added `pulse.collectors.rss.fetch_feeds` and `load_feeds`, which read `feeds.toml` and
  map RSS 2.0 and Atom entries to `Item`s with `source="rss"`.
- Did: a feed that fails to download or parse is logged as a warning and skipped.
- Files: `feeds.toml`, `src/pulse/collectors/rss.py`, `tests/collectors/test_rss.py`,
  `tests/fixtures/rss2.xml`, `tests/fixtures/blog_atom.xml`.
- Tests: fixture-based RSS 2.0, Atom, mixed failing-feed, and TOML loading cases; no network.
- Why: stdlib `ElementTree` and `tomllib` cover both formats, so no new dependency. Entries
  with no link are skipped. Item text is the raw content or summary, with HTML left in place.
- Next: strip HTML from `text` before ranking; wire collectors into storage.
