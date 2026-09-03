"""Tests for the Node math-speech bridge (MathJax 4 + Speech Rule Engine)."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from podpaper.speech import mathspeak
from podpaper.speech.mathspeak import MathItem, MathSpeech, MathSpeechError, verbalize

_problem = mathspeak.bridge_problem()
pytestmark = pytest.mark.skipif(_problem is not None, reason=f"math bridge unavailable: {_problem}")

FORBIDDEN = set("\\$^_{}")

VALID: dict[str, tuple[str, bool]] = {
    "emc2": ("E = mc^2", False),
    "fraction": (r"\frac{a+b}{c}", True),
    "sum": (r"\sum_{i=1}^{n} i^2", True),
    "integral": (r"\int_0^\infty e^{-x^2}\,dx", True),
    "matrix": (r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}", True),
    "greek": (r"\alpha + \beta = \Gamma", False),
    "set": (r"\mathcal{L}\{f\} = \{x_i : x_i^2 < 1\}", True),
}
INVALID_TEX = r"\frac{a}{b"


@pytest.fixture(scope="module")
def batch() -> dict[str, MathSpeech]:
    items = [MathItem(id=key, tex=tex, display=display) for key, (tex, display) in VALID.items()]
    items.insert(3, MathItem(id="invalid", tex=INVALID_TEX, display=True))
    results = verbalize(items)
    assert [r.id for r in results] == [i.id for i in items]
    return {r.id: r for r in results}


def _readings(result: MathSpeech) -> tuple[str, str]:
    assert result.ok, result.error
    assert result.error is None
    assert result.speech is not None
    return result.speech.clearspeak.lower(), result.speech.mathspeak.lower()


def test_emc2(batch: dict[str, MathSpeech]) -> None:
    for reading in _readings(batch["emc2"]):
        assert "equals" in reading
        assert "squared" in reading
    mathml = batch["emc2"].mathml
    assert mathml is not None
    assert mathml.startswith("<math")
    assert "<msup" in mathml


def test_fraction(batch: dict[str, MathSpeech]) -> None:
    clearspeak, mathspeak_reading = _readings(batch["fraction"])
    assert "numerator" in clearspeak
    assert "denominator" in clearspeak
    assert "fraction" in mathspeak_reading
    assert "over" in mathspeak_reading
    for reading in (clearspeak, mathspeak_reading):
        assert "a plus b" in reading


def test_sum_with_limits(batch: dict[str, MathSpeech]) -> None:
    for reading in _readings(batch["sum"]):
        assert "sum" in reading
        assert "i equals 1" in reading
        assert "squared" in reading


def test_integral(batch: dict[str, MathSpeech]) -> None:
    for reading in _readings(batch["integral"]):
        assert "integral" in reading
        assert "infinity" in reading
        assert "d x" in reading


def test_matrix(batch: dict[str, MathSpeech]) -> None:
    for reading in _readings(batch["matrix"]):
        assert "2 by 2" in reading
        assert "matrix" in reading
        assert "row" in reading


def test_greek_letters(batch: dict[str, MathSpeech]) -> None:
    for reading in _readings(batch["greek"]):
        for name in ("alpha", "beta", "gamma"):
            assert name in reading


def test_display_flag_reaches_mathml(batch: dict[str, MathSpeech]) -> None:
    display = batch["fraction"].mathml
    inline = batch["emc2"].mathml
    assert display is not None
    assert inline is not None
    assert 'display="block"' in display
    assert 'display="block"' not in inline


def test_invalid_item_does_not_stop_the_batch(batch: dict[str, MathSpeech]) -> None:
    bad = batch["invalid"]
    assert not bad.ok
    assert bad.mathml is None
    assert bad.speech is None
    assert bad.error
    assert "brace" in bad.error.lower()
    assert len(batch) == len(VALID) + 1
    for key in VALID:
        assert batch[key].ok, key


def test_undefined_macro_is_an_error_not_speech() -> None:
    (result,) = verbalize([MathItem(id="u", tex=r"\notarealmacro x")])
    assert not result.ok
    assert result.error
    assert "undefined" in result.error.lower()


def test_no_latex_characters_in_speech(batch: dict[str, MathSpeech]) -> None:
    for key in VALID:
        speech = batch[key].speech
        assert speech is not None
        for reading in (speech.clearspeak, speech.mathspeak):
            assert reading.strip()
            assert not FORBIDDEN & set(reading), (key, reading)


def test_empty_batch() -> None:
    assert verbalize([]) == []


def test_missing_node_modules_says_npm_ci(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    missing = tmp_path_factory.mktemp("node") / "node_modules"
    monkeypatch.setattr(mathspeak, "NODE_MODULES", missing)
    with pytest.raises(MathSpeechError, match="npm ci"):
        verbalize([MathItem(id="x", tex="x")])


def test_missing_node_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mathspeak.shutil, "which", lambda _name: None)
    with pytest.raises(MathSpeechError, match="node"):
        verbalize([MathItem(id="x", tex="x")])


# --- regressions from review ------------------------------------------------------------

LINE_SEPARATORS = {"ls": chr(0x2028), "ps": chr(0x2029), "nel": chr(0x85)}


def _cli(stdin: bytes) -> list[dict[str, object]]:
    proc = subprocess.run(
        ["node", str(mathspeak.SCRIPT)], input=stdin, capture_output=True, timeout=60, check=True
    )
    return [json.loads(line) for line in proc.stdout.split(b"\n") if line]


@pytest.mark.parametrize("name", sorted(LINE_SEPARATORS))
def test_unicode_line_separator_in_tex_and_id(name: str) -> None:
    sep = LINE_SEPARATORS[name]
    items = [
        MathItem(id="a", tex="x"),
        MathItem(id=f"b{sep}b", tex=f"x {sep} y + \\text{{p{sep}q}}"),
        MathItem(id="c", tex="z"),
    ]
    results = verbalize(items)
    assert [r.id for r in results] == [i.id for i in items]
    assert all(r.ok for r in results), [r.error for r in results]
    speech = results[1].speech
    assert speech is not None
    assert "x y plus" in speech.clearspeak.lower()
    assert "empty" not in speech.clearspeak.lower()


def test_cli_output_is_ascii_one_line_per_item() -> None:
    sep = LINE_SEPARATORS["nel"]
    line = json.dumps({"id": "n", "tex": f"\\text{{a{sep}b caf\u00e9}}"}, ensure_ascii=False)
    proc = subprocess.run(
        ["node", str(mathspeak.SCRIPT)],
        input=line.encode() + b"\n",
        capture_output=True,
        timeout=60,
        check=True,
    )
    assert proc.stdout.isascii()
    assert proc.stdout.count(b"\n") == 1
    assert json.loads(proc.stdout)["ok"] is True


def test_macros_do_not_leak_between_items() -> None:
    pairs = [
        (r"\DeclareMathOperator{\foo}{foo} \foo x", r"\foo y"),
        (r"\DeclarePairedDelimiter{\abs}{\lvert}{\rvert} \abs{x}", r"\abs{y}"),
        (r"\newcommand{\R}{\mathbb{R}} x \in \R", r"y \in \R"),
        (r"\def\q{z} \q", r"\q"),
    ]
    items = [
        MathItem(id=f"{kind}{n}", tex=tex)
        for n, pair in enumerate(pairs)
        for kind, tex in zip(("def", "use"), pair, strict=True)
    ]
    results = {r.id: r for r in verbalize(items)}
    for n in range(len(pairs)):
        assert results[f"def{n}"].ok, results[f"def{n}"].error
        use = results[f"use{n}"]
        assert not use.ok, (n, use.speech)
        assert use.error is not None
        assert "undefined control sequence" in use.error.lower()
    # Same answer when the using items run alone: results do not depend on batch order.
    alone = verbalize([i for i in items if i.id.startswith("use")])
    assert [r.error for r in alone] == [results[r.id].error for r in alone]


def test_labels_and_tags_do_not_collide_between_items() -> None:
    tex = r"\begin{equation} a = b \label{eq:one} \tag{1} \end{equation}"
    results = verbalize([MathItem(id=str(n), tex=tex, display=True) for n in range(3)])
    assert all(r.ok for r in results), [r.error for r in results]
    assert len({r.mathml for r in results}) == 1


def test_large_batch_keeps_order() -> None:
    items = [MathItem(id=f"i{n}", tex=f"x_{{{n}}} + {n}") for n in range(300)]
    results = verbalize(items)
    assert [r.id for r in results] == [i.id for i in items]
    for n, result in enumerate(results):
        assert result.ok, result.error
        assert result.speech is not None
        assert str(n) in result.speech.clearspeak


def test_oversized_items_fail_fast_and_keep_neighbours() -> None:
    items = [
        MathItem(id="before", tex="a + b"),
        MathItem(id="long", tex="+".join("a" * 5000)),
        MathItem(id="mid", tex="c"),
        MathItem(id="dense", tex=r"\begin{pmatrix}" + r"\\".join(["a&" * 60 + "a"] * 40) + "}"),
        MathItem(
            id="big", tex=r"\begin{pmatrix}" + r"\\".join(["a&" * 30 + "a"] * 60) + r"\end{pmatrix}"
        ),
        MathItem(id="after", tex="d"),
    ]
    started = time.monotonic()
    results = {r.id: r for r in verbalize(items)}
    assert time.monotonic() - started < 30
    for key in ("before", "mid", "after"):
        assert results[key].ok, results[key].error
    for key, word in (("long", "too long"), ("dense", ""), ("big", "too large")):
        bad = results[key]
        assert not bad.ok
        assert bad.error is not None
        assert word in bad.error
        assert len(bad.error) < 400


def test_real_slow_formula_times_out_alone() -> None:
    # SRE's MathSpeak rules take several seconds on a flat sum of 150 subscripted terms.
    slow = "+".join(f"x_{{{n}}}" for n in range(150))
    items = [MathItem(id="a", tex="x"), MathItem(id="slow", tex=slow), MathItem(id="c", tex="y")]
    before, timed_out, after = verbalize(items, item_timeout_s=1.0)
    assert before.ok
    assert after.ok
    assert not timed_out.ok
    assert timed_out.error is not None
    assert "timed out" in timed_out.error


def test_error_messages_are_short() -> None:
    (result,) = verbalize([MathItem(id="e", tex="\\" + "q" * 3000 + " x")])
    assert not result.ok
    assert result.error is not None
    assert len(result.error) < 400


FAKE_BRIDGE = """
import { writeSync } from 'node:fs';
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
for (const line of Buffer.concat(chunks).toString('utf8').split('\\n')) {
  if (line === '') continue;
  const { id, tex } = JSON.parse(line);
  if (tex === 'SLOW') for (;;) {}
  const speech = { clearspeak: tex, mathspeak: tex };
  writeSync(1, JSON.stringify({ id, ok: true, mathml: '<math/>', speech, error: null }) + '\\n');
}
"""


@pytest.fixture
def fake_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "fake.mjs"
    script.write_text(FAKE_BRIDGE, encoding="utf-8")
    monkeypatch.setattr(mathspeak, "SCRIPT", script)
    monkeypatch.setattr(mathspeak, "STARTUP_GRACE_S", 2.0)


@pytest.mark.usefixtures("fake_bridge")
def test_slow_items_time_out_alone() -> None:
    texes = ["a", "SLOW", "b", "c", "SLOW", "SLOW", "d"]
    items = [MathItem(id=str(n), tex=tex) for n, tex in enumerate(texes)]
    results = verbalize(items, item_timeout_s=0.3)
    assert [r.id for r in results] == [i.id for i in items]
    for item, result in zip(items, results, strict=True):
        if item.tex == "SLOW":
            assert not result.ok
            assert result.error is not None
            assert "timed out" in result.error
        else:
            assert result.ok, result.error
            assert result.speech is not None
            assert result.speech.clearspeak == item.tex


@pytest.mark.usefixtures("fake_bridge")
def test_total_timeout_raises() -> None:
    items = [MathItem(id="0", tex="a"), MathItem(id="1", tex="SLOW")]
    with pytest.raises(MathSpeechError, match="exceeded"):
        verbalize(items, timeout_s=1.0, item_timeout_s=30.0)


def test_cli_accepts_bom_and_crlf() -> None:
    out = _cli(b'\xef\xbb\xbf{"id":"bom","tex":"x"}\r\n\r\n{"id":"b","tex":"y"}')
    assert [(r["id"], r["ok"]) for r in out] == [("bom", True), ("b", True)]


def test_cli_validates_field_types() -> None:
    lines = [
        {"id": 5, "tex": "x"},
        {"tex": "x"},
        {"id": "d", "tex": "x", "display": "true"},
        {"id": "t", "tex": 3},
        {"id": "good", "tex": "x", "display": True},
    ]
    stdin = "".join(json.dumps(line) + "\n" for line in lines) + "not json\n[1]\n"
    out = _cli(stdin.encode())
    assert [r["id"] for r in out] == [None, None, "d", "t", "good", None, None]
    assert [r["ok"] for r in out] == [False, False, False, False, True, False, False]
    assert all(r["error"] for r in out if not r["ok"])


def test_bad_line_fails_only_its_own_item(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the CLI to see a line it cannot read an id from, in the middle of a batch.
    real_dumps = json.dumps

    def dumps(obj: dict[str, object], *, ensure_ascii: bool = True) -> str:
        if obj.get("id") == "bad":
            return "{broken"
        return real_dumps(obj, ensure_ascii=ensure_ascii)

    monkeypatch.setattr(mathspeak.json, "dumps", dumps)
    results = verbalize([MathItem(id=key, tex="x") for key in ("a", "bad", "c")])
    assert [(r.id, r.ok) for r in results] == [("a", True), ("bad", False), ("c", True)]
    assert results[1].error is not None
    assert "json" in results[1].error.lower()


def test_wrapping_math_delimiters_are_stripped() -> None:
    texes = ["$x^2$", "$$x^2$$", r"\(x^2\)", r"\[x^2\]", " $ x^2 $ "]
    results = verbalize([MathItem(id=str(n), tex=tex) for n, tex in enumerate(texes)])
    for result in results:
        assert result.ok, result.error
        assert result.speech is not None
        assert result.speech.clearspeak.lower() == "x squared"


def test_stray_dollar_is_rejected_but_escaped_dollar_is_read() -> None:
    stray, escaped = verbalize(
        [MathItem(id="s", tex="$a$ + $b$"), MathItem(id="e", tex=r"\$ 5 + \text{is \$3}")]
    )
    assert not stray.ok
    assert stray.error is not None
    assert "delimiter" in stray.error
    assert escaped.ok, escaped.error
    assert escaped.speech is not None
    assert "dollar" in escaped.speech.clearspeak.lower()
    assert "$" not in escaped.speech.clearspeak + escaped.speech.mathspeak


def test_unresolved_reference_is_an_error() -> None:
    results = verbalize(
        [MathItem(id="r", tex=r"x \text{ by } \eqref{nothing}"), MathItem(id="q", tex="a ??? b")]
    )
    assert not results[0].ok
    assert results[0].error is not None
    assert "unresolved reference" in results[0].error
    assert results[1].ok or "reference" not in (results[1].error or "")


@pytest.mark.parametrize("tex", [r"\ ", r"\quad", "{}", r"\phantom{x}", chr(0xFEFF), "$$"])
def test_unspeakable_math_has_one_message(tex: str) -> None:
    (result,) = verbalize([MathItem(id="e", tex=tex)])
    assert not result.ok
    assert result.error is not None
    assert result.error in {
        "formula has no speakable content",
        '"tex" must be a non-empty string',
    }


def test_zero_width_characters_are_not_read() -> None:
    tex = "x" + chr(0xFEFF) + " + " + chr(0x200B) + "y"
    (result,) = verbalize([MathItem(id="z", tex=tex)])
    assert result.ok, result.error
    assert result.speech is not None
    assert result.speech.clearspeak.lower() == "x plus y"
    assert result.speech.mathspeak.lower() == "x plus y"


def test_common_paper_macros_are_accepted() -> None:
    texes = {
        "bm": r"\bm{x} + 1",
        "ensuremath": r"\ensuremath{x + 1}",
        "color": r"\textcolor{red}{x} + {\color{blue} 1}",
        "nicefrac": r"\nicefrac{1}{2}",
        "href": r"\href{https://example.org}{x}",
        "newcommand": r"\newcommand{\vv}[1]{\mathbf{#1}} \vv{a} + 1",
    }
    results = verbalize([MathItem(id=key, tex=tex) for key, tex in texes.items()])
    for result in results:
        assert result.ok, (result.id, result.error)
        speech = result.speech
        assert speech is not None
        assert not FORBIDDEN & set(speech.clearspeak + speech.mathspeak), result.id
    by_id = {r.id: r for r in results}
    bold = by_id["bm"].speech
    assert bold is not None
    assert "bold" in bold.clearspeak.lower()


def test_recursive_macro_is_an_error() -> None:
    before, loop, after = verbalize(
        [
            MathItem(id="a", tex="x"),
            MathItem(id="loop", tex=r"\def\a{\a\a}\a"),
            MathItem(id="c", tex="y"),
        ]
    )
    assert before.ok
    assert after.ok
    assert not loop.ok
