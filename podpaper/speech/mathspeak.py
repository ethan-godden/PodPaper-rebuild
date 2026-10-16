"""Rule-based math readings: LaTeX to MathML to speech through the Node bridge.

The work is done by ``podpaper/node/mathspeak.mjs`` (MathJax 4 for LaTeX to MathML, the
Speech Rule Engine for ClearSpeak and MathSpeak readings). This module runs that CLI once
per batch, watches it item by item, and validates what comes back. See
``docs/adr/0002-mathjax-sre-bridge.md``.
"""

from __future__ import annotations

import json
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import IO

from pydantic import BaseModel, ConfigDict, ValidationError

NODE_DIR = Path(__file__).resolve().parent.parent / "node"
SCRIPT = NODE_DIR / "mathspeak.mjs"
NODE_MODULES = NODE_DIR / "node_modules"

DEFAULT_TIMEOUT_S = 600.0
"""Wall-clock limit for one ``verbalize`` call, restarts included."""
DEFAULT_ITEM_TIMEOUT_S = 10.0
"""Longest wait for one item's result. Ordinary formulas take a few milliseconds."""
STARTUP_GRACE_S = 10.0
"""Extra wait for the first result of a process: Node has to load MathJax and SRE first."""
_EXIT_WAIT_S = 10.0


