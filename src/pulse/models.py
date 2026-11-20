"""Core data types for Pulse."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query parameters that only track clicks and never change the content of a page.
_TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src", "s", "si"}


def canonical_url(url: str) -> str:
    """Normalize a URL so the same page from different sources dedupes to one key.

    Lowercases scheme and host, drops the fragment, tracking params (utm_* and friends),
    and a trailing slash on the path.
    """
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/") if parts.path not in ("", "/") else ""
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


@dataclass(frozen=True)
class Item:
    """One piece of content collected from any source."""

    source: str  # e.g. "hn", "arxiv", "rss", "github", "x"
    url: str
    title: str
    text: str = ""
    author: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    # Every source that saw it; filled in by the store and ignored in equality.
    sources: tuple[str, ...] = field(default=(), compare=False)

    @property
    def key(self) -> str:
        """Stable identity used for deduplication across sources."""
        return canonical_url(self.url)
