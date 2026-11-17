from pulse.models import Item, canonical_url


def test_canonical_url_strips_tracking_fragment_and_case():
    url = "HTTPS://Example.com/Post/?utm_source=x&id=3&fbclid=abc#comments"
    assert canonical_url(url) == "https://example.com/Post?id=3"


def test_canonical_url_keeps_root_and_meaningful_params():
    assert canonical_url("https://news.ycombinator.com/item?id=42") == (
        "https://news.ycombinator.com/item?id=42"
    )
    assert canonical_url("https://example.com/") == "https://example.com"


def test_same_page_from_two_sources_has_same_key():
    a = Item(source="hn", url="https://blog.dev/post/?utm_medium=hn", title="Post")
    b = Item(source="x", url="https://BLOG.dev/post#top", title="Post")
    assert a.key == b.key
