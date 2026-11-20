import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, timedelta

import httpx

from pulse.cli import main
from pulse.digest import collect, rank, render, run_digest, select
from pulse.models import Item
from pulse.store import Store

NOW = datetime(2026, 11, 20, 4, 0, tzinfo=UTC)


def item(title, hours_ago=0, sources=("hn",), text="", url=None):
    return Item(
        source=sources[0],
        sources=tuple(sources),
        url=url or f"https://example.com/{title}",
        title=title,
        text=text,
        published_at=NOW - timedelta(hours=hours_ago),
        fetched_at=NOW,
    )


def test_rank_newest_first():
    ranked = rank([item("old", 10), item("new", 1), item("mid", 5)])
    assert [i.title for i in ranked] == ["new", "mid", "old"]


def test_rank_boosts_multi_source_items():
    ranked = rank([item("new", 1), item("old-but-shared", 10, sources=("hn", "rss"))])
    assert [i.title for i in ranked] == ["old-but-shared", "new"]


def test_rank_boost_is_bounded():
    ranked = rank([item("new", 1), item("ancient-shared", 100, sources=("hn", "rss"))])
    assert [i.title for i in ranked] == ["new", "ancient-shared"]


def src(title, source, hours_ago=1, sources=None):
    return item(title, hours_ago, sources=sources or (source,))


def titles(items):
    return [i.title for i in items]


def test_select_drops_items_older_than_cutoff():
    old = [src("old", "hn", 24 * 3 + 1)]
    assert titles(select([*old, src("new", "hn", 24 * 3 - 1)], NOW)) == ["new"]


def test_select_cutoff_falls_back_to_first_seen():
    undated = Item(
        source="hn", url="https://e.com/u", title="u", fetched_at=NOW - timedelta(days=5)
    )
    assert select([undated], NOW) == []
    assert select([undated], NOW, max_age=timedelta(days=9)) == [undated]


def test_select_gives_each_source_its_slots():
    items = [src(f"hn{n}", "hn", n) for n in range(1, 9)]
    items += [src(f"ax{n}", "arxiv", 20 + n) for n in range(1, 6)]
    items += [src(f"rs{n}", "rss", 30 + n) for n in range(1, 6)]
    got = select(items, NOW)
    assert len(got) == 10
    assert sum(i.source == "hn" for i in got) == 4
    assert sum(i.source == "arxiv" for i in got) == 3
    assert sum(i.source == "rss" for i in got) == 3
    assert "hn5" not in titles(got) and "hn4" in titles(got)


def test_select_fills_empty_slots_from_best_remaining():
    items = [src(f"hn{n}", "hn", n) for n in range(1, 9)]
    items += [src("ax1", "arxiv", 20)]
    got = select(items, NOW)
    assert len(got) == 9
    assert "ax1" in titles(got)
    assert sum(i.source == "hn" for i in got) == 8
    assert titles(select([*items, src("rs1", "rss", 40)], NOW))[-1] == "rs1"


def test_select_counts_shared_item_once_in_first_source():
    shared = Item(
        source="hn",
        sources=("hn", "rss"),
        url="https://e.com/s",
        title="shared",
        published_at=NOW,
        fetched_at=NOW,
    )
    dup = Item(source="rss", url="https://e.com/s/", title="dup", published_at=NOW, fetched_at=NOW)
    got = select([shared, dup], NOW)
    assert titles(got) == ["shared"]


def test_select_respects_limit():
    items = [src(f"hn{n}", "hn", n) for n in range(1, 9)]
    items += [src(f"ax{n}", "arxiv", n) for n in range(1, 4)]
    assert len(select(items, NOW, limit=2)) == 2


def test_render_lists_title_sources_link_and_line():
    out = render(
        [
            item(
                "A [x]",
                sources=("hn", "rss"),
                text="first line\n\nsecond   line",
                url="https://a.io/p",
            )
        ],
        date(2026, 11, 20),
    )
    assert out == (
        "# Pulse digest 2026-11-20\n\n"
        "1. [A \\[x\\]](https://a.io/p)\n"
        "   hn, rss: first line second line\n"
    )


def test_render_truncates_text_and_handles_empty():
    out = render([item("t", text="word " * 100)], date(2026, 11, 20))
    assert out.splitlines()[-1].endswith("...")
    assert "No new items today." in render([], date(2026, 11, 20))


def test_collect_skips_failing_collector():
    def boom():
        raise httpx.ConnectError("down")

    assert [i.title for i in collect({"bad": boom, "ok": lambda: [item("a")]})] == ["a"]


def test_collect_skips_collector_with_malformed_xml():
    def bad_xml():
        raise ET.ParseError("not well-formed")

    assert [i.title for i in collect({"arxiv": bad_xml, "ok": lambda: [item("a")]})] == ["a"]


def test_run_digest_same_day_rerun_keeps_file_and_sent_state(tmp_path):
    items = [item("a", 3), item("b", 2), item("c", 1)]
    day = date(2026, 11, 20)
    with Store(tmp_path / "t.db") as store:
        path = run_digest(store, {"x": lambda: items}, tmp_path / "out", day, 2, NOW)
        first = path.read_text()
        again = run_digest(store, {"x": lambda: items}, tmp_path / "out", day, 2, NOW)
        assert again == path
        assert path.read_text() == first
        next_day = run_digest(
            store, {"x": lambda: items}, tmp_path / "out", date(2026, 11, 21), 2, NOW
        )
        assert "[a]" in next_day.read_text()


def test_run_digest_writes_file_and_marks_sent(tmp_path):
    items = [item("a", 3), item("b", 2), item("c", 1)]
    with Store(tmp_path / "t.db") as store:
        path = run_digest(store, {"x": lambda: items}, tmp_path / "out", date(2026, 11, 20), 2, NOW)
        assert path == tmp_path / "out" / "2026-11-20.md"
        body = path.read_text()
        assert "[c]" in body and "[b]" in body and "[a]" not in body
        second = run_digest(
            store, {"x": lambda: items}, tmp_path / "out", date(2026, 11, 21), 2, NOW
        )
        assert "[a]" in second.read_text() and "[c]" not in second.read_text()


def test_cli_digest(tmp_path, monkeypatch):
    monkeypatch.setattr("pulse.cli.default_collectors", lambda: {"x": lambda: [item("a")]})
    code = main(["digest", "--db", str(tmp_path / "d" / "p.db"), "--out", str(tmp_path / "o")])
    assert code == 0
    assert len(list((tmp_path / "o").glob("*.md"))) == 1
