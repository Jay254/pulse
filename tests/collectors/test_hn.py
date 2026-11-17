from datetime import UTC, datetime

import httpx

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
