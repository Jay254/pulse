"""Hacker News collector using the official Firebase API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from pulse.models import Item

BASE_URL = "https://hacker-news.firebaseio.com/v0"
ITEM_URL = "https://news.ycombinator.com/item?id={id}"

logger = logging.getLogger(__name__)


def fetch_top(limit: int = 30, client: httpx.Client | None = None) -> list[Item]:
    """Return up to `limit` current top HN stories.

    Walks the top-story list until that many live stories are collected.
    A story that fails to load is logged and skipped. A failure loading the
    top-story list itself still raises.
    """
    if client is None:
        with httpx.Client(timeout=10) as own_client:
            return _fetch_top(limit, own_client)
    return _fetch_top(limit, client)


def _fetch_top(limit: int, client: httpx.Client) -> list[Item]:
    resp = client.get(f"{BASE_URL}/topstories.json")
    resp.raise_for_status()
    items: list[Item] = []
    for story_id in resp.json():
        if len(items) >= limit:
            break
        try:
            story_resp = client.get(f"{BASE_URL}/item/{story_id}.json")
            story_resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
            logger.warning("Skipping HN story %s: %s", story_id, exc)
            continue
        item = _to_item(story_resp.json())
        if item is not None:
            items.append(item)
    return items


def _to_item(data: dict | None) -> Item | None:
    if not data or data.get("deleted") or data.get("dead") or data.get("type") != "story":
        return None
    return Item(
        source="hn",
        url=data.get("url") or ITEM_URL.format(id=data["id"]),
        title=data.get("title", ""),
        text=data.get("text", ""),
        author=data.get("by"),
        published_at=datetime.fromtimestamp(data["time"], UTC) if "time" in data else None,
    )
