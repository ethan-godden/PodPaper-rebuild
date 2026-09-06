# ADR 0002: MathJax 4 and SRE bridge for rule-based math speech

Status: accepted for M0 (provisional; the M1 spike "MathJax/SRE engine choice" closes it)
Date: 2026-11-23

## Context

The plan calls for "a Node batch CLI wrapping MathJax and the Speech Rule Engine (SRE) for
LaTeX to MathML to rule-based speech". Literal readings (L3 ClearSpeak style, L4 MathSpeak
style) always come from SRE, and the SRE reading is the fallback for every other level, so
this bridge must never crash and must never need the network.

npm registry state on 2026-11-23:

| Package | `latest` | Notes |
|---|---|---|
| `@mathjax/src` | 4.1.3 | MathJax 4 source and components; depends on `speech-rule-engine` exactly `5.0.0-rc.4` |
| `mathjax` | 4.1.3 | Bundled components only (browser-oriented), depends on the font package |
| `speech-rule-engine` | 4.1.5 | `latest`; 5.x exists only as alpha, beta and rc builds (`5.0.0-rc.4` has no dist-tag) |
| `mathjax-full` | 3.2.2 | MathJax 3 line, not used |

So there are two candidate speech engines: the SRE 5 release candidate that MathJax 4 ships
with, or the stable standalone SRE 4.1.5.

## Decision

1. LaTeX to MathML: `@mathjax/src` 4.1.3, used as a library (TeX input jax, lite adaptor,
   `SerializedMmlVisitor`). No output jax and no fonts are loaded.
2. Speech: **SRE 5.0.0-rc.4, the exact build MathJax 4.1.3 depends on**, called directly
   through its own Node API (`setupEngine`, `engineReady`, `toSpeech`) on the MathML string
   that MathJax produced. It is listed as a direct dependency with the same exact version,
   so npm installs one copy shared with MathJax.
3. Speech is **not** produced through MathJax's own a11y pipeline (`a11y/semantic-enrich`,
   `a11y/speech`). In MathJax 4 that pipeline generates speech in a worker and attaches it
   to rendered output for the explorer; it is built for pages, not for batch text output.
   Calling SRE directly gives the same engine and rule sets with a synchronous call.
4. Standalone SRE 4.1.5 is not used. Reasons: one SRE version in the tree instead of two;
   the readings match what MathJax 4 itself would say; MathJax 4 emits MathML that SRE 5 is
   developed against; SRE 4 is in maintenance. The cost is depending on a release
   candidate. Both versions are pinned exactly in `package.json` and `package-lock.json`,
   and switching engines is a one-line change in `mathspeak.mjs` plus the version pin.

Both packages are Apache-2.0.

### Offline behaviour

SRE loads its locale rules (`base.json`, `en.json`) lazily. In Node it reads them with `fs`
from the directory in `SRE_JSON_PATH`; only its browser and worker modes use the jsDelivr
URL in `Variables.url`. `mathspeak.mjs` resolves
`node_modules/speech-rule-engine/lib/mathmaps`, checks that `en.json` exists, and sets
`process.env.SRE_JSON_PATH` before loading the SRE CommonJS bundle (`lib/sre.js`), so the
path never depends on the working directory or on SRE's fallback guesses. Verified by
running the CLI under `node --permission --allow-fs-read='*'`, which denies all network
access: output is identical.

### Contract

`podpaper/node/mathspeak.mjs` reads JSON Lines on stdin (`{"id", "tex", "display"}`) and
writes one JSON line per non-blank input line, in order, as soon as each item is finished:
`{"id", "ok", "mathml", "speech": {"clearspeak", "mathspeak"}, "error"}`.

Framing:

- Input lines are split on `\n` only (a `\r` before it and a leading UTF-8 BOM are
  dropped). Node `readline` is not used because it also splits on U+2028 and U+2029, which
  are legal inside JSON strings and do occur in PDF-extracted text.
- Output is pure ASCII: every other character is written as a `\uXXXX` escape, so a
  consumer can never see a line break other than `\n`. The Python side sends ASCII-escaped
  JSON as well and splits the output on `b"\n"`, not with `str.splitlines()`.
- Results are positional. `id` is echoed when it is a string and is `null` when the line
  could not be read that far; `verbalize()` matches by position and turns such a line into
  a failure of that one item. Duplicate ids are allowed for the same reason.

Validation, each giving `ok=false` for that item only:

- Invalid JSON, a non-object line, a non-string `id` or `tex`, a non-boolean `display`.
- `tex` longer than 4000 characters, or MathML with more than 2000 elements. A 20-line
  aligned block is about 2600 characters and 1100 elements, so real formulas pass.
- A TeX error. MathJax's `formatError` is overridden to throw, so no `merror` node is
  produced silently; a remaining `merror` is also treated as an error. The `noerrors` and
  `noundefined` packages are deliberately not loaded: an undefined macro is an error, not
  red text that would be read aloud.
- An unresolved `\ref` or `\eqref` (MathJax renders it as "???"). References cannot
  resolve when each formula is parsed alone, so the pipeline must substitute the number or
  text before calling the bridge.
- An unescaped `$` left inside the formula (`\$` is read as "dollar").
- Math with nothing to say (`{}`, `\quad`, `\phantom{x}`): one message for both rule sets,
  "formula has no speakable content".
- Error messages are cut to 300 characters; SRE otherwise embeds the whole MathML.

Normalisation before parsing: zero-width characters and the BOM are removed, U+0085,
U+2028 and U+2029 become a space, and one pair of delimiters wrapping the whole formula
(`$...$`, `$$...$$`, `\(...\)`, `\[...\]`) is stripped. The `display` flag is not changed
by the delimiter that was stripped.

