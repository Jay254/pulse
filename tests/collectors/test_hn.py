import logging
from datetime import UTC, datetime

import httpx
import pytest

from pulse.collectors.hn import fetch_top

STORIES = {
    1: {
        "id": 1,
        "type": "story",
        "by": "alice",
        "time": 1700000000,
        "title": "A",
        "url": "https://example.com/a",
    },
    2: {
        "id": 2,
        "type": "story",
        "by": "bob",
        "time": 1700000100,
        "title": "Ask HN: Q",
        "text": "body",
    },
    3: {"id": 3, "type": "story", "dead": True, "title": "Dead"},
    4: {"id": 4, "deleted": True},
    5: {"id": 5, "type": "comment", "text": "hi"},
}


def make_client(calls: list[str] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if calls is not None:
            calls.append(path)
        if path.endswith("topstories.json"):
            return httpx.Response(200, json=list(STORIES))
        story_id = int(path.rsplit("/", 1)[1].removesuffix(".json"))
        return httpx.Response(200, json=STORIES[story_id])

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_normal_story():
    [item] = fetch_top(limit=1, client=make_client())
    assert item.source == "hn"
    assert item.title == "A"
    assert item.url == "https://example.com/a"
    assert item.author == "alice"
    assert item.published_at == datetime.fromtimestamp(1700000000, UTC)


def test_story_without_url_uses_hn_link():
    items = fetch_top(limit=2, client=make_client())
    assert items[1].url == "https://news.ycombinator.com/item?id=2"
    assert items[1].text == "body"


def test_dead_deleted_and_non_story_skipped():
    items = fetch_top(client=make_client())
    assert [i.title for i in items] == ["A", "Ask HN: Q"]


def test_limit_respected():
    calls: list[str] = []
    fetch_top(limit=2, client=make_client(calls))
    assert len(calls) == 3  # topstories + 2 items


def test_fills_limit_past_dead_and_deleted():
    extra = {
        6: {
            "id": 6,
            "type": "story",
            "title": "Extra",
            "url": "https://example.com/extra",
        }
    }
    # Dead, deleted, and a comment sit inside the first `limit` ids.
    ids = [3, 4, 5, 1, 2, 6]
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("topstories.json"):
            return httpx.Response(200, json=ids)
        story_id = int(path.rsplit("/", 1)[1].removesuffix(".json"))
        return httpx.Response(200, json={**STORIES, **extra}[story_id])

    items = fetch_top(limit=2, client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert [item.title for item in items] == ["A", "Ask HN: Q"]
    assert not any(path.endswith("/6.json") for path in calls)


def test_failed_story_is_skipped(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("topstories.json"):
            return httpx.Response(200, json=[1, 99, 2])
        story_id = int(path.rsplit("/", 1)[1].removesuffix(".json"))
        if story_id == 99:
            return httpx.Response(500)
        return httpx.Response(200, json=STORIES[story_id])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.WARNING, logger="pulse.collectors.hn"):
        items = fetch_top(limit=2, client=client)
    assert [item.title for item in items] == ["A", "Ask HN: Q"]
    warned = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("99" in message for message in warned)


def test_timed_out_story_is_skipped(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("topstories.json"):
            return httpx.Response(200, json=[1, 99, 2])
        story_id = int(path.rsplit("/", 1)[1].removesuffix(".json"))
        if story_id == 99:
            raise httpx.ReadTimeout("timed out")
        return httpx.Response(200, json=STORIES[story_id])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.WARNING, logger="pulse.collectors.hn"):
        items = fetch_top(limit=2, client=client)
    assert [item.title for item in items] == ["A", "Ask HN: Q"]
    warned = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("99" in message for message in warned)


def test_topstories_failure_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_top(limit=2, client=client)
