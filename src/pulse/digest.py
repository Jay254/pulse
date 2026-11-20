"""Build the daily digest: collect, store, rank, write markdown, mark sent."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx

from pulse.collectors import arxiv, hn, rss
from pulse.models import Item
from pulse.store import Store

log = logging.getLogger(__name__)

DEFAULT_LIMIT = 10
_LINE_MAX = 200
# Each extra source that saw an item makes it rank as if it were this much newer.
_MULTI_SOURCE_BOOST = timedelta(hours=24)

Collector = Callable[[], list[Item]]


def default_collectors() -> dict[str, Collector]:
    """The collectors that run without credentials."""
    return {
        "hn": hn.fetch_top,
        "arxiv": arxiv.fetch_recent,
        "rss": lambda: rss.fetch_feeds(rss.load_feeds()),
    }


def _when(item: Item) -> datetime:
    when = item.published_at or item.fetched_at
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def rank(items: Sequence[Item]) -> list[Item]:
    """Order items for the digest: newest first, boosted for each extra source.

    A learned ranker replaces this later; keep the signature.
    """

    def score(item: Item) -> datetime:
        extra = max(len(item.sources) - 1, 0)
        return _when(item) + _MULTI_SOURCE_BOOST * extra

    return sorted(items, key=score, reverse=True)


def _one_line(text: str) -> str:
    line = " ".join(text.split())
    return line if len(line) <= _LINE_MAX else line[: _LINE_MAX - 3].rstrip() + "..."


def _escape(text: str) -> str:
    """Escape characters that would break a markdown link label."""
    return re.sub(r"([\\\[\]])", r"\\\1", " ".join(text.split()))


def render(items: Sequence[Item], day: date) -> str:
    """Render the digest as markdown: title, sources, link, one line of text."""
    lines = [f"# Pulse digest {day.isoformat()}", ""]
    if not items:
        lines.append("No new items today.")
    for n, item in enumerate(items, start=1):
        sources = ", ".join(item.sources or (item.source,))
        lines.append(f"{n}. [{_escape(item.title)}]({item.url.strip()})")
        detail = f"{sources}: {_one_line(item.text)}" if item.text.strip() else sources
        lines.append(f"   {detail}")
    return "\n".join(lines) + "\n"


def collect(collectors: dict[str, Collector]) -> list[Item]:
    """Run each collector; a failing source is logged and skipped."""
    items: list[Item] = []
    for name, fetch in collectors.items():
        try:
            items.extend(fetch())
        except (httpx.HTTPError, ValueError, OSError) as exc:
            log.warning("collector %s failed: %s", name, exc)
    return items


def run_digest(
    store: Store,
    collectors: dict[str, Collector],
    out_dir: Path | str,
    day: date | None = None,
    limit: int = DEFAULT_LIMIT,
) -> Path:
    """Collect, store, pick the top `limit` unsent items, write the file, mark them sent."""
    day = day or datetime.now(UTC).date()
    store.upsert(collect(collectors))
    picked = rank(store.unsent(-1))[:limit]
    path = Path(out_dir) / f"{day.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(picked, day), encoding="utf-8")
    store.mark_sent(item.key for item in picked)
    return path
