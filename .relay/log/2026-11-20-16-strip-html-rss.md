# #16 Strip HTML from RSS item text

Agent: claude
Date: 2026-11-20

- Did: added `html_to_text()` in the RSS collector (standard library `HTMLParser`). RSS item text and Atom `html` constructs are converted to plain text: tags dropped, entities decoded, whitespace collapsed, `<script>` and `<style>` contents removed.
- Did: RSS titles are cleaned the same way only when they contain a `<`.
- Did: Atom `text` constructs stay literal, `xhtml` is read from its elements, and only `html` goes through `html_to_text()` (Codex review).
- Files: `src/pulse/collectors/rss.py`, `tests/collectors/test_rss.py`, `tests/fixtures/rss_html.xml`
- Tests: added `test_strips_html_from_text` with nested tags, entities, script and style blocks. All tests, ruff check, and ruff format pass.
- Why: block-level tags (`p`, `div`, `li`, and similar) become spaces so adjacent paragraphs do not run together; inline tags add none.
- Next: none.
