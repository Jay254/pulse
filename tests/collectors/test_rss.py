import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from pulse.collectors.rss import DEFAULT_FEEDS_PATH, _parse_feed, fetch_feeds, load_feeds

FIXTURES = Path(__file__).parents[1] / "fixtures"
HTML_URL = "https://html.example.com/feed.xml"
RSS_URL = "https://blog.example.com/feed.xml"
ATOM_URL = "https://atom.example.com/atom.xml"
BAD_URL = "https://down.example.com/feed.xml"
JUNK_URL = "https://junk.example.com/feed.xml"


def make_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == RSS_URL:
            return httpx.Response(200, content=(FIXTURES / "rss2.xml").read_bytes())
        if url == HTML_URL:
            return httpx.Response(200, content=(FIXTURES / "rss_html.xml").read_bytes())
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


def test_atom_xhtml_text_is_kept():
    xml = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
    <title type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">Hi <b>there</b></div></title>
    <link href="https://a.example/p"/>
    <content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml"><p>Body text</p></div></content>
    </entry></feed>"""
    (item,) = _parse_feed(xml)
    assert item.title == "Hi there"
    assert item.text == "Body text"


def test_atom_relative_links_are_resolved():
    xml = b"""<feed xmlns="http://www.w3.org/2005/Atom" xml:base="https://a.example/blog/">
    <entry><link href="posts/one"/></entry>
    <entry><link href="/root"/></entry>
    </feed>"""
    urls = [i.url for i in _parse_feed(xml, "https://feeds.example/atom.xml")]
    assert urls == ["https://a.example/blog/posts/one", "https://a.example/root"]
    (item,) = _parse_feed(
        b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><link href="x"/></entry></feed>',
        "https://f.example/dir/atom.xml",
    )
    assert item.url == "https://f.example/dir/x"


def test_rss_guid_only_used_when_permalink():
    xml = b"""<rss><channel>
    <item><guid isPermaLink="false">post-123</guid></item>
    <item><guid>not a url</guid></item>
    <item><guid>https://a.example/p</guid></item>
    </channel></rss>"""
    assert [i.url for i in _parse_feed(xml)] == ["https://a.example/p"]


def test_strips_html_from_text():
    first, second = fetch_feeds([HTML_URL], client=make_client())
    assert first.title == "Token fraud"
    assert first.text == (
        "Token fraud Claire Vo runs Tom & Jerry <3 \u00a9 2025. Second paragraph with bold text."
    )
    assert "<" not in first.text.replace("<3", "")
    assert "alert" not in first.text
    assert "color" not in first.text
    assert second.title == "Plain title & more"
    assert second.text == "Atom-like summary."


def test_atom_text_types_are_respected():
    xml = b"""<feed xmlns="http://www.w3.org/2005/Atom" xmlns:x="http://www.w3.org/1999/xhtml">
    <entry>
      <title>Literal &lt;b&gt;tags&lt;/b&gt;</title>
      <link href="https://a.example/1"/>
      <content type="text">Write &lt;b&gt;bold&lt;/b&gt; literally</content>
    </entry>
    <entry>
      <title type="html">&lt;i&gt;Marked&lt;/i&gt; up &amp;amp; done</title>
      <link href="https://a.example/2"/>
      <summary type="html">&lt;p&gt;Hello &lt;b&gt;there&lt;/b&gt;&lt;/p&gt;</summary>
    </entry>
    <entry>
      <title>Xhtml</title>
      <link href="https://a.example/3"/>
      <content type="xhtml"><x:div>Keep <x:b>this</x:b>
        text</x:div></content>
    </entry>
    </feed>"""
    one, two, three = _parse_feed(xml)
    assert one.title == "Literal <b>tags</b>"
    assert one.text == "Write <b>bold</b> literally"
    assert two.title == "Marked up & done"
    assert two.text == "Hello there"
    assert three.text == "Keep this text"
