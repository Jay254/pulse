# #2 arXiv collector (cs.LG, cs.AI, cs.CL)

Agent: cursor
Date: 2026-11-17

- Did: added `pulse.collectors.arxiv.fetch_recent`, which queries the export Atom API once,
  sorted by submission date, and maps papers to `Item`s.
- Files: `src/pulse/collectors/arxiv.py`, `tests/collectors/test_arxiv.py`,
  `tests/fixtures/arxiv_atom.xml`.
- Tests: fixture-based tests for field mapping, multi-author `"et al."`, title whitespace, and
  the request's query and User-Agent; all pass offline.
- Why: stdlib `ElementTree` avoids a feed-parser dependency; an injectable `httpx.Client`
  matches the HN collector so tests never hit the network.
- Next: RSS collector (`feeds.toml`), then SQLite storage.
