from __future__ import annotations

from pathlib import Path

import pytest

from podpaper import ir
from podpaper.cache import BlobStore, StageCache, cache_key


@pytest.fixture
def cache(tmp_path: Path) -> StageCache:
    return StageCache(tmp_path / "db.sqlite", BlobStore(tmp_path / "blobs"))


def test_blob_store_is_content_addressed(tmp_path: Path) -> None:
    store = BlobStore(tmp_path)
    digest = store.put(b"hello")
    assert store.put(b"hello") == digest
    assert store.get(digest) == b"hello"
    assert not store.has("0" * 64)
    assert [p.name for p in tmp_path.rglob("*") if p.is_file()] == [digest]


def test_key_depends_on_stage_version_and_parts() -> None:
    base = cache_key("layout", 1, {"page": "abc", "threshold": 0.5})
    assert base == cache_key("layout", 1, {"threshold": 0.5, "page": "abc"})
    assert base != cache_key("layout", 2, {"page": "abc", "threshold": 0.5})
    assert base != cache_key("route", 1, {"page": "abc", "threshold": 0.5})
    assert base != cache_key("layout", 1, {"page": "abc", "threshold": 0.6})


def test_run_computes_once_and_survives_reopen(tmp_path: Path) -> None:
    calls = []

    def work() -> bytes:
        calls.append(1)
        return b"result"

    first = StageCache(tmp_path / "db.sqlite", BlobStore(tmp_path / "blobs"))
    assert first.run("s", 1, ["x"], work) == b"result"
    assert first.run("s", 1, ["x"], work) == b"result"
    first.close()

    again = StageCache(tmp_path / "db.sqlite", BlobStore(tmp_path / "blobs"))
    assert again.run("s", 1, ["x"], work) == b"result"
    assert len(calls) == 1
    assert (again.hits, again.misses) == (1, 0)


def test_failed_unit_is_not_cached(cache: StageCache) -> None:
    def boom() -> bytes:
        raise RuntimeError("killed")

    with pytest.raises(RuntimeError):
        cache.run("s", 1, ["x"], boom)
    assert cache.run("s", 1, ["x"], lambda: b"ok") == b"ok"


def test_missing_blob_is_recomputed(cache: StageCache) -> None:
    cache.run("s", 1, ["x"], lambda: b"one")
    for path in cache.blobs.root.rglob("*"):
        if path.is_file():
            path.unlink()
    assert cache.run("s", 1, ["x"], lambda: b"two") == b"two"


def test_run_model_round_trips(cache: StageCache) -> None:
    box = cache.run_model("s", 1, ["b"], ir.BBox, lambda: ir.BBox(x0=0, y0=0, x1=1, y1=2))
    again = cache.run_model("s", 1, ["b"], ir.BBox, lambda: ir.BBox(x0=9, y0=9, x1=9, y1=9))
    assert again == box
