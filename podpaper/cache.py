"""Content-addressed blob store and stage cache.

A stage unit is done if and only if its cache key exists. The key hashes the
stage name, its version, and every input that can change the output (model
revision, parameters, input hashes), so killing a run and starting it again
resumes from the last finished unit, and changing a parameter recomputes only
what depends on it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json(value: Any) -> str:
    """Deterministic JSON for hashing. Pydantic models are dumped first."""

    def default(obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"cannot hash {type(obj).__name__}")

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=default)


def cache_key(stage: str, version: int, parts: Any) -> str:
    return sha256_bytes(stable_json([stage, version, parts]).encode())


class BlobStore:
    """Immutable files named by the sha256 of their content."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, digest: str) -> Path:
        return self.root / digest[:2] / digest

    def has(self, digest: str) -> bool:
        return self.path(digest).exists()

    def put(self, data: bytes) -> str:
        digest = sha256_bytes(data)
        target = self.path(digest)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                os.replace(tmp, target)  # atomic: a killed run never leaves a partial blob
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        return digest

    def get(self, digest: str) -> bytes:
        return self.path(digest).read_bytes()


class StageCache:
    """Maps cache keys to blobs, in SQLite."""

    def __init__(self, db_path: Path, blobs: BlobStore) -> None:
        self.blobs = blobs
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS stage_cache ("
            "key TEXT PRIMARY KEY, stage TEXT NOT NULL, version INTEGER NOT NULL, "
            "blob TEXT NOT NULL, seconds REAL NOT NULL, created REAL NOT NULL)"
        )
        self._db.commit()
        self.hits = 0
        self.misses = 0

    def close(self) -> None:
        self._db.close()

    def lookup(self, key: str) -> bytes | None:
        row = self._db.execute("SELECT blob FROM stage_cache WHERE key = ?", (key,)).fetchone()
        if row is None or not self.blobs.has(row[0]):
            return None
        return self.blobs.get(row[0])

    def run(self, stage: str, version: int, parts: Any, fn: Callable[[], bytes]) -> bytes:
        """Return the cached bytes for this unit, computing and storing them if absent."""
        key = cache_key(stage, version, parts)
        cached = self.lookup(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        started = time.monotonic()
        data = fn()
        digest = self.blobs.put(data)
        self._db.execute(
            "INSERT OR REPLACE INTO stage_cache VALUES (?, ?, ?, ?, ?, ?)",
            (key, stage, version, digest, time.monotonic() - started, time.time()),
        )
        self._db.commit()
        return data

    def run_model[M: BaseModel](
        self, stage: str, version: int, parts: Any, model: type[M], fn: Callable[[], M]
    ) -> M:
        """Like ``run`` for a stage whose output is one pydantic model."""
        data = self.run(stage, version, parts, lambda: fn().model_dump_json().encode())
        return model.model_validate_json(data)
