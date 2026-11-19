import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from pulse.collectors.rss import DEFAULT_FEEDS_PATH, fetch_feeds, load_feeds

FIXTURES = Path(__file__).parents[1] / "fixtures"
RSS_URL = "https://blog.example.com/feed.xml"
ATOM_URL = "https://atom.example.com/atom.xml"
BAD_URL = "https://down.example.com/feed.xml"
JUNK_URL = "https://junk.example.com/feed.xml"


def make_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == RSS_URL:
            return httpx.Response(200, content=(FIXTURES / "rss2.xml").read_bytes())
        if url == ATOM_URL:
            return httpx.Response(200, content=(FIXTURES / "blog_atom.xml").read_bytes())
        if url == JUNK_URL:
            return httpx.Response(200, content=b"<html><not xml")
        if url == BAD_URL:
            return httpx.Response(500)
        raise httpx.ConnectError("unreachable", request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parses_rss2():
    items = fetch_feeds([RSS_URL], client=make_client())
    assert [i.url for i in items] == [
        "https://blog.example.com/first",
        "https://blog.example.com/second",
    ]
    first, second = items
    assert first.source == "rss"
    assert first.title == "First post"
    assert first.text == "Summary of the first post."
    assert first.author == "Ada Lovelace"
    assert first.published_at == datetime(2025, 3, 3, 10, tzinfo=UTC)
    assert second.author is None
    assert second.published_at is None


def test_parses_atom():
    first, second = fetch_feeds([ATOM_URL], client=make_client())
    assert first.source == "rss"
    assert first.url == "https://atom.example.com/posts/1"
    assert first.title == "Atom post"
    assert first.text == "Full content."
    assert first.author == "Grace Hopper"
    assert first.published_at == datetime(2025, 2, 1, 8, 30, tzinfo=UTC)
    assert second.url == "https://atom.example.com/posts/2"
    assert second.published_at == datetime(2025, 1, 15, tzinfo=UTC)


def test_broken_feeds_do_not_fail_others(caplog):
    feeds = [BAD_URL, RSS_URL, "https://gone.example.com/x", JUNK_URL, ATOM_URL]
    with caplog.at_level(logging.WARNING, logger="pulse.collectors.rss"):
        items = fetch_feeds(feeds, client=make_client())
    assert len(items) == 4
    warned = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warned) == 3
    assert any(BAD_URL in m for m in warned)
    assert any(JUNK_URL in m for m in warned)


def test_load_feeds_reads_starter_list():
    feeds = load_feeds()
    assert DEFAULT_FEEDS_PATH.name == "feeds.toml"
    assert len(feeds) == 4
    assert "https://simonwillison.net/atom/everything/" in feeds


def test_load_feeds_custom_path(tmp_path):
    path = tmp_path / "f.toml"
    path.write_text('feeds = ["https://a.example/feed"]\n')
    assert load_feeds(path) == ["https://a.example/feed"]
