# ADR 0001: arXiv terms of use and native HTML markup

- Status: Accepted 2026-11-23 (owner decision 3 answered with the default, see ADR 0004; the choice between options (a) and (b) for residual risk R1 is to be confirmed before the first corpus fetch in M4)
- Date: 2026-11-23
- Scope: the data engine corpus (PLAN.md "Data engine", M4 and M7) and the opt-in runtime correction stage S5b

## Context

The plan uses arXiv in two ways.

1. **Training corpus.** Fetch CC-BY and CC0 arXiv papers as PDF plus arXiv's native HTML, parse the HTML into a geometry-free reference PaperDoc, and align it to the PDF to produce training labels. About 400 papers in M4, 3,000 in M7.
2. **Runtime correction (S5b, after v1).** When the user converts a paper whose arXiv ID resolves, optionally fetch its arXiv HTML and use it to correct formula LaTeX and prose.

Both depend on two things the plan marked "verify": whether arXiv's terms allow this automated fetching, and whether the HTML markup is regular enough to parse. This record answers both from primary sources fetched on 2026-11-23. Everything under Findings was read in this session unless it is listed under "Unverified items".

Request budget used for this check: 8 requests to `arxiv.org` (robots.txt, three HTML papers, one abstract page, one build log, one PDF `HEAD`, one full HTML page of an old paper), each at least 15 seconds apart, plus a handful to `info.arxiv.org` (static help pages), `oaipmh.arxiv.org` and `export.arxiv.org/api`. The review of this record fetched one more HTML paper (2611.25152v1), which is used in section 5.

Which document governs what, since the rest of this record depends on it:

- **Website fetches** (`arxiv.org/pdf`, `/html`, `/abs`) are governed by `robots.txt` and the "Robots Beware" help page, and are constrained by the full-content harvesting policy quoted in section 2. No page read grants permission for systematic full-text collection from the website.
- **The API Terms of Use** govern "arXiv APIs", which the ToU lists as OAI-PMH, RSS, the legacy API, bulk data downloads and SWORD. They apply to our metadata harvest and to any bulk-data use. They are not a grant for website fetching; where this record cites them for website fetches it is by analogy only.

## Findings

### 1. robots.txt

`https://arxiv.org/robots.txt` (header comment: "Indiscriminate automated downloads from this site are not permitted"), for `User-agent: *`:

- `Crawl-delay: 15`
- Allowed: `/archive /year /list /abs /pdf /html /catchup`
- Disallowed, among others: `/e-print /src /ps /dvi /format /api /search /oai2 /find /view /ftp /refs /cits /user /auth /form`

So `/abs`, `/pdf` and `/html` may be fetched by a robot at one request per 15 seconds. TeX source (`/e-print`, `/src`) may not be fetched from the website at all; source comes only from bulk data.

`https://export.arxiv.org/robots.txt` is, in full:

```
User-agent: * 
Disallow: /
```

This conflicts with the bulk-data help page, which asks harvesters to use `export.arxiv.org` (see below). The two statements cannot both be followed for `/pdf` and `/html`, so the policy in this ADR takes the stricter reading and does not fetch papers from the mirror.

The "Robots Beware" page adds: arXiv monitors activity and denies access to violators; continued requests after a `403` are treated as an attack; anyone needing relaxed limits must contact arXiv in advance. It also steers automated users away from the website: "Several interfaces designed to provide machine access to arXiv are provided. See our OAI-PMH, arXiv API and RSS documentation."

### 2. API terms of use and bulk-data guidance

Terms of Use for arXiv APIs (`info.arxiv.org/help/api/tou.html`). Scope, in its words: "Our APIs include our OAI-PMH interface, RSS feeds, the legacy arXiv API, bulk data downloads, and SWORD bulk deposit API ... By using arXiv APIs, you are agreeing to the terms and conditions outlined on this page." Website page fetches are not in that list.

- Rate limit for the legacy APIs (OAI-PMH, RSS, arXiv API): at most one request every three seconds, one connection at a time, counted across all machines under one's control.
- Allowed: "Retrieve, store, transform, and share descriptive metadata"; "Retrieve, store, and use the content of arXiv e-prints for your own personal use, or for research purposes."
- Not allowed: "Store and serve arXiv e-prints (PDFs, source files, or other content) from your servers, unless you have the permission of the copyright holder or are permitted to do so by the license with which the e-print was submitted"; circumventing rate limits; claiming arXiv endorsement.
- Metadata (title, abstract, authors, identifiers, categories) is CC0.

Bulk Data Access (`info.arxiv.org/help/bulk_data.html`):

- Metadata: OAI-PMH is the preferred bulk route.
- Full text: Kaggle dataset and Amazon S3. "Please do not attempt to download the complete corpus programmatically. The Amazon S3 buckets are the accepted mechanism to download the complete corpus, but you are welcome to \"play catch-up\" programmatically between updates of the buckets." The catch-up sentence is the closest thing found to permission for programmatic fetching of recent papers, and it is framed as a supplement to a bulk download, not as a stand-alone route.
- "If you build indexes or tools based on the full-text, you must link back to arXiv for downloads."
- "A small fraction of submissions are made with other licenses and this information is available in the OAI-PMH metadata."
- "Custom programmatic harvesting": asks harvesters to use `export.arxiv.org` and suggests "bursts at 4 requests per second with a 1 second sleep, per burst". This is the only harvesting guidance on the page. It is looser than robots.txt and contradicted by the mirror's own robots.txt; we do not rely on it.

Full-content harvesting policy. The OAI-PMH `Identify` response (`oaipmh.arxiv.org/oai?verb=Identify`) says "Metadata harvesting permitted through OAI interface" and "Full-content harvesting not permitted (except by special arrangement)". The linked page (`info.arxiv.org/help/oa/dataPolicy.html`) reads in full: "Full-content harvesting from arXiv.org is not permitted except by special arrangement. Bulk downloads for certain purposes are supported." It gives no size threshold and does not define "harvesting".

Amazon S3 (`info.arxiv.org/help/bulk_data_s3.html`): requester-pays bucket `s3://arxiv` in us-east-1 with `pdf/arXiv_pdf_YYMM_NNN.tar` and `src/arXiv_src_YYMM_NNN.tar` chunks of about 500 MB and XML manifests; about 9.2 TB in total as of April 2025; updated roughly monthly. **Only PDF and source are documented. HTML is not offered in bulk** on any page read.

