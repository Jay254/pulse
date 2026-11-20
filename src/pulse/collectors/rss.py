"""RSS 2.0 and Atom collector driven by `feeds.toml`."""

from __future__ import annotations

import logging
import re
import tomllib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import httpx

from pulse.models import Item

USER_AGENT = "pulse/0.1"
DEFAULT_FEEDS_PATH = Path(__file__).parents[3] / "feeds.toml"
_ATOM = "{http://www.w3.org/2005/Atom}"
_DC = "{http://purl.org/dc/elements/1.1/}"
_CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
_XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"

_SKIPPED_TAGS = {"script", "style"}
_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "tr", "td", "th", "table", "blockquote",
    "pre", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
}  # fmt: skip

_INLINE_TAGS = {"a", "b", "i", "u", "em", "strong", "span", "code", "sub", "sup", "small", "mark"}
_MARKUP_RE = re.compile(
    r"</?(?:" + "|".join(sorted(_SKIPPED_TAGS | _BLOCK_TAGS | _INLINE_TAGS)) + r")\b[^>]*>",
    re.IGNORECASE,
)

logger = logging.getLogger(__name__)


class _TextExtractor(HTMLParser):
    """Collect the text of an HTML fragment, ignoring script and style contents."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        return " ".join("".join(self._parts).split())


def html_to_text(value: str) -> str:
    """Convert an HTML fragment to plain text with entities decoded and whitespace collapsed."""
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return parser.text()


def _clean_title(title: str) -> str:
    """Collapse whitespace, and strip tags only when the title contains known HTML tags.

    Literal angle brackets such as `Vec<T>` are kept.
    """
    return html_to_text(title) if _MARKUP_RE.search(title) else " ".join(title.split())


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
            items.extend(_parse_feed(resp.content, str(resp.url)))
        except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
            logger.warning("Skipping feed %s: %s", url, exc)
    return items


def _parse_feed(content: bytes, base_url: str = "") -> list[Item]:
    root = ET.fromstring(content)
    if root.tag == f"{_ATOM}feed":
        feed_base = urljoin(base_url, root.get(_XML_BASE, ""))
        entries = [_atom_item(entry, feed_base) for entry in root.findall(f"{_ATOM}entry")]
    elif root.tag == "rss":
        entries = [_rss_item(item) for item in root.findall("./channel/item")]
    else:
        raise ValueError(f"unrecognized feed root element {root.tag!r}")
    return [item for item in entries if item is not None]


def _text(element: ET.Element, tag: str) -> str:
    return (element.findtext(tag) or "").strip()


def _rss_guid_url(item: ET.Element) -> str:
    """Return the GUID only when it is a permalink URL, else an empty string."""
    guid = item.find("guid")
    if guid is None or guid.get("isPermaLink", "true").lower() == "false":
        return ""
    value = (guid.text or "").strip()
    return value if value.startswith(("http://", "https://")) else ""


def _rss_item(item: ET.Element) -> Item | None:
    url = _text(item, "link") or _rss_guid_url(item)
    if not url:
        return None
    return Item(
        source="rss",
        url=url,
        title=_clean_title(_text(item, "title")),
        text=html_to_text(_text(item, f"{_CONTENT}encoded") or _text(item, "description")),
        author=_text(item, f"{_DC}creator") or _text(item, "author") or None,
        published_at=_parse_date(_text(item, "pubDate"), rfc2822=True),
    )


def _atom_text(element: ET.Element, tag: str) -> str:
    """Read an Atom text construct as plain text, honoring its `type`.

    `text` (the default) is literal, `xhtml` is already parsed into elements, and `html`
    holds escaped markup that needs converting.
    """
    child = element.find(tag)
    if child is None:
        return ""
    kind = (child.get("type") or "text").lower()
    if kind == "xhtml":
        return " ".join("".join(child.itertext()).split())
    value = (child.text or "").strip()
    if kind in ("html", "text/html"):
        return html_to_text(value)
    return " ".join(value.split())


def _atom_item(entry: ET.Element, feed_base: str = "") -> Item | None:
    url = _atom_link(entry, feed_base)
    if not url:
        return None
    published = _text(entry, f"{_ATOM}published") or _text(entry, f"{_ATOM}updated")
    return Item(
        source="rss",
        url=url,
        title=_atom_text(entry, f"{_ATOM}title"),
        text=_atom_text(entry, f"{_ATOM}content") or _atom_text(entry, f"{_ATOM}summary"),
        author=_text(entry, f"{_ATOM}author/{_ATOM}name") or None,
        published_at=_parse_date(published, rfc2822=False),
    )


def _atom_link(entry: ET.Element, feed_base: str = "") -> str:
    """Return the alternate link resolved against xml:base and the feed URL."""
    entry_base = urljoin(feed_base, entry.get(_XML_BASE, ""))
    for link in entry.findall(f"{_ATOM}link"):
        href = (link.get("href") or "").strip()
        if link.get("rel", "alternate") == "alternate" and href:
            return urljoin(urljoin(entry_base, link.get(_XML_BASE, "")), href)
    entry_id = _text(entry, f"{_ATOM}id")
    return entry_id if entry_id.startswith(("http://", "https://")) else ""


def _parse_date(raw: str, *, rfc2822: bool) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw) if rfc2822 else datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
