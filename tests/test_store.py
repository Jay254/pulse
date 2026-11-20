import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from pulse.models import Item
from pulse.store import SCHEMA_VERSION, Store

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def make(source="hn", url="https://example.com/a", title="A", age_hours=0, **kw):
    return Item(
        source=source,
        url=url,
        title=title,
        published_at=NOW - timedelta(hours=age_hours),
        fetched_at=NOW,
        **kw,
    )


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "pulse.db") as s:
        yield s


def test_upsert_counts_new_items(store):
    assert store.upsert([make(url="https://example.com/a"), make(url="https://example.com/b")]) == 2
    assert store.upsert([make(url="https://example.com/a")]) == 0


def test_dedupe_across_sources_and_url_variants(store):
    hn = make(source="hn", url="https://Example.com/a/?utm_source=x")
    rss = make(source="rss", url="https://example.com/a")
    assert store.upsert([hn]) == 1
    assert store.upsert([rss]) == 0
    assert len(store.unsent(10)) == 1


def test_sources_merge_without_duplicates(store):
    store.upsert([make(source="hn")])
    store.upsert([make(source="rss"), make(source="hn")])
    assert store.sources(make().key) == ["hn", "rss"]


def test_duplicates_within_one_batch(store):
    assert store.upsert([make(source="hn"), make(source="rss")]) == 1
    assert store.sources(make().key) == ["hn", "rss"]


def test_unsent_newest_first_with_limit(store):
    store.upsert(
        [
            make(url="https://example.com/old", age_hours=48),
            make(url="https://example.com/new", age_hours=1),
            make(url="https://example.com/mid", age_hours=24),
        ]
    )
    assert [i.url for i in store.unsent(10)] == [
        "https://example.com/new",
        "https://example.com/mid",
        "https://example.com/old",
    ]
    assert [i.url for i in store.unsent(2)] == [
        "https://example.com/new",
        "https://example.com/mid",
    ]


def test_unsent_round_trips_fields(store):
    item = make(text="body", author="Ann")
    store.upsert([item])
    (got,) = store.unsent(1)
    assert got == item


def test_mark_sent_excludes_items_and_keeps_first_timestamp(store, tmp_path):
    a, b = make(url="https://example.com/a"), make(url="https://example.com/b")
    store.upsert([a, b])
    store.mark_sent([a.key], at=NOW)
    assert [i.url for i in store.unsent(10)] == [b.url]
    store.mark_sent([a.key], at=NOW + timedelta(days=1))
    row = sqlite3.connect(tmp_path / "pulse.db").execute(
        "SELECT sent_at FROM items WHERE key = ?", (a.key,)
    )
    assert row.fetchone()[0] == NOW.isoformat()


def test_sent_items_stay_sent_after_reupsert(store):
    item = make()
    store.upsert([item])
    store.mark_sent([item.key])
    store.upsert([make(source="rss")])
    assert store.unsent(10) == []


def test_schema_version_set_and_persisted(tmp_path):
    path = tmp_path / "pulse.db"
    Store(path).close()
    version = sqlite3.connect(path).execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION
    Store(path).close()


def test_newer_schema_is_rejected(tmp_path):
    path = tmp_path / "pulse.db"
    sqlite3.connect(path).execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}").close()
    with pytest.raises(RuntimeError):
        Store(path)