Kaggle (`Cornell-University/arxiv`, metadata API read in this session): dataset licence CC0 for the metadata; its description states the full PDF set is free in the Google Cloud Storage bucket `gs://arxiv-dataset`. The description's `gsutil` examples mention PDFs and, in one comment, "source files"; the bucket was not listed, so its exact contents are unverified. HTML is not mentioned.

Reading these together:

- What the sources do say: robots.txt permits robots on `/pdf` and `/html` at one request per 15 seconds, and nothing read forbids a targeted, licence-filtered fetch at that rate. Fetching the corpus wholesale is clearly not allowed.
- What they do not say: no page affirmatively permits systematic full-text collection from `arxiv.org`. The machine interfaces arXiv points to (OAI-PMH, API, RSS, bulk data) do not serve HTML, and the one harvesting route it describes (`export.arxiv.org`) is closed by that host's robots.txt.
- **Unresolved conflict (residual risk R1).** The full-content harvesting policy says harvesting from arXiv.org needs a special arrangement, with no threshold. Whether 800 requests (M4) or 6,000 requests (M7) for specific papers counts as "full-content harvesting" is an interpretation, not something the sources settle. The reading used here is that the policy targets collection of the corpus or large parts of it, and that 3,000 papers (about 0.15% of a corpus arXiv's HTML page describes as over 2 million papers) fetched within robots.txt is not that. arXiv could read it the other way. Section "Decision" makes this part of owner decision 3 and reduces the exposure by taking PDFs from bulk storage.

### 3. How the licence is exposed per paper

- **OAI-PMH** (`https://oaipmh.arxiv.org/oai`, moved from `export.arxiv.org/oai2` in March 2025). Metadata formats `arXiv` and `arXivRaw` both carry one `<license>` element per record. Observed values:

  ```xml
  <id>2611.27969</id> ... <categories>math.NA cs.NA math.AP math.PR</categories>
  <license>http://creativecommons.org/licenses/by/4.0/</license>
  ```

  CC0 appears as `http://creativecommons.org/publicdomain/zero/1.0/`. The filter is an exact match on those two URIs. Other values seen: `.../licenses/by-sa/4.0/`, `.../by-nc-sa/4.0/`, `.../by-nc-nd/4.0/`, `http://arxiv.org/licenses/nonexclusive-distrib/1.0/`.
- One `ListRecords` call (`set=math:math:NA&from=2026-11-20`, 95 records) returned 39 CC-BY, 1 CC0, 41 arXiv non-exclusive, 10 BY-NC-ND, 3 BY-SA, 1 BY-NC-SA: about 42% CC-BY or CC0. This is a weak sample: 95 records modified over three days in one category, selected by modification date, so it includes replacements of older papers (for example 2110.02926 and 2504.07255). It disagrees with arXiv's own statements, which describe the whole corpus: the ToU says "a very small subset of arXiv e-prints are submitted with licenses that permit redistribution" and the bulk-data page says "a small fraction". The likely explanation is that CC licences are much more common among recent submissions than across the corpus since 1991, but that was not measured. Whether 3,000 qualifying papers stratified across fields exist from 2024 onward remains unverified.
- OAI-PMH limits: sets are `group:archive:CATEGORY` (for example `math:math:NA`, `physics:hep-th`); selective harvesting is by record datestamp (last modification), not submission date; only the latest version of each paper is exposed; resumption tokens expire daily. Responses are slow: the 95-record call took 58 seconds, and a wider one (`set=stat`, 5 days) did not answer within 120 seconds.
- OAI-PMH usage guidance (`info.arxiv.org/help/oa/index.html`): "Make requests without a datestamp range (recommended)"; for incremental harvests "from is best taken from the last server response; don't set the until date"; and "Beware: due to bulk updates, some dates contain large numbers of updates."
- **arXiv API** (`export.arxiv.org/api/query`): the Atom entry has no licence field (confirmed on a live response, and stated on the reuse help page). It is not usable for the licence filter. The first call in this session returned `429 Rate exceeded`; a retry minutes later succeeded.
- **Abstract page**: `<div class="abs-license"><a href="http://creativecommons.org/licenses/by/4.0/" ... class="has_license">`.
- **HTML paper page**: every native HTML page carries the licence and the exact version in its page chrome:

  ```html
  <div id="infobox" class="infobox">
    <a id="license-tr" href="https://info.arxiv.org/help/license/index.html#licenses-available">
      License: CC BY 4.0
    </a>
    <div id="watermark-tr">
  arXiv:2611.27969v1 [math.NA] 20 Nov 2026</div>
  </div>
  ```

  The infobox is presumably rendered from the same arXiv metadata that OAI-PMH exposes, so it is not independent evidence of the licence and does not establish the licence of that specific version. Its use is as a fetch-time consistency check: it catches a new version or a licence change between the metadata harvest and the page fetch.
- The licence help page says the licence is chosen per version and is irrevocable, and that "different versions of the work can have different licenses". The metadata exposes a single value with no version attribute.

### 4. What the licences allow for derived datasets

- **CC BY 4.0** (legal code read in this session, Section 3(a)): sharing the material, including in modified form, is allowed for any purpose provided we retain, if supplied with the material, creator identification, a copyright notice, a notice that refers to the licence, a notice that refers to the disclaimer of warranties, and a URI to the material where practicable; indicate that we modified it; and state the licence with its URI. These may be satisfied "in any reasonable manner", including by linking to a resource that holds the information. Any licence we apply to adapted material must not stop recipients from complying with CC BY. Attribution must be removed on the licensor's request where practicable.
- **CC0 1.0**: no conditions (per arXiv's licence page: "distribute, remix, adapt, and build upon the material in any medium or format, with no conditions").
- **Excluded:** BY-SA (share-alike would bind the whole derived dataset), BY-NC-SA, BY-NC-ND, and the arXiv non-exclusive licence (no reuse rights; arXiv states it cannot grant redistribution).
- The right to redistribute comes from the paper's licence, not from arXiv. arXiv's ToU (for content obtained through its APIs and bulk data) defers to that licence for storing and serving content, and the bulk-data page says arXiv itself cannot grant distribution rights. So redistribution of CC-BY and CC0 papers and of labels derived from them is permitted with attribution.

The attribution manifest the plan already calls for satisfies Section 3(a) if each row holds: arXiv ID with version, title, authors, licence URI, source URL (`https://arxiv.org/abs/<id>v<n>`), any copyright notice and warranty-disclaimer notice the paper itself supplies (usually none; record when present), and a note that the content was modified (parsed, aligned, segmented). The source URL also meets the bulk-data page's requirement to link back to arXiv for downloads.

### 5. The native HTML markup

CC BY 4.0 papers inspected (licence per the page infobox; the first three also per OAI-PMH):

| ID | Category | Why chosen | Size | `<math>` count |
|---|---|---|---|---|
| 2611.27433v1 | math.OC | theorems, proofs, algorithm float, tables, SVG figures, footnotes | 1.0 MB | 1,141 |
| 2611.27969v1 | math.NA | amsart-style article: sub-numbered equations, left equation numbers, appendix, PNG subfigures | 1.8 MB | 1,600 |
| 2610.12336v2 | cs.MS | short pandoc-generated software paper: code, footnotes, untitled table, hand-rolled bibliography | 75 KB | 5 |
| 2611.25152v1 | math.NA | fetched during review of this record: author-year citations, different heading levels, appendix nested in a section | 1.1 MB | 1,099 |

A fifth page, `arxiv.org/html/1706.03762` (served as v7, dated 02 Aug 2023), was fetched in full (188 KB, 142 `<math>` elements) to see whether older papers have HTML. It is under the arXiv non-exclusive licence, not CC BY. It was used only for local inspection, is counted in the math tally below, and must not enter any dataset.

**Sample limits.** Five pages, one generator version. The four CC-BY papers are three mathematics papers from one week of listings (math.OC, two math.NA) and one pandoc-generated software paper; the fifth is a single-column machine-learning paper. No physics (revtex), two-column CS conference, biology-style or astronomy paper was looked at. The rules below are what these pages show. The fourth paper broke several patterns the first three shared (heading levels, ID shapes, appendix nesting, citation text), so further variation should be expected; variants seen are called out in each paragraph.

**Generator.** All five pages carry the same stamp, and it is not Perl LaTeXML:

```html
<!--Generated by LaTeXML oxide (version 0.7.6) http://dlmf.nist.gov/LaTeXML/.-->
```

The build log confirms `latexml_oxide (latexml-oxide 0.7.6; revision 1ef264a2bb)`. This is `dginev/latexml-oxide`, a Rust port of LaTeXML (CC0-1.0), whose README says it is used for production arXiv HTML and is in public beta as of July 2026. The output keeps LaTeXML's `ltx_*` class vocabulary and ID scheme. The HTML for 1706.03762v7 (a version dated August 2023) has `last-modified: Mon, 24 Aug 2026`, so it was generated or regenerated then. arXiv's accessible-HTML page gives the documented reason old papers have HTML: "We are gradually backfilling HTML for arXiv's corpus of over 2 million papers over time." One header cannot distinguish a first-time backfill from a re-conversion, so mutability of the HTML for a fixed paper version is likely (the converter is in beta and old papers are being converted with current builds) but not shown.

**Page skeleton.** Parse only `article.ltx_document`. Everything else is arXiv chrome: site header, `nav.ltx_TOC` (repeats every heading, including math), `div#infobox`, a report-issue dialog, and `footer.arxiv-html-footer`. Unversioned `/html/<id>` returns `200` directly with the latest version; the actual version is in `#watermark-tr` and in links such as `/pdf/2611.27433v1`. Asset URLs are relative to `/html/` and include the version: `2611.27433v1/consensus_formation.svg`.

**IDs.** Unique within a page and usable as link targets, but their shape varies between papers, so the parser must not derive the kind or nesting of an element from its ID. Shapes seen: `S2` section, `S2.SS1` subsection, `S2.SS1.SSS1` subsubsection, `S1.SS0.SSS0.Px1` unnumbered `\paragraph`, `A1` appendix, `Sx1` unnumbered section, `S2.p1` paragraph, `S2.p1.1` its first `<p>`, `S2.E2` numbered equation, `S2.Ex1` unnumbered equation, `S4.EGx1` equation group, `S2.E16X`, `S2.E16Xa`, `S2.E16Xb` lines of a multi-line equation (also `S4.Ex13X`, `S4.Ex13Xa` for unnumbered ones), `S1.E1.1` a sub-numbered line, `S3.F1` figure, `S5.F1.sf1` subfigure, `S3.T1` table, `alg1` algorithm, `alg1.l3` algorithm line, `footnote1`, `bib.bib27` bibliography item, `S2.p1.m4` math. Theorem-like blocks are `S2.Thmtheorem1` when the counter is numbered within sections and `Thmproposition1`, `Thmlemma1` (no section prefix) when it is not. One paper's appendix wrapper had the ID `S6.2` (see below).

**Sections and headings.** `<section>` elements whose class gives the kind (`ltx_section`, `ltx_subsection`, `ltx_subsubsection`, `ltx_paragraph`, `ltx_appendix`, `ltx_bibliography`); the heading is the section's `ltx_title` child and the number sits in a `ltx_tag` span:

```html
<section id="S1.SS1" class="ltx_subsection">
<h3 class="ltx_title ltx_title_subsection"><span class="ltx_tag ltx_tag_subsection">1.1 </span>Notation</h3>
```

Heading levels are not fixed. Four pages used `h1.ltx_title_document`, `h2.ltx_title_section`, `h3.ltx_title_subsection`, `h4.ltx_title_subsubsection`, `h5.ltx_title_paragraph`. The fourth CC-BY paper (2611.25152v1) used `h3` for sections, `h4` for subsections, `h5` for subsubsections and `h6` for `\paragraph`, while its bibliography title stayed `h2`:

```html
<section id="S1" class="ltx_section"><h3 class="ltx_title ltx_title_section">
```

`h6` is also used for abstract, keywords, classification, theorem and proof titles, so in that paper `\paragraph` and theorem titles share a level. Take the kind and depth from the `ltx_title_*` and section classes, never from the `h` level.

Appendices come in at least two forms. The amsart paper has a top-level sibling `<section id="A1" class="ltx_appendix">` with `h2.ltx_title_appendix` and `span.ltx_tag_appendix` ("Appendix A "). The fourth paper has an untitled wrapper nested inside its last numbered section, containing ordinary sections that continue the numbering:

```html
<section id="S6.2" class="ltx_appendix">
<section id="S7" class="ltx_section">
<h3 class="ltx_title ltx_title_section"><span class="ltx_tag ltx_tag_section">7 </span>Auxiliary estimates for the analysis</h3>
```

So DOM nesting of `<section>` elements does not always mirror the logical outline: a `ltx_section` can sit two levels inside another `ltx_section`. Build the outline from the sequence of titled sections and their classes, and treat `section.ltx_appendix` as a marker that what follows is appendix material, whether or not it has a title of its own.

Number punctuation varies by document class ("1 " versus "1. "). Front matter: `div.ltx_authors > span.ltx_creator.ltx_role_author > span.ltx_personname`, `div.ltx_dates`, `div#abstract1.ltx_abstract` (absent in the pandoc paper, which has no abstract block at all), `div.ltx_keywords`, `div.ltx_classification`. Author blocks can contain affiliations, ORCID links and e-mail addresses (`span.ltx_contact.ltx_role_email`); the parser should drop contact details rather than carry them into datasets.

**Paragraphs.** A logical paragraph is `div.ltx_para`. It contains one or more `p.ltx_p` with display equations as sibling `<table>` elements between them, so a sentence that runs through a displayed formula is one `ltx_para` with `p`, `table`, `p`:

```html
<div id="S2.p1" class="ltx_para">
<p id="S2.p1.2" class="ltx_p">...</p>
<table id="S2.Ex1" class="ltx_equation ltx_eqn_table"> ... </table>
<p id="S2.p1.3" class="ltx_p">where <math id="S2.p1.m1" ...>...</math> is a continuous, generally nonconvex function. ...</p>
</div>
```

Inline styling is `span.ltx_text` with `ltx_font_bold`, `ltx_font_italic`, `ltx_font_typewriter`, and `em.ltx_emph`. Lists are `ol.ltx_enumerate` / `ul.ltx_itemize` with `li.ltx_item`, the label in `span.ltx_tag.ltx_tag_item`, and the body again in `div.ltx_para`.

**Math.** Every formula is a `<math>` element with Presentation MathML and the TeX kept twice: in the `alttext` attribute and in an `<annotation encoding="application/x-tex">`. Across all 3,987 `<math>` elements in the five pages (1,141 + 1,600 + 5 + 1,099, plus 142 in the 2017 page), none lacked either, and the two were identical after entity decoding. No Content MathML (`annotation-xml`) and no math rendered as images were present.

```html
<math id="abstract1.m1" class="ltx_Math" alttext="L^{q}(0,T;H^{-1}(D))" display="inline" intent=":literal"><semantics><mrow><msup><mi>L</mi><mi>q</mi></msup><mo lspace="0em" rspace="0em">&#8203;</mo><mrow><mo stretchy="false">(</mo>...</mrow></mrow><annotation encoding="application/x-tex">L^{q}(0,T;H^{-1}(D))</annotation></semantics></math>
```

(The invisible operator between `L^q` and the bracket is shown above as `&#8203;`; in the page it is a literal U+200B zero-width space, not U+2062.) Points the parser must handle:

- The TeX is LaTeXML's normalised re-serialisation, not the author's bytes: braces are added (`x^{*}`), `\displaystyle` is prefixed inside aligned rows, spacing appears as `\kern 5.0pt`. Author macros and package commands survive unexpanded (`\argmin`, `\mathds{N}`, `\lVert`), so the TeX is not guaranteed to compile or to be MathJax-safe without a macro table.
- Attribute values are HTML-escaped (`alttext="T&gt;0"`); decode before use.
- `class="ltx_math_unparsed"` replaces `ltx_Math` when LaTeXML's math grammar failed (27 of 1,141 and 86 of 1,600 in the two math papers, for example `\|\cdot\|`). The element still has MathML and TeX; only the MathML tree is flat. Take TeX from either; do not trust MathML structure on these.
- **Do not use the `display` attribute to tell inline from display math.** Rows of aligned environments carry `display="inline"` with `\displaystyle`. Display math is identified by its container (`table.ltx_equation` or `table.ltx_equationgroup`).
- Text that LaTeX set in math but LaTeXML emitted as text appears as `span.ltx_text.ltx_markedasmath`.

**Display equations and numbers.** A single equation is a one-row table; the number, when present, is in a `td.ltx_eqn_eqno`:

```html
<table id="S2.E2" class="ltx_equation ltx_eqn_table">
<tbody><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
<td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
<td class="ltx_eqn_cell ltx_align_center"><math id="S2.E2.m1" class="ltx_Math" alttext="..." display="block" intent=":literal">...</math></td>
<td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
<td rowspan="1" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equation ltx_align_right">(2)</span></td></tr></tbody>
</table>
```

Display math takes three table shapes. In all of them a line of math is a `tr.ltx_equation.ltx_eqn_row`, with one `<math>` per alignment column (so `a &= b` is two `<math>` elements, the second starting with `\displaystyle=`).

1. **Single equation**: `table.ltx_equation.ltx_eqn_table` with ID `S*.E*` or `S*.Ex*`, one row, as above.
2. **Align-type group of separate equations**: `table.ltx_equationgroup.ltx_eqn_align.ltx_eqn_table`. Here `EGx` is the ID of the group table, and each equation in the group is its own `<tbody>` carrying the equation ID (the ID is on `tbody`, not on `tr`):

   ```html
   <table id="S4.EGx1" class="ltx_equationgroup ltx_eqn_align ltx_eqn_table">
   <tbody id="S4.Ex20"><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
   ```

   Each `tbody` carries its own number, if any, as `span.ltx_tag_equation` in its row. Observed `tbody` IDs here are `S*.E*`, `S*.Ex*`, `S*.Ex*a` and `A*.Ex*`. Every line of the source `align` becomes its own `tbody`, so a continued chain (`a &= b \\ &= c`) appears as consecutive `tbody` elements, the later ones with an empty left cell; whether to join them is a parser decision.
3. **One multi-line equation**: `table.ltx_equationgroup.ltx_eqn_table` (no `ltx_eqn_align`), where the table itself carries the equation ID and the lines carry that ID with an `X`, `Xa`, `Xb`, ... suffix. A numbered one has the suffix IDs on the rows and a single number in a `rowspan` cell tagged `ltx_tag_equationgroup`:

   ```html
   <table id="S2.E16" class="ltx_equationgroup ltx_eqn_table"><tbody>
   <tr id="S2.E16X" class="ltx_equation ltx_eqn_row ltx_align_baseline"> ...
   <td rowspan="3" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equationgroup ltx_align_right">(16)</span></td></tr>
   <tr id="S2.E16Xa" ...> <tr id="S2.E16Xb" ...>
   ```

   An unnumbered one was seen with the suffix IDs on per-line `<tbody>` elements instead (`<table id="S4.Ex13" ...><tbody id="S4.Ex13X"><tr class="ltx_equation ...">`).

Counts of group tables by shape (2) / (3): 38 / 32 in 2611.27433, 58 / 5 in 2611.27969, 6 / 61 in 2611.25152, 2 / 0 in the 2017 page. Both are common, and which dominates depends on the author's choice of environment. For shape (3) the parser must join the lines into one equation with one number; for shape (2) each `tbody` is a separately identified line.

Sub-numbered lines (seen only in the amsart paper, 8 rows) are rows with IDs like `S1.E1.1` and their own `span.ltx_tag_equation` ("(1.1a)") inside a shape (3) table whose ID is the parent equation (`S1.E1`); that table has no group tag. With `article.ltx_leqno` (same paper) the number cell is the first cell in the row and has `ltx_align_left`. A row is a spacer, to be skipped, when it has class `ltx_eqn_row` without `ltx_equation`; the only instances seen (4, all in the amsart paper) had an `EGx` ID and a single empty `colspan` cell: `<tr id="S1.EGx1" class="ltx_eqn_row"><td class="ltx_eqn_cell" colspan="5"></td></tr>`. Unnumbered equations have `Ex` IDs and no `eqno` cell, but identify numbering by the presence of the tag span, not by the ID.

**Theorems and proofs.**

```html
<div id="S2.Thmtheorem1" class="ltx_theorem ltx_theorem_assumption">
<h6 class="ltx_title ltx_runin ltx_title_theorem"><span class="ltx_tag ltx_tag_theorem"><span id="S2.Thmtheorem1.2" class="ltx_text ltx_font_bold">Assumption 2.1</span></span><span id="S2.Thmtheorem1.3" class="ltx_text ltx_font_bold">.</span></h6>
<div id="S2.Thmtheorem1.p1" class="ltx_para"> ... </div>
</div>
```

The environment type is the second class (`ltx_theorem_theorem`, `_lemma`, `_proposition`, `_definition`, `_remark`, `_assumption` observed). The ID encodes the LaTeX counter, not the type: with a shared counter a theorem can be `S1.Thmlemma1`, and when the counter is not numbered within sections the ID has no section prefix (`<div id="Thmproposition1" class="ltx_theorem ltx_theorem_proposition">`, label "Proposition 1"; `Thmlemma1` in the same paper). Read the type from the class and the label from `ltx_tag_theorem`. Proofs are `div.ltx_proof` with `h6.ltx_title_proof` ("Proof.").

**Figures.** `figure.ltx_figure` with `figcaption.ltx_caption`; the label ("Figure 1") is in `span.ltx_tag.ltx_tag_figure` inside the caption, followed by the caption text, which may contain math and cross-references. The graphic is `<img class="ltx_graphics" src="2611.27969v1/figures/.../velocity.png" alt="Refer to caption">` or, for vector art, `<object type="image/svg+xml" data="2611.27433v1/consensus_formation.svg" class="ltx_graphics ...">`. Subfigures are nested `figure.ltx_figure.ltx_figure_panel` (IDs `...sf1`, captions tagged "(a)") inside `div.ltx_flex_figure > div.ltx_flex_cell`, with the outer `figcaption` last. TikZ and similar become inline `svg.ltx_picture`.

**Tables.** `figure.ltx_table` wrapping `table.ltx_tabular` with `thead.ltx_thead`, `tbody.ltx_tbody`, `tr.ltx_tr`, `th.ltx_td.ltx_th.ltx_th_column|ltx_th_row`, `td.ltx_td`, alignment and rule classes (`ltx_align_center`, `ltx_border_tt`, `ltx_border_t`, `ltx_border_bb`), and `colspan` where used. Header cells are inferred (`ltx_guessed_headers`), so do not rely on `th`. The caption is a `figcaption` with `span.ltx_tag_table` ("Table 1"); the pandoc paper's table has no caption at all. Variation: `\resizebox` wraps the table in `div.ltx_transformed_outer > span.ltx_transformed_inner`; side-by-side tabulars sit in `div.ltx_flex_figure.ltx_flex_table`; `p{}` columns wrap cell text in `span.ltx_inline-block > span.ltx_p.ltx_minipage`.

**Algorithms and code.** An `algorithm` float is `figure.ltx_float.ltx_float_algorithm` with `figcaption` holding `span.ltx_tag.ltx_tag_float` ("Algorithm 1"), then `div.ltx_listing` with one `div.ltx_listingline` per line (IDs `alg1.l1`, ...), each starting with a line-number span `span.ltx_tag.ltx_tag_listingline` ("1:"). Keywords are bold spans; nesting depth is only leading whitespace. The pandoc paper's highlighted code block is not a listing at all: each line is a `span.ltx_text.ltx_verbatim.ltx_font_typewriter.ltx_inline-block` inside an ordinary `p`. Inline code is `span.ltx_text.ltx_font_typewriter`.

**Citations and bibliography.**

```html
<cite class="ltx_cite ltx_citemacro_cite">[<a href="#bib.bib13" title="" class="ltx_ref">38</a>, <a href="#bib.bib11" title="" class="ltx_ref">59</a>]</cite>
```

The visible number and the target ID number are unrelated (`#bib.bib13` displays as 38), so resolve through the `href`. Citation text is not always numeric. With natbib author-year styles the link text is the author and year, and the surrounding brackets may be absent:

```html
<cite class="ltx_cite ltx_citemacro_cite"><a href="#bib.bib24" title="" class="ltx_ref">Einkemmer and Lubich (2018)</a>; ...</cite>
```

Author-year citations can be grammatical parts of a sentence ("as shown by Einkemmer and Lubich (2018)"), so removing every `cite` element from the prose can leave a broken sentence; the prose-metric exclusion needs to handle both styles. `ltx_citemacro_citep` also occurs as the second class (2017 page); other `ltx_citemacro_*` values should be expected. With BibTeX the bibliography is `section#bib.ltx_bibliography > ul.ltx_biblist > li.ltx_bibitem` with typed fields (`ltx_bib_author`, `ltx_bib_year`, `ltx_bib_title`, `ltx_bib_journal`, `ltx_bib_volume`, `ltx_bib_pages`), the label in `span.ltx_tag_bibitem`, external links, and a back-reference block `span.ltx_bibblock.ltx_bib_cited` ("Cited by: §1") that is not in the PDF and must be dropped. In the pandoc paper the conversion is degraded: the references are a plain `section#Sx8` titled "References" with untyped `li.ltx_bibitem` entries, and citations show raw keys (`[<a href="#bib.bibx1" ...>ref-baydin2018ad_survey</a>]`). The plan already excludes citation and reference text from the prose metric; that exclusion is needed.

**Cross-references.** `a.ltx_ref` with a fragment `href`, the visible number in `span.ltx_text.ltx_ref_tag`, and a `title` giving the target's breadcrumb:

```html
(<a href="#S2.E3" title="Equation 3 ‣ 2.1 Discrete-time finite-particle regime ‣ ..." class="ltx_ref"><span class="ltx_text ltx_ref_tag">3</span></a>)
```

Parentheses and words such as "Section" are usually plain text outside the link, but one paper also had the word inside the link as an extra span (`<span class="ltx_text ltx_ref_tag">Section</span> <span class="ltx_text ltx_ref_tag">3.2</span>`), so take the target from the `href` and treat the link text as prose. An unresolved `\ref` becomes an empty `<span class="ltx_ref"></span>`. External links are `a.ltx_ref.ltx_url` or `a.ltx_ref.ltx_href`.

**Footnotes.** Inline at the point of the mark; the body is nested inside and must be lifted out of the sentence:

```html
<span id="footnote1" class="ltx_note ltx_role_footnote"><sup class="ltx_note_mark">1</sup><span class="ltx_note_outer"><span class="ltx_note_content"><sup class="ltx_note_mark">1</sup>
  <span class="ltx_tag ltx_tag_note">1</span> In clustered federated learning, ...</span></span></span>
```

The mark appears three times (outer `sup`, inner `sup`, `ltx_tag_note`). Related roles: `ltx_role_thanks` and `ltx_role_footnotemark` in author blocks; title notes as `span.ltx_pubnotes`.

**Conversion quality signal.** Each page links its build log at `/html/<id>v<n>/__stdout.txt` (plain text, about 250 KB for the paper checked). It ends with a severity line; for 2611.27969v1 it was `Status:conversion:2`, with 3 `Error:` and 137 `Warning:` lines, although the page looked complete. No `ltx_ERROR` or `ltx_missing` elements occurred in any of the five pages. The log is the only way found to filter to "converted without errors", at the cost of a third request per paper.

**Summary of variation between papers.** Same generator version and class vocabulary throughout. Differences come from the document class and source toolchain: equation-number side (`ltx_leqno`), heading number punctuation, presence of abstract/keywords blocks, typed versus untyped bibliography, numeric versus author-year versus raw-key citation text, listings versus verbatim spans for code, tables with or without captions and wrappers, heading levels (`h2` or `h3` for sections), ID shapes (theorem IDs with or without a section prefix), appendix form (titled sibling or untitled nested wrapper), and the mix of equation-group shapes.

What held across the pages looked at is the class vocabulary: `ltx_title_*`, `ltx_para`/`ltx_p`, the equation table classes, `ltx_theorem_*`, `ltx_tag_*`, `ltx_cite`, `ltx_ref`, `ltx_note`, and TeX in `alttext`. What did not hold is anything derived from `h` level, ID shape or the DOM nesting of sections. This rests on five pages weighted toward mathematics (see "Sample limits"), and the fourth paper alone added four variants. The rules are a starting point for the M3 parser, not a stable specification: the parser should be tested on a wider, field-stratified sample (physics, two-column CS, biology-style, astronomy) before they are treated as settled, and it should count and report elements whose classes it does not recognise.

### 6. Fallback sources

| Source | Verified in this session | Licence | Fit |
|---|---|---|---|
| arXiv S3 bulk (`s3://arxiv/pdf`, `/src`) plus local conversion | Help page read; bucket not accessed | Papers keep their own licences | Works for PDF and TeX source. Requester pays; monthly tars of about 500 MB mix all papers, so getting 3,000 specific papers means downloading many tars. HTML must be produced locally |
| `gs://arxiv-dataset` (via Kaggle) | Kaggle description read; bucket not accessed | Same | PDFs, stated to be free. One `gsutil` example in the description mentions source files; actual bucket contents and layout unverified |
| LaTeXML (`brucemiller/LaTeXML`) | Repo and LICENSE read; latest release v0.8.8 (2024-02-26) | Public domain (NIST), CC0-equivalent | Perl; needs TeX Live for many packages |
| latexml-oxide (`dginev/latexml-oxide`) | Repo and README read; pushed 2026-11-23 | CC0-1.0 | The converter arXiv actually runs (0.7.6). Prebuilt macOS binaries and a Homebrew tap; TeX Live still needed at runtime for raw packages. Produces the same markup as section 5, so the same parser applies. Preferred over Perl LaTeXML |
| unarXive 2022 (`IllDepence/unarXive`) | README and both Zenodo records read | Code MIT. Open subset (Zenodo 7752615, 4.8 GB): CC BY-SA 4.0. Full set (Zenodo 7752754): restricted, by request | Covers 1991 to 2022 only, structured text with formulas as LaTeX, no PDFs. Share-alike licence and no pairing make it a poor substitute; usable at most as an equation pool |
| ar5iv 04.2024 dataset (SIGMathLing) | Dataset page read | C-UDA-1.0, download link only after submitting a licence form | 2.17 M HTML documents from LaTeXML 0.8.8, up to April 2024, no images. Requires an agreement in the owner's name; not a drop-in |

## Decision

### Use 1: training corpus from PDF plus native HTML — GO, with conditions, subject to owner decision 3

Basis and its limit. The go rests on robots.txt (which permits `/pdf` and `/html` at a 15-second delay) and on the absence of any statement forbidding a targeted, licence-filtered fetch. It does not rest on an affirmative permission, because none exists for website full-text collection, and it leaves residual risk R1 open: arXiv's full-content harvesting policy requires a special arrangement and sets no threshold. The owner must choose, as part of decision 3 in PLAN.md, between:

- (a) proceed on the robots.txt reading, with the conditions below, accepting that arXiv may regard the M7 run as harvesting and block the address (hard stop on `403`, no retry); or
- (b) ask arXiv first (the help contact page) and wait for a special arrangement or a no. This discloses the owner's identity to arXiv, which is why this record does not do it.

The recommendation is (a) for the 400-paper M4 slice, and for M7 either (b) or (a) with PDFs taken from bulk storage so that only one request per paper, the HTML, goes to the website. If the owner declines both, use fallback 2 (bulk source plus local conversion), which needs no website fetching.

Conditions:

1. Select papers from OAI-PMH metadata only, by exact licence URI: `http://creativecommons.org/licenses/by/4.0/` or `http://creativecommons.org/publicdomain/zero/1.0/`. Nothing else, including BY-SA.
2. Fetch only the latest version (the one the metadata licence describes), by versioned URL, and reject the paper unless the HTML page's `#license-tr` text and `#watermark-tr` version agree with the metadata. This is a fetch-time consistency check, not independent proof of the licence.
3. Follow the fetch policy below without exception.
4. Write the attribution manifest row before a paper enters any derived dataset.
5. Strip arXiv page chrome and author contact details before anything is stored in a derived dataset. Redistribute only content from `article.ltx_document` and the PDF.
6. The 400-paper slice (800 website requests) fetches PDF and HTML from `arxiv.org`.
7. For the 3,000-paper corpus the default is PDFs from bulk storage (`gs://arxiv-dataset`, or `s3://arxiv/pdf`), which arXiv names as the accepted mechanism, and only the HTML from `arxiv.org` (3,000 website requests instead of 6,000). Fetching the PDFs from the website as well is the exception, allowed only if bulk access proves unworkable (bucket contents and cost are unverified) and the owner has accepted option (a) for it.
8. The parser rules in section 5 are provisional. Before M4 labels are trusted, run the parser on a field-stratified sample and review its unrecognised-class report.

### Use 2: runtime fetch of arXiv HTML for the user's paper (S5b) — GO, with conditions

1. Off by default, opt-in per document, as the plan already states. It sends only the arXiv ID.
2. One `GET https://arxiv.org/html/<id>v<n>` per document, cached permanently. The justification is that this is a single, user-initiated retrieval of one page that robots.txt leaves open, at a rate far below the crawl delay; it is the automated equivalent of the user opening the page, and is not harvesting on any reading. It is not a grant under the API ToU, which does not cover website fetches; the ToU's allowance of personal and research use of e-print content is consistent with it but is cited only by analogy. No licence filter applies because nothing is redistributed: the result stays on the machine.
3. Same user agent, spacing and error handling as the corpus fetcher, sharing one global rate limiter.
4. Verify `#watermark-tr` matches the version of the PDF being converted when the PDF's version is known; on mismatch, skip correction rather than align against a different version.
5. Native HTML exists for at least some pre-2024 papers (the 1706.03762 fetch returned a page, and arXiv says it is backfilling), so S5b should not gate on submission date; it should gate on the HTTP result.

### Fetch policy to implement

- **Hosts.** Papers: `https://arxiv.org/pdf/<id>v<n>` and `https://arxiv.org/html/<id>v<n>` only. Metadata: `https://oaipmh.arxiv.org/oai` (`metadataPrefix=arXiv`). Do not fetch `/pdf` or `/html` from `export.arxiv.org` (its robots.txt disallows everything). Never request `/e-print`, `/src`, `/format`, `/api` or `/search` on `arxiv.org`.
- **User agent.** `PodPaper/<version> (research corpus builder)` for the data engine and `PodPaper/<version>` for the runtime fetch, plus `(+<public project URL>)` only if such a URL exists. No name, no e-mail address, no machine or account identifiers. Never a browser string.
- **Rate.** One connection. At least 15 seconds between the completion of one `arxiv.org` request and the start of the next, enforced by a single process-wide limiter persisted across restarts (store the last request time). At least 3 seconds between OAI-PMH requests. No parallelism, no second machine.
- **Errors.** On `403`: stop the whole run and do not retry automatically. On `429` or `503`: honour `Retry-After` if present, otherwise back off starting at 5 minutes and doubling, and stop after three attempts. On `404` for HTML: record "no HTML" and never ask again for that version. Timeouts of 120 seconds for OAI-PMH, which is slow.
- **Caching.** Content-addressed store keyed by `<id>v<n>` and kind (`pdf`, `html`, `log`), holding the raw bytes, `ETag`, `Last-Modified`, fetch time and SHA-256. A cached object is never re-fetched. Because arXiv's HTML for a given version may change (likely, not shown), the stored SHA-256 and the generator stamp are part of the dataset record.
- **Scope per paper.** PDF and HTML: two requests. The build log is a third, optional request; enable it for the 400-paper slice to measure whether `Status:conversion` predicts label quality, then decide for the full corpus. Do not fetch figure assets; geometry and pixels come from the PDF.
- **Metadata harvest.** Follow the documented pattern: `ListRecords` per `group:archive:CATEGORY` set with `from` only and no `until`, following resumption tokens within the same day, and for later incremental runs take `from` from the last server response. Start with a recent `from` (weeks, not years) because responses are slow and some dates hold very large bulk updates; widen only if the corpus cannot be filled. If a request times out at 120 seconds, the fallback is a bounded `from`/`until` window, which deviates from arXiv's recommendation and should be logged as such. Datestamps are modification dates, so results include old papers that were recently replaced: filter by the arXiv ID's `YYMM` prefix for submission date, and remember that only the latest version and its licence are described. Cache the raw XML.
- **Budget.** 400 papers: 800 website requests, about 3.3 hours (5 hours with logs). 3,000 papers with bulk PDFs: 3,000 website requests, about 12.5 hours (25 hours with logs). 3,000 papers with PDFs from the website: 6,000 requests, about 25 hours (37.5 hours with logs).
- **Stamp check.** Record the `Generated by` comment per page. The parser is validated against `LaTeXML oxide (version 0.7.6)`; a different stamp is logged and the paper is flagged for a markup regression check.

### Fallbacks, in order

1. PDFs from `gs://arxiv-dataset` or `s3://arxiv/pdf`, HTML still from `arxiv.org`. This is the default for the 3,000-paper run (condition 7) and the fallback for the 400-paper slice.
2. If HTML fetching becomes unavailable, is refused by arXiv, or the owner declines the residual risk R1: TeX source from `s3://arxiv/src`, converted locally with latexml-oxide (same markup, same parser). Adds a TeX Live dependency.
3. Perl LaTeXML 0.8.8 as a second converter if latexml-oxide fails on the Mac.
4. unarXive and the ar5iv dataset are not adopted, for the licence and coverage reasons in the table.

## Consequences

- Owner decision 3 gains a sub-question: proceed on the robots.txt reading or ask arXiv first (residual risk R1). The M4 slice can start on the recommended default; the M7 run should not start until that is answered.
- The M7 corpus builder needs a bulk-PDF path (GCS or S3 client, manifest lookup from arXiv ID to tar or object) in addition to the website fetcher.
- The plan's fetch budget (15-second delay, about 3 hours and about a day) is confirmed as arithmetic. `arxiv.py` needs a persistent global rate limiter, a content-addressed cache, and hard stops on `403`.
- The licence filter needs an OAI-PMH harvester; the arXiv API cannot provide it. OAI-PMH is slow and has no submission-date selection, so corpus selection is a separate, cached step that runs before any paper fetch.
- The reference parser can be built on class names, with TeX read from `alttext`. It must not rely on heading level, ID shape or section nesting, and the rules need a wider test sample before they are treated as stable. It must special-case: `display` on aligned rows, the three equation table shapes, appendix wrappers, author-year citations, unparsed math, footnotes nested in prose, citation numbers versus bib IDs, the "Cited by" blocks, degraded pandoc-style papers, and author contact details.
- TeX from the HTML is normalised and may contain unexpanded author macros. Formula labels built from it need a normalisation pass and a compile or MathJax check before they are trusted as ground truth. This affects the formula-LaTeX metric and the S5b replacement step.
- arXiv is still generating HTML for old papers and the converter is in beta, so the HTML for a given version probably changes over time (not shown directly). Labels should be treated as reproducible only from our cache, not by re-fetching. The cache is part of the dataset.
- A paper with conversion errors in its log can still render fully, and a clean render is not proof of completeness. Coverage checks against the PDF remain necessary, as the plan's audit already assumes.
- Derived datasets can be published under terms compatible with CC BY 4.0, with the attribution manifest shipped alongside. BY-SA papers stay out, so no share-alike obligation attaches.
- The runtime path makes one request to arXiv per opted-in document and reveals the arXiv ID and the user's IP address to arXiv; the opt-in text should say so.

## Unverified items

- Whether `export.arxiv.org` serves `/html` or `/pdf` at all. Not requested, because its robots.txt disallows it.
- What `arxiv.org/html/<id>` returns for a paper with no HTML (status code and body). No such paper was probed; `404` handling above is an assumption.
- **Residual risk R1:** whether arXiv regards a licence-filtered fetch of 400 or 3,000 papers from the website as "full-content harvesting" needing a special arrangement. The policy has no threshold; the go decision rests on an interpretation.
- Whether the metadata licence can differ from the licence of the latest version, and how per-version licences could be read. The metadata has one licence field and the help page says versions can differ. The infobox check does not resolve this, since it likely shows the same metadata value; it only catches changes between harvest and fetch.
- Whether arXiv re-converts HTML for a paper version that already has HTML (one `Last-Modified` header is consistent with either backfill or re-conversion).
- The exact infobox text for CC0 papers ("License: CC Zero" or similar). Only CC BY 4.0 and the arXiv non-exclusive licence were seen. Compare on the first CC0 paper fetched and prefer the metadata URI.
- The meaning of the `Status:conversion:N` scale in latexml-oxide (assumed to follow LaTeXML: 0 clean, 1 warning, 2 error, 3 fatal), and what failed constructs look like in the HTML (`ltx_ERROR` was not observed).
- Markup of whole classes of paper not sampled: physics (revtex), two-column CS conference styles, biology-style and astronomy papers. The sample is four CC-BY papers (three mathematics, one pandoc) plus one machine-learning page.
- Markup of constructs not present in the papers inspected: `lstlisting` and `minted` code floats, `longtable`, multi-row cells, `cases` and matrices inside MathML (only their TeX was seen), `\tag`, starred theorems with optional titles, `subequations` cross-references, chemistry and physics packages.
- The share of CC-BY and CC0 papers, and so whether 3,000 papers stratified across fields are available from 2024 onward. The one 95-record math.NA sample (about 42%) conflicts with arXiv's "very small subset" and "small fraction" statements about the corpus; neither settles the figure for recent papers per field.
- The plan's figure that about 75% of papers convert without errors (arXiv:2605.16562) was not checked; the latexml-oxide README cites the same paper and claims 98% for the current converter.
- Access to `s3://arxiv` and `gs://arxiv-dataset` (no cloud credentials used), what the GCS bucket actually holds (PDFs only, or source too) and how objects are keyed, their current cost, and whether the Kaggle metadata snapshot carries a per-paper licence field.
- Whether arXiv asserts any rights of its own over the generated HTML. No statement was found on the pages read; the policy avoids the question by redistributing only author content and stripping arXiv chrome.
- Whether arXiv would grant a special arrangement or wants advance notice for the corpus run. Robots Beware requires advance contact only for relaxed limits, but the full-content harvesting policy may require it regardless of rate (R1). Contacting arXiv would disclose the owner's identity, so it is left as an owner decision.
- Third-party material inside a CC-BY paper (reused figures) may not be covered by the paper's licence. Not checkable automatically.
- This is an engineering reading of published terms, not legal advice.
