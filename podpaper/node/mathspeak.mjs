#!/usr/bin/env node
// Batch CLI: LaTeX -> MathML (MathJax 4) -> rule-based speech (Speech Rule Engine).
//
// stdin : JSON Lines, one {"id": string, "tex": string, "display"?: boolean} per line.
//         Lines end with "\n" (an optional "\r" before it is dropped). Blank lines are skipped.
// stdout: one JSON line per non-blank input line, in input order, written as soon as that
//         item is finished:
//         {"id", "ok", "mathml", "speech": {"clearspeak", "mathspeak"}, "error"}
//         Output is pure ASCII (everything else is \uXXXX-escaped), so "\n" is the only
//         line break a consumer can ever see.
//
// A bad item (invalid JSON, wrong field types, TeX parse error, oversized formula, speech
// failure) yields ok=false with a short message. It never aborts the batch. "id" is echoed
// when it is a string and is null otherwise; results are positional, so callers should
// match by line number, not by id.
//
// Every item gets its own TeX parser, so nothing defined in one item (\newcommand, \def,
// \DeclareMathOperator, labels, tags) is visible to another. Nothing is fetched at run
// time: MathJax is imported from node_modules and SRE reads its English rule files from
// node_modules/speech-rule-engine/lib/mathmaps (see docs/adr/0002-mathjax-sre-bridge.md).
//
// A formula that is slow inside SRE cannot be interrupted from here (SRE is synchronous).
// The size limits below keep that rare; the Python wrapper adds a per-item watchdog.

