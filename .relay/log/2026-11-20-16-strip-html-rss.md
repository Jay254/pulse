# #16 Strip HTML from RSS item text

Agent: claude
Date: 2026-11-20

- Did: added `html_to_text()` in the RSS collector (standard library `HTMLParser`). RSS and Atom item text is converted to plain text: tags dropped, entities decoded, whitespace collapsed, `<script>` and `<style>` contents removed.
- Did: titles are cleaned the same way only when they contain a `<`.
- Files: `src/pulse/collectors/rss.py`, `tests/collectors/test_rss.py`, `tests/fixtures/rss_html.xml`
- Tests: added `test_strips_html_from_text` with nested tags, entities, script and style blocks. All tests, ruff check, and ruff format pass.
- Why: block-level tags (`p`, `div`, `li`, and similar) become spaces so adjacent paragraphs do not run together; inline tags add none.
- Next: none.
