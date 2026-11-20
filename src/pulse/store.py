"""SQLite store for collected items, deduplicated across sources."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from pulse.models import Item

SCHEMA_VERSION = 1

_SCHEMA_V1 = """
CREATE TABLE items (
    key           TEXT PRIMARY KEY,
    url           TEXT NOT NULL,
    title         TEXT NOT NULL,
    text          TEXT NOT NULL,
    author        TEXT,
    published_at  TEXT,
    first_seen_at TEXT NOT NULL,
    sent_at       TEXT,
    sources       TEXT NOT NULL
);
CREATE INDEX items_unsent ON items (sent_at, published_at);
"""


def _to_iso(value: datetime) -> str:
    """Store datetimes in UTC so string order matches time order."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC)
    return value.isoformat()


def _from_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class Store:
    """Persistent item store keyed by `Item.key`."""

    def __init__(self, path: str | Path) -> None:
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._migrate()

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _migrate(self) -> None:
        """Apply schema steps newer than `PRAGMA user_version`."""
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"database schema {version} is newer than supported {SCHEMA_VERSION}"
            )
        if version < 1:
            with self._db:
                self._db.executescript(f"BEGIN;{_SCHEMA_V1}PRAGMA user_version = 1;COMMIT;")

    def upsert(self, items: Iterable[Item]) -> int:
        """Insert new items and add new sources to existing ones.

        Returns the number of items that were not in the store before.
        """
        new = 0
        with self._db:
            for item in items:
                row = self._db.execute(
                    "SELECT sources FROM items WHERE key = ?", (item.key,)
                ).fetchone()
                if row is None:
                    self._db.execute(
                        "INSERT INTO items (key, url, title, text, author, published_at,"
                        " first_seen_at, sources) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            item.key,
                            item.url,
                            item.title,
                            item.text,
                            item.author,
                            _to_iso(item.published_at) if item.published_at else None,
                            _to_iso(item.fetched_at),
                            json.dumps([item.source]),
                        ),
                    )
                    new += 1
                    continue
                sources = json.loads(row["sources"])
                if item.source not in sources:
                    sources.append(item.source)
                    self._db.execute(
                        "UPDATE items SET sources = ? WHERE key = ?",
                        (json.dumps(sources), item.key),
                    )
        return new

    def sources(self, key: str) -> list[str]:
        """Sources that have seen the item, in first-seen order."""
        row = self._db.execute("SELECT sources FROM items WHERE key = ?", (key,)).fetchone()
        return json.loads(row["sources"]) if row else []

    def unsent(self, limit: int) -> list[Item]:
        """Items not yet sent, newest first.

        Newest is by `published_at`, falling back to `first_seen_at`. The returned
        `Item.source` is the first source that saw the item and `Item.sources` lists all.
        A negative `limit` returns every unsent item.
        """
        rows = self._db.execute(
            "SELECT * FROM items WHERE sent_at IS NULL"
            " ORDER BY COALESCE(published_at, first_seen_at) DESC, key LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            Item(
                source=json.loads(r["sources"])[0],
                sources=tuple(json.loads(r["sources"])),
                url=r["url"],
                title=r["title"],
                text=r["text"],
                author=r["author"],
                published_at=_from_iso(r["published_at"]),
                fetched_at=datetime.fromisoformat(r["first_seen_at"]),
            )
            for r in rows
        ]

    def mark_sent(self, keys: Iterable[str], at: datetime | None = None) -> None:
        """Record that items were sent. Already sent items keep their first `sent_at`."""
        stamp = _to_iso(at or datetime.now(UTC))
        with self._db:
            self._db.executemany(
                "UPDATE items SET sent_at = ? WHERE key = ? AND sent_at IS NULL",
                [(stamp, key) for key in keys],
            )