import { existsSync, writeSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

import { liteAdaptor } from '@mathjax/src/js/adaptors/liteAdaptor.js';
import { STATE } from '@mathjax/src/js/core/MathItem.js';
import { SerializedMmlVisitor } from '@mathjax/src/js/core/MmlTree/SerializedMmlVisitor.js';
import { RegisterHTMLHandler } from '@mathjax/src/js/handlers/html.js';
import { TeX } from '@mathjax/src/js/input/tex.js';
import '@mathjax/src/js/input/tex/ams/AmsConfiguration.js';
import '@mathjax/src/js/input/tex/base/BaseConfiguration.js';
import '@mathjax/src/js/input/tex/boldsymbol/BoldsymbolConfiguration.js';
import '@mathjax/src/js/input/tex/braket/BraketConfiguration.js';
import '@mathjax/src/js/input/tex/cancel/CancelConfiguration.js';
import '@mathjax/src/js/input/tex/color/ColorConfiguration.js';
import '@mathjax/src/js/input/tex/configmacros/ConfigMacrosConfiguration.js';
import '@mathjax/src/js/input/tex/html/HtmlConfiguration.js';
import '@mathjax/src/js/input/tex/mathtools/MathtoolsConfiguration.js';
import '@mathjax/src/js/input/tex/newcommand/NewcommandConfiguration.js';
import '@mathjax/src/js/input/tex/textmacros/TextMacrosConfiguration.js';
import '@mathjax/src/js/input/tex/units/UnitsConfiguration.js';
import { mathjax } from '@mathjax/src/js/mathjax.js';

// No "noundefined"/"noerrors": they would hide parse errors instead of reporting them.
// "newcommand" is safe because the parser is rebuilt for every item.
const TEX_PACKAGES = [
  'base',
  'ams',
  'boldsymbol',
  'braket',
  'cancel',
  'color',
  'configmacros',
  'html',
  'mathtools',
  'newcommand',
  'textmacros',
  'units',
];
// Aliases for common paper macros whose LaTeX packages MathJax does not ship.
const TEX_MACROS = {
  bm: ['\\boldsymbol{#1}', 1],
  ensuremath: ['#1', 1],
};
const LOCALE = 'en';
const DOMAINS = ['clearspeak', 'mathspeak'];

// Size limits. Ordinary formulas are far below them (a 20-line aligned block is about 2600
// characters and 1100 MathML elements and takes about 0.25 s).
const MAX_TEX_CHARS = 4000;
const MAX_MATHML_ELEMENTS = 2000;
const MAX_ERROR_CHARS = 300;
const NO_SPEECH = 'formula has no speakable content';

// --- SRE: load the CommonJS bundle and point it at the local rule files -----------------
const require = createRequire(import.meta.url);
const sreDir = path.dirname(require.resolve('speech-rule-engine/package.json'));
const mathmaps = path.join(sreDir, 'lib', 'mathmaps');
if (!existsSync(path.join(mathmaps, `${LOCALE}.json`))) {
  process.stderr.write(`mathspeak: SRE locale file missing: ${mathmaps}/${LOCALE}.json\n`);
  process.exit(2);
}
// Must be set before the bundle is evaluated: SRE reads it once at load time. With the path
// set, SRE's Node loader reads the locale with fs and never falls back to its CDN URL.
process.env.SRE_JSON_PATH = mathmaps;
const sre = require('speech-rule-engine/lib/sre.js');

// Switching rule sets is cheap once the locale is loaded (about 0.3 ms per item measured).
async function setDomain(domain) {
  await sre.setupEngine({
    locale: LOCALE,
    domain,
    style: 'default',
    modality: 'speech',
    markup: 'none',
    speech: 'none',
  });
  await sre.engineReady();
}

// --- MathJax: TeX -> MathML ---------------------------------------------------------------
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const visitor = new SerializedMmlVisitor();

class ItemError extends Error {}

// Remove characters that carry no math and that SRE would read as "empty": zero-width
// characters and the BOM are dropped, Unicode line breaks become a space.
function cleanTex(source) {
  return source
    .replace(/[\u200b-\u200d\u2060\ufeff]/g, '')
    .replace(/[\u0085\u2028\u2029]/g, ' ')
    .trim();
}

// Strip one pair of math delimiters wrapping the whole formula: $...$, $$...$$, \(...\),
// \[...\]. Only when the pair really encloses everything ("$a$ + $b$" is left alone).
function stripDelimiters(source) {
  const pairs = [
    ['$$', '$$'],
    ['$', '$'],
    ['\\(', '\\)'],
    ['\\[', '\\]'],
  ];
  for (const [open, close] of pairs) {
    if (
      source.length >= open.length + close.length &&
      source.startsWith(open) &&
      source.endsWith(close)
    ) {
      const inner = source.slice(open.length, source.length - close.length);
      const escapedClose = inner.endsWith('\\') && !inner.endsWith('\\\\');
      const nested =
        open === '$' || open === '$$'
          ? /(^|[^\\])\$/.test(inner)
          : inner.includes(open) || inner.includes(close);
      if (!escapedClose && !nested) return inner.trim();
    }
  }
  return source;
}

function texToMathml(source, display) {
  // A new input jax and document per item: macro tables, labels and equation numbers
  // belong to the jax, so this is what keeps items independent (about 0.3 ms each).
  const tex = new TeX({
    packages: TEX_PACKAGES,
    macros: TEX_MACROS,
    formatError: (_jax, err) => {
      throw err;
    },
  });
  const doc = mathjax.document('', { InputJax: tex });
  const node = doc.convert(source, { display, end: STATE.CONVERT });
  const mathml = visitor.visitTree(node);
  if (/<merror[\s>]/.test(mathml)) {
    const text = mathml.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    throw new Error(`MathJax produced an error node: ${text}`);
  }
  return mathml;
}

function message(err) {
  const text = (err && err.message ? String(err.message) : String(err)) || 'unknown error';
  const flat = text.replace(/\s+/g, ' ').trim();
  return flat.length > MAX_ERROR_CHARS ? `${flat.slice(0, MAX_ERROR_CHARS)}...` : flat;
}

async function processLine(line) {
  const out = { id: null, ok: false, mathml: null, speech: null, error: null };
  let item;
  try {
    item = JSON.parse(line);
  } catch (err) {
    out.error = `invalid JSON input line: ${message(err)}`;
    return out;
  }
  if (item === null || typeof item !== 'object' || Array.isArray(item)) {
    out.error = 'input line is not a JSON object';
    return out;
  }
  if (typeof item.id !== 'string') {
    out.error = '"id" must be a string';
    return out;
  }
  out.id = item.id;
  if (item.display !== undefined && typeof item.display !== 'boolean') {
    out.error = '"display" must be a boolean when present';
    return out;
  }
  if (typeof item.tex !== 'string') {
    out.error = '"tex" must be a string';
    return out;
  }
  if (item.tex.length > MAX_TEX_CHARS) {
    out.error = `formula too long: ${item.tex.length} characters (limit ${MAX_TEX_CHARS})`;
    return out;
  }
  const source = stripDelimiters(cleanTex(item.tex));
  if (source === '') {
    out.error = '"tex" must be a non-empty string';
    return out;
  }

  let mathml;
  try {
    mathml = texToMathml(source, item.display === true);
  } catch (err) {
    out.error = `TeX parse error: ${message(err)}`;
    return out;
  }
  const elements = (mathml.match(/<m[a-z]+[\s>]/g) ?? []).length;
  if (elements > MAX_MATHML_ELEMENTS) {
    out.error = `formula too large: ${elements} MathML elements (limit ${MAX_MATHML_ELEMENTS})`;
    return out;
  }
  // An unescaped "$" that survived delimiter stripping is markup, not math ("\$" is fine).
  if (/<m[a-z]+ data-latex="\$"/.test(mathml)) {
    out.error = 'stray "$" math delimiter in formula';
    return out;
  }
  // \ref and \eqref cannot resolve here (each item is parsed alone); MathJax renders them
  // as "???", which must not be read aloud. The caller has to substitute the number.
  if (/<mtext[^>]*>[^<]*\?\?\?/.test(mathml) && /\\(eq)?ref\b/.test(source)) {
    out.error = 'unresolved reference: replace \\ref and \\eqref with their text before conversion';
    return out;
  }

  const speech = {};
  for (const domain of DOMAINS) {
    try {
      await setDomain(domain);
      const raw = sre.toSpeech(mathml);
      const text = typeof raw === 'string' ? raw.replace(/\s+/g, ' ').trim() : '';
      // ClearSpeak says "empty" for math that is only space; MathSpeak says nothing.
      if (text === '' || text === 'empty') throw new ItemError(NO_SPEECH);
      speech[domain] = text;
    } catch (err) {
      out.error = err instanceof ItemError ? err.message : `speech error (${domain}): ${message(err)}`;
      return out;
    }
  }
  out.ok = true;
  out.mathml = mathml;
  out.speech = speech;
  return out;
}

// Synchronous write to fd 1, so a line is out of the process before the next (possibly
// slow) item starts. process.stdout is never touched, which leaves the descriptor blocking.
function emit(result) {
  const json = JSON.stringify(result).replace(
    /[\u007f-\uffff]/g,
    (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`,
  );
  const data = Buffer.from(`${json}\n`, 'ascii');
  let offset = 0;
  while (offset < data.length) {
    try {
      offset += writeSync(1, data, offset);
    } catch (err) {
      if (err.code !== 'EAGAIN') throw err;
    }
  }
}

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  let input = Buffer.concat(chunks).toString('utf8');
  if (input.startsWith('\ufeff')) input = input.slice(1);

  // Split on "\n" only: U+2028, U+2029 and U+0085 are legal inside JSON strings.
  for (let line of input.split('\n')) {
    if (line.endsWith('\r')) line = line.slice(0, -1);
    if (line.trim() === '') continue;
    let result;
    try {
      result = await processLine(line);
    } catch (err) {
      result = { id: null, ok: false, mathml: null, speech: null, error: message(err) };
    }
    emit(result);
  }
}

main().catch((err) => {
  process.stderr.write(`mathspeak: fatal: ${err && err.stack ? err.stack : err}\n`);
  process.exit(1);
});
