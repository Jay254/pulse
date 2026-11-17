# Pulse

A personal research feed that learns what you care about.

Pulse collects new items from Hacker News, arXiv, RSS, GitHub, and X posts you share, removes
duplicates, ranks them with a model trained on your own ratings, and sends a short daily digest
to Telegram. One tap turns an idea into a GitHub issue.

## Develop

```sh
uv sync
uv run pytest
uv run ruff check .
```