class MathSpeechError(RuntimeError):
    """The Node bridge is unavailable, crashed, broke its output contract, or ran out of time."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MathItem(_Model):
    """One formula to verbalize. ``id`` is echoed back; ``display`` marks display math."""

    id: str
    tex: str
    display: bool = False


class Readings(_Model):
    """The two literal rule readings of one formula."""

    clearspeak: str
    mathspeak: str


class MathSpeech(_Model):
    """Result for one ``MathItem``.

    ``ok`` is false when the LaTeX did not parse, the formula was too large or too slow, or
    no reading could be produced; then ``error`` says why and ``mathml`` and ``speech`` are
    ``None``.
    """

    id: str
    ok: bool
    mathml: str | None = None
    speech: Readings | None = None
    error: str | None = None


class _WireResult(_Model):
    """One output line of the CLI. ``id`` is null when the CLI could not read the id."""

    id: str | None
    ok: bool
    mathml: str | None = None
    speech: Readings | None = None
    error: str | None = None


def bridge_problem() -> str | None:
    """Return why the bridge cannot run, or ``None`` when it can."""
    if shutil.which("node") is None:
        return "node was not found on PATH; install Node.js (version 20 or later)"
    if not SCRIPT.is_file():
        return f"bridge script is missing: {SCRIPT}"
    if not NODE_MODULES.is_dir():
        return f'{NODE_MODULES} is missing; run "npm ci" in {NODE_DIR}'
    return None


def verbalize(
    items: Sequence[MathItem],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    item_timeout_s: float = DEFAULT_ITEM_TIMEOUT_S,
) -> list[MathSpeech]:
    """Return one ``MathSpeech`` per item, in input order. Results are matched by position.

    A formula that fails to parse, is too large, or takes longer than ``item_timeout_s``
    comes back with ``ok=False``; it does not raise and does not affect the other items.
    Items never see each other's macro definitions. A slow item costs one process restart:
    the bridge is killed, that item is marked failed, and the items after it are run in a
    new process.

    ``MathSpeechError`` is raised only when the bridge itself cannot run, exits non-zero,
    returns output that does not match the input, or the whole call exceeds ``timeout_s``.
    """
    if not items:
        return []
    problem = bridge_problem()
    if problem is not None:
        raise MathSpeechError(problem)

    deadline = time.monotonic() + timeout_s
    results: list[MathSpeech] = []
    while len(results) < len(items):
        pending = items[len(results) :]
        done = _run_batch(pending, item_timeout_s=item_timeout_s, deadline=deadline)
        results.extend(done)
        if len(done) < len(pending):
            if time.monotonic() >= deadline:
                raise MathSpeechError(
                    f"math speech bridge exceeded {timeout_s:g} s on {len(items)} item(s); "
                    f"{len(results)} finished"
                )
            slow = pending[len(done)]
            results.append(
                MathSpeech(
                    id=slow.id,
                    ok=False,
                    error=f"math speech timed out after {item_timeout_s:g} s on this formula",
                )
            )
    return results


def _pump(stream: IO[bytes], lines: queue.Queue[bytes | None]) -> None:
    """Forward stdout lines to the queue; ``None`` marks end of output."""
    try:
        # Binary iteration splits on b"\n" only, unlike str.splitlines().
        for raw in stream:
            lines.put(raw)
    finally:
        lines.put(None)


def _run_batch(
    items: Sequence[MathItem], *, item_timeout_s: float, deadline: float
) -> list[MathSpeech]:
    """Run one bridge process over ``items``.

    Returns a result for every item, or only for the items before the first one whose
    result did not arrive in time (the process is killed at that point).
    """
    # ASCII-only JSON: U+2028, U+2029 and U+0085 must never reach the pipe unescaped.
    payload = "".join(json.dumps(item.model_dump(), ensure_ascii=True) + "\n" for item in items)
    results: list[MathSpeech] = []
    with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as stderr:
        stdin.write(payload.encode("ascii"))
        stdin.seek(0)
        try:
            proc = subprocess.Popen(
                ["node", str(SCRIPT)],
                stdin=stdin,
                stdout=subprocess.PIPE,
                stderr=stderr,
                cwd=NODE_DIR,
            )
        except OSError as exc:
            raise MathSpeechError(f"could not start node: {exc}") from exc
        assert proc.stdout is not None
        lines: queue.Queue[bytes | None] = queue.Queue()
        reader = threading.Thread(target=_pump, args=(proc.stdout, lines), daemon=True)
        reader.start()
        try:
            for index, item in enumerate(items):
                wait = item_timeout_s + (STARTUP_GRACE_S if index == 0 else 0.0)
                wait = min(wait, deadline - time.monotonic())
                try:
                    raw = lines.get(timeout=max(wait, 0.0))
                except queue.Empty:
                    return results
                if raw is None:
                    _check_exit(proc, stderr)
                    raise MathSpeechError(
                        f"math speech bridge returned {len(results)} result(s) "
                        f"for {len(items)} item(s)"
                    )
                results.append(_parse_result(item, raw))
            try:
                extra = lines.get(timeout=_EXIT_WAIT_S)
            except queue.Empty as exc:
                raise MathSpeechError(
                    "math speech bridge did not exit after its last item"
                ) from exc
            if extra is not None:
                raise MathSpeechError(
                    f"math speech bridge returned more than {len(items)} result(s)"
                )
            _check_exit(proc, stderr)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            reader.join(timeout=_EXIT_WAIT_S)
            if not reader.is_alive():
                # Closing while the reader is still blocked in read() would wait on its lock.
                proc.stdout.close()
    return results


def _check_exit(proc: subprocess.Popen[bytes], stderr: IO[bytes]) -> None:
    """Raise if the finished bridge process reported failure."""
    try:
        code = proc.wait(timeout=_EXIT_WAIT_S)
    except subprocess.TimeoutExpired as exc:
        raise MathSpeechError("math speech bridge closed its output but did not exit") from exc
    if code == 0:
        return
    stderr.seek(0)
    detail = stderr.read().decode("utf-8", errors="replace").strip()[-2000:] or "no stderr output"
    hint = (
        f' (dependencies look incomplete; run "npm ci" in {NODE_DIR})'
        if "ERR_MODULE_NOT_FOUND" in detail or "Cannot find module" in detail
        else ""
    )
    raise MathSpeechError(f"math speech bridge exited with code {code}{hint}: {detail}")


def _parse_result(item: MathItem, raw: bytes) -> MathSpeech:
    """Validate one output line as the result for ``item`` (matched by position)."""
    try:
        wire = _WireResult.model_validate_json(raw)
    except ValidationError as exc:
        raise MathSpeechError(
            f"math speech bridge returned an invalid result for item {item.id!r}: {exc}"
        ) from exc
    if wire.id is None:
        # The CLI could not read this line's id; that is a failure of this item only.
        if wire.ok:
            raise MathSpeechError(f"math speech bridge lost the id of item {item.id!r}")
    elif wire.id != item.id:
        raise MathSpeechError(
            f"math speech bridge results out of order: expected id {item.id!r}, got {wire.id!r}"
        )
    if wire.ok and (wire.speech is None or wire.mathml is None):
        raise MathSpeechError(
            f"math speech bridge marked item {item.id!r} ok without mathml and speech"
        )
    if not wire.ok:
        return MathSpeech(id=item.id, ok=False, error=wire.error or "unknown bridge error")
    return MathSpeech(id=item.id, ok=True, mathml=wire.mathml, speech=wire.speech)
