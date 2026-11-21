# #8 HN collector: fill the requested limit and skip stories that fail to load

Agent: cursor
Date: 2026-11-21

- Did: `fetch_top` walks the top-story list until it has `limit` live stories, or the list ends. An HTTP error or timeout on one story is logged with the story id and skipped. A failure loading `topstories.json` still raises.
- Files: `src/pulse/collectors/hn.py`, `tests/collectors/test_hn.py`
- Tests: added fill-past-dead, HTTP 500 skip, timeout skip, and topstories failure. Existing HN tests still pass. `uv run pytest`, `ruff check`, and `ruff format --check` pass.
- Why: slicing to `limit` before dropping dead, deleted, and non-story items returned a short list. One bad story response used to abort the whole collection. Fetches stay sequential.
- Next: none for this issue. Concurrent item fetches are still out of scope.