Isolation between items: a new TeX input jax and document are built for every item (about
0.3 ms). Macro tables, labels and equation numbers live in the jax, so nothing defined in
one item (`\newcommand`, `\def`, `\let`, `\newenvironment`, `\DeclareMathOperator`,
`\DeclarePairedDelimiter`, `\label`, `\tag`) is visible in another, and a result does not
depend on batch order. That is what makes a per-formula cache valid. Because of it the
`newcommand` package is now loaded: definitions inside one item work for that item.
Recursive definitions end in MathJax's macro substitution limit, as an ordinary error.

TeX packages loaded: base, ams, boldsymbol, braket, cancel, color, configmacros, html,
mathtools, newcommand, textmacros, units. Two aliases are configured: `\bm` (to
`\boldsymbol`) and `\ensuremath` (to its argument).

SRE: locale `en`, style `default`, markup `none`; the rule set is switched per item
(ClearSpeak, then MathSpeak), which costs about 0.3 ms once the locale is loaded.

Slow formulas: SRE is synchronous and cannot be interrupted inside the Node process. Its
MathSpeak rule set is roughly quartic in the number of subscripted terms of a flat sum
(100 terms 1.1 s, 150 terms 5.5 s, 200 terms 16 s; ClearSpeak stays under 0.1 s). The size
limits do not catch that case, so `verbalize()` watches the output: if an item's line does
not arrive within `item_timeout_s` (default 10 s, plus 10 s for process start-up on the
first item), the process is killed, that item is returned with `ok=False` and a "timed out"
error, and the remaining items run in a new process. The direct CLI has no such watchdog.

`podpaper/speech/mathspeak.py` exposes
`verbalize(items, *, timeout_s=600, item_timeout_s=10) -> list[MathSpeech]`. It raises
`MathSpeechError` if `node` or `node_modules` is missing (the message says to run `npm ci`
in `podpaper/node`), if the bridge exits non-zero or breaks the contract, or if the whole
call exceeds `timeout_s`.

### Measured on the M3 Max (Node 26.13.1)

- Cold start plus 13 items: about 0.25 s wall.
- 500 sum-and-fraction items in one batch through `verbalize`: about 1.8 s wall with the
  first version; 300 short items take about 0.7 s with a parser per item and per-item rule
  set switching.
- `node_modules` is about 113 MB (mostly `@mathjax/src`, which ships ts, mjs, cjs and
  bundles).

## Consequences and known limits

- The MathML carries MathJax's `data-latex` and `data-mjx-*` attributes. They are harmless
  for speech but must be stripped before the S4 MathML agreement check (canonicalisation is
  not part of this bridge yet).
- Readings observed that later stages must handle:
  - Upright capital Greek from MathJax (`mathvariant="normal"`) is read "normal Gamma".
  - ClearSpeak reads `\cdot` between a bare operator and a vector as "times"
    ("nabla times bold E"); MathSpeak says "dot".
  - MathSpeak uses its markers ("StartFraction", "Subscript", "Baseline", "upper E").
    That is the literal L4 style by design.
- ClearSpeak reads an explicit space (`x \ y`) as "x empty y"; MathSpeak skips it.
- Document-level macros from the paper preamble are not supported yet: a formula may only
  use macros it defines itself.
- Still hard errors on real papers: `\require{...}`, `\mathtoolsset` options MathJax does
  not know (for example `showonlyrefs`), two equation environments in one item
  ("Erroneous nesting of equation structures"), and macros from packages that are not
  loaded (physics, mhchem, upgreek, siunitx, bbm, dsfont).
- A slow formula costs up to `item_timeout_s` and one process restart before it is
  reported; the cause inside SRE's MathSpeak rules has not been investigated.

## Remaining for the M1 spike

1. Compare SRE 5.0.0-rc.4 against standalone 4.1.5 on a sample of real equations from the
   fixtures (crashes, empty readings, reading differences) and record numbers. Go, or fall
   back to 4.1.5 for speech while keeping MathJax 4 for parsing.
2. Decide which engine owns the semantic tree (SRE `toSemantic` / `toEnriched`) needed by
   the verifier and the complexity threshold, and add it to the output contract.
3. Add canonical MathML output (attribute stripping, stable serialisation) for S4.
4. Choose ClearSpeak preferences and the MathSpeak style (default, brief, sbrief), and
   decide how to handle "normal" on upright Greek (TeX-side `mathStyle` or a rule
   preference).
5. Paper-level macro support: pass the preamble definitions explicitly with each item (or
   once per batch as a declared macro context that is part of the cache key), never as
   state left over from earlier items. Decide which further TeX packages real papers need
   (mhchem, physics, upgreek, siunitx-style units, bbm, dsfont), count the
   "Undefined control sequence" failures on the fixtures, and decide what to do with
   `\require`, unknown `\mathtoolsset` options and items holding several equation
   environments (split upstream or reject).
6. Find the cause of the MathSpeak slowdown on long flat sums (report upstream if it is an
   SRE 5 regression; compare with 4.1.5) and revisit the size limits and the 10 s watchdog
   with numbers from real papers.
7. Decide how resolved cross-references reach the bridge (`\eqref` replaced by
   "equation 3" text upstream is the current assumption).
8. Decide between one process per batch (current) and a long-lived worker if S7 calls
   become frequent enough for the 0.2 s start-up to matter.
9. Re-check the registry when SRE 5.0.0 final and the next MathJax 4 release land, and
   re-pin both together.
