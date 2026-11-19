"""RSS 2.0 and Atom collector driven by `feeds.toml`."""

from __future__ import annotations

import logging
import tomllib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

from pulse.models import Item

USER_AGENT = "pulse/0.1"
DEFAULT_FEEDS_PATH = Path(__file__).parents[3] / "feeds.toml"
_ATOM = "{http://www.w3.org/2005/Atom}"
_DC = "{http://purl.org/dc/elements/1.1/}"
_CONTENT = "{http://purl.org/rss/1.0/modules/content/}"

logger = logging.getLogger(__name__)


def load_feeds(path: Path | str = DEFAULT_FEEDS_PATH) -> list[str]:
    """Read the `feeds` list of URLs from a TOML file."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return [str(url) for url in data.get("feeds", [])]


def fetch_feeds(feeds: list[str], client: httpx.Client | None = None) -> list[Item]:
    """Return items from every feed in `feeds`.

    A feed that fails to download or parse is logged as a warning and skipped.
    """
    if client is None:
        with httpx.Client(
            timeout=30, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        ) as own_client:
            return _fetch_feeds(feeds, own_client)
    return _fetch_feeds(feeds, client)


def _fetch_feeds(feeds: list[str], client: httpx.Client) -> list[Item]:
    items: list[Item] = []
    for url in feeds:
        try:
            resp = client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            items.extend(_parse_feed(resp.content))
        except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
            logger.warning("Skipping feed %s: %s", url, exc)
    return items


def _parse_feed(content: bytes) -> list[Item]:
    root = ET.fromstring(content)
    if root.tag == f"{_ATOM}feed":
        entries = [_atom_item(entry) for entry in root.findall(f"{_ATOM}entry")]
    elif root.tag == "rss":
        entries = [_rss_item(item) for item in root.findall("./channel/item")]
    else:
        raise ValueError(f"unrecognized feed root element {root.tag!r}")
    return [item for item in entries if item is not None]


def _text(element: ET.Element, tag: str) -> str:
    return (element.findtext(tag) or "").strip()


def _rss_item(item: ET.Element) -> Item | None:
    url = _text(item, "link") or _text(item, "guid")
    if not url:
        return None
    return Item(
        source="rss",
        url=url,
        title=" ".join(_text(item, "title").split()),
        text=_text(item, f"{_CONTENT}encoded") or _text(item, "description"),
        author=_text(item, f"{_DC}creator") or _text(item, "author") or None,
        published_at=_parse_date(_text(item, "pubDate"), rfc2822=True),
    )


def _atom_item(entry: ET.Element) -> Item | None:
    url = _atom_link(entry)
    if not url:
        return None
    published = _text(entry, f"{_ATOM}published") or _text(entry, f"{_ATOM}updated")
    return Item(
        source="rss",
        url=url,
        title=" ".join(_text(entry, f"{_ATOM}title").split()),
        text=_text(entry, f"{_ATOM}content") or _text(entry, f"{_ATOM}summary"),
        author=_text(entry, f"{_ATOM}author/{_ATOM}name") or None,
        published_at=_parse_date(published, rfc2822=False),
    )


def _atom_link(entry: ET.Element) -> str:
    for link in entry.findall(f"{_ATOM}link"):
        if link.get("rel", "alternate") == "alternate" and link.get("href"):
            return link.get("href", "").strip()
    return _text(entry, f"{_ATOM}id")


def _parse_date(raw: str, *, rfc2822: bool) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw) if rfc2822 else datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
