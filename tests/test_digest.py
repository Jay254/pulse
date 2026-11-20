from datetime import UTC, date, datetime, timedelta

import httpx

from pulse.cli import main
from pulse.digest import collect, rank, render, run_digest
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


def test_run_digest_writes_file_and_marks_sent(tmp_path):
    items = [item("a", 3), item("b", 2), item("c", 1)]
    with Store(tmp_path / "t.db") as store:
        path = run_digest(store, {"x": lambda: items}, tmp_path / "out", date(2026, 11, 20), 2)
        assert path == tmp_path / "out" / "2026-11-20.md"
        body = path.read_text()
        assert "[c]" in body and "[b]" in body and "[a]" not in body
        second = run_digest(store, {"x": lambda: items}, tmp_path / "out", date(2026, 11, 21), 2)
        assert "[a]" in second.read_text() and "[c]" not in second.read_text()


def test_cli_digest(tmp_path, monkeypatch):
    monkeypatch.setattr("pulse.cli.default_collectors", lambda: {"x": lambda: [item("a")]})
    code = main(["digest", "--db", str(tmp_path / "d" / "p.db"), "--out", str(tmp_path / "o")])
    assert code == 0
    assert len(list((tmp_path / "o").glob("*.md"))) == 1
