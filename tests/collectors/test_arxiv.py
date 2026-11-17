from datetime import UTC, datetime
from pathlib import Path

import httpx

from pulse.collectors.arxiv import fetch_recent

FIXTURE = (Path(__file__).parents[1] / "fixtures" / "arxiv_atom.xml").read_bytes()


def make_client(calls: list[httpx.Request] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        return httpx.Response(200, content=FIXTURE)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parses_saved_atom_fixture():
    items = fetch_recent(client=make_client())
    assert len(items) == 2

    paper, note = items
    assert paper.source == "arxiv"
    assert paper.url == "https://arxiv.org/abs/2403.00001v1"
    assert paper.text == "A short abstract\nabout learning."
    assert paper.published_at == datetime(2024, 3, 1, tzinfo=UTC)

    assert note.source == "arxiv"
    assert note.url == "https://arxiv.org/abs/2402.99999v2"
    assert note.text == "Just one author."
    assert note.published_at == datetime(2024, 2, 15, 12, 30, tzinfo=UTC)


def test_multi_author_uses_et_al():
    paper, note = fetch_recent(client=make_client())
    assert paper.author == "Ada Lovelace et al."
    assert note.author == "Grace Hopper"


def test_title_whitespace_collapsed():
    paper, note = fetch_recent(client=make_client())
    assert paper.title == "Learning with Newlines"
    assert note.title == "Single Author Note"


def test_one_request_sorted_by_submission_date():
    calls: list[httpx.Request] = []
    fetch_recent(categories=("cs.LG", "cs.CL"), max_results=10, client=make_client(calls))
    assert len(calls) == 1
    request = calls[0]
    assert str(request.url).startswith("https://export.arxiv.org/api/query?")
    assert request.url.params["search_query"] == "cat:cs.LG OR cat:cs.CL"
    assert request.url.params["max_results"] == "10"
    assert request.url.params["start"] == "0"
    assert request.url.params["sortBy"] == "submittedDate"
    assert request.url.params["sortOrder"] == "descending"
    assert request.headers["user-agent"] == "pulse/0.1"
