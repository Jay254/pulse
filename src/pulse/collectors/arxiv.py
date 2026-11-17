"""arXiv collector using the export Atom API."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from pulse.models import Item

API_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "pulse/0.1"
_ATOM = "http://www.w3.org/2005/Atom"
_NS = {"atom": _ATOM}


def fetch_recent(
    categories: tuple[str, ...] = ("cs.LG", "cs.AI", "cs.CL"),
    max_results: int = 50,
    client: httpx.Client | None = None,
) -> list[Item]:
    """Return recent papers in `categories`, newest submission first (at most `max_results`)."""
    if client is None:
        with httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}) as own_client:
            return _fetch_recent(categories, max_results, own_client)
    return _fetch_recent(categories, max_results, client)


def _fetch_recent(
    categories: tuple[str, ...], max_results: int, client: httpx.Client
) -> list[Item]:
    resp = client.get(
        API_URL,
        params={
            "search_query": " OR ".join(f"cat:{category}" for category in categories),
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        },
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    return _parse_feed(resp.text)


def _parse_feed(xml_text: str) -> list[Item]:
    root = ET.fromstring(xml_text)
    return [_to_item(entry) for entry in root.findall("atom:entry", _NS)]


def _to_item(entry: ET.Element) -> Item:
    raw_title = entry.findtext("atom:title", default="", namespaces=_NS) or ""
    raw_summary = entry.findtext("atom:summary", default="", namespaces=_NS) or ""
    return Item(
        source="arxiv",
        url=_abstract_url(entry),
        title=" ".join(raw_title.split()),
        text=raw_summary.strip(),
        author=_format_author(entry),
        published_at=_parse_published(entry),
    )


def _abstract_url(entry: ET.Element) -> str:
    for link in entry.findall("atom:link", _NS):
        rel = link.get("rel", "alternate")
        link_type = link.get("type")
        if rel == "alternate" and link_type in (None, "text/html"):
            href = link.get("href")
            if href:
                return href
    return (entry.findtext("atom:id", default="", namespaces=_NS) or "").strip()


def _format_author(entry: ET.Element) -> str | None:
    names = []
    for author in entry.findall("atom:author", _NS):
        name = (author.findtext("atom:name", default="", namespaces=_NS) or "").strip()
        if name:
            names.append(name)
    if not names:
        return None
    if len(names) == 1:
        return names[0]
    return f"{names[0]} et al."


def _parse_published(entry: ET.Element) -> datetime | None:
    raw = (entry.findtext("atom:published", default="", namespaces=_NS) or "").strip()
    if not raw:
        return None
    return datetime.fromisoformat(raw)
