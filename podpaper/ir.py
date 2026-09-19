"""Document intermediate representation (IR), version 0.

Three artifacts per document, kept separate because the listener can change
how things are read without the document changing:

* ``PaperDoc``       - what is on the page
* ``NarrationPlan``  - what is said
* ``Timeline``       - when it is said

All geometry is in PDF points with the origin at the top-left of the page.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 0

Unit = Annotated[float, Field(ge=0.0, le=1.0)]
Id = Annotated[str, Field(min_length=1)]


class Model(BaseModel):
    """Base: reject unknown fields so schema drift fails loudly."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


# --------------------------------------------------------------------------- geometry


class BBox(Model):
    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="after")
    def _ordered(self) -> BBox:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("bbox corners must satisfy x0 <= x1 and y0 <= y1")
        return self


class Prov(Model):
    """Where an element sits. More than one Prov means it spans pages or columns."""

    page: int = Field(ge=0)
    bbox: BBox


class Page(Model):
    index: int = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    route: Literal["text_layer", "text_layer+math", "full_ocr", "escalate"] | None = None
    text_layer_score: Unit | None = None


# --------------------------------------------------------------------------- spans


class Text(Model):
    type: Literal["text"] = "text"
    text: str


class MathRef(Model):
    """Inline math; the content lives in ``PaperDoc.math``."""

    type: Literal["math"] = "math"
    math_id: str


class DisplayMathRef(Model):
    """A display equation that is grammatically part of this sentence."""

    type: Literal["display_math"] = "display_math"
    element_id: str


class Cite(Model):
    type: Literal["cite"] = "cite"
    text: str
    bib_ids: list[str] = Field(default_factory=list)


class XRef(Model):
    """In-text mention such as "Fig. 3" or "Eq. (4)"."""

    type: Literal["xref"] = "xref"
    text: str
    target_element_id: str | None = None


class FootnoteMark(Model):
    type: Literal["footnote_mark"] = "footnote_mark"
    text: str
    footnote_element_id: str | None = None


class Link(Model):
    type: Literal["link"] = "link"
    text: str
    url: str


Span = Annotated[
    Text | MathRef | DisplayMathRef | Cite | XRef | FootnoteMark | Link,
    Field(discriminator="type"),
]


class Sentence(Model):
    id: Id
    spans: list[Span]


# --------------------------------------------------------------------------- elements


class Kind(StrEnum):
    TITLE = "title"
    AUTHORS = "authors"
    ABSTRACT = "abstract"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    DISPLAY_MATH = "display_math"
    FIGURE = "figure"
    TABLE = "table"
    CAPTION = "caption"
    ALGORITHM = "algorithm"
    CODE = "code"
    THEOREM = "theorem"
    PROOF = "proof"
    FOOTNOTE = "footnote"
    REFERENCE_ENTRY = "reference_entry"
    FURNITURE = "furniture"


class SkipGroup(StrEnum):
    """Groups the player can skip as a whole."""

    PROOF = "proof"
    REFERENCES = "references"
    FOOTNOTE = "footnote"
    APPENDIX = "appendix"
    ACKNOWLEDGEMENTS = "acknowledgements"


class Source(StrEnum):
    TEXT_LAYER = "textlayer"
    RULE = "rule"
    VLM = "vlm"
    HTML = "html"
    LLM = "llm"


class Trust(StrEnum):
    OK = "ok"
    LOW = "low"


class Confidence(Model):
    layout: Unit | None = None
    recog: Unit | None = None
    agreement: Unit | None = None
    trust: Trust = Trust.OK


class Element(Model):
    id: Id
    kind: Kind
    order: int = Field(ge=0, description="Position in the global reading order.")
    prov: list[Prov] = Field(
        default_factory=list,
        description="Boxes on the page. Empty only in a geometry-free document (no pages).",
    )
    source: Source
    confidence: Confidence = Field(default_factory=Confidence)

    flow_id: str | None = Field(
        default=None,
        description="Elements sharing a flow_id form one logical paragraph.",
    )
    continues_from: str | None = None
    display_no: int | None = Field(
        default=None, ge=1, description='Number by type, as in "Paragraph 2".'
    )
    label: str | None = Field(default=None, description='Printed label, e.g. "(4)" or "Fig. 3".')
    section_id: str | None = None
    skip_group: SkipGroup | None = None

    # Content: which fields are set depends on kind.
    sentences: list[Sentence] = Field(default_factory=list)
    math_id: str | None = None
    table_html: str | None = None
    image_blob: str | None = Field(default=None, description="Content hash of the crop.")
    raw_text: str | None = Field(
        default=None, description="Algorithm or code body, shown not read."
    )

    description: str | None = Field(
        default=None, description="Generated figure description (S6); never the caption."
    )

    caption_id: str | None = Field(default=None, description="On a figure/table: its caption.")
    target_id: str | None = Field(default=None, description="On a caption: what it captions.")

    @model_validator(mode="after")
    def _content_matches_kind(self) -> Element:
        if self.kind is Kind.DISPLAY_MATH and self.math_id is None:
            raise ValueError(f"{self.id}: display_math needs math_id")
        if self.kind is not Kind.DISPLAY_MATH and self.math_id is not None:
            raise ValueError(f"{self.id}: only display_math carries math_id")
        return self


class MathStats(Model):
    nodes: int = Field(ge=0)
    depth: int = Field(ge=0)
    has_2d: bool = False
    n_lines: int = Field(default=1, ge=1)


class Math(Model):
    id: Id
    display: bool
    tex: str
    tex_norm: str | None = None
    mathml: str | None = None
    alt_tex: list[str] = Field(
        default_factory=list, description="Other readings: rule mapping or second recogniser."
    )
    number: str | None = None
    stats: MathStats | None = None
    leaves: list[str] = Field(
        default_factory=list,
        description="Multiset of identifiers, numbers and operators from the semantic tree.",
    )
    confidence: Confidence = Field(default_factory=Confidence)


class Section(Model):
    id: Id
    title: str
    level: int = Field(ge=1)
    parent_id: str | None = None
    heading_element_id: str | None = None


class BibEntry(Model):
    id: Id
    text: str
    number: int | None = None
    element_id: str | None = None


class GlossaryRow(Model):
    symbol_tex: str
    meaning: str
    defined_in: str = Field(description="Element id of the defining sentence's element.")


class LexiconEntry(Model):
    written: str
    spoken: str | None = None
    phonemes: str | None = None


class PaperDoc(Model):
    schema_version: Literal[0] = SCHEMA_VERSION
    doc_id: Id = Field(description="sha256 of the input PDF.")
    title: str | None = None
    arxiv_id: str | None = None
    pages: list[Page] = Field(
        description="Empty for a geometry-free reference document (e.g. parsed from HTML)."
    )
    elements: list[Element]
    math: dict[str, Math] = Field(default_factory=dict)
    sections: list[Section] = Field(default_factory=list)
    bibliography: list[BibEntry] = Field(default_factory=list)
    glossary: list[GlossaryRow] = Field(default_factory=list)
    lexicon: list[LexiconEntry] = Field(default_factory=list)

    def element(self, element_id: str) -> Element:
        for el in self.elements:
            if el.id == element_id:
                return el
        raise KeyError(element_id)

    @model_validator(mode="after")
    def _consistent(self) -> PaperDoc:
        errors: list[str] = []

        ids = [el.id for el in self.elements]
        if len(set(ids)) != len(ids):
            errors.append("element ids are not unique")
        id_set = set(ids)

        if [el.order for el in self.elements] != list(range(len(self.elements))):
            errors.append("elements must be listed in reading order with order = 0..n-1")

        for key, m in self.math.items():
            if key != m.id:
                errors.append(f"math key {key!r} does not match id {m.id!r}")

        n_pages = len(self.pages)
        if [p.index for p in self.pages] != list(range(n_pages)):
            errors.append("pages must be listed with index = 0..n-1")

        section_ids = {s.id for s in self.sections}
        if len(section_ids) != len(self.sections):
            errors.append("section ids are not unique")
        bib_ids = {b.id for b in self.bibliography}
        if len(bib_ids) != len(self.bibliography):
            errors.append("bibliography ids are not unique")
        by_id = {el.id: el for el in self.elements}
        sentence_ids: list[str] = []

        def need_element(owner: str, field: str, ref: str | None) -> None:
            if ref is not None and ref not in id_set:
                errors.append(f"{owner}.{field} -> unknown element {ref!r}")

        for el in self.elements:
            if n_pages and not el.prov:
                errors.append(f"{el.id}: needs at least one box in a document with pages")
            for p in el.prov:
                if p.page >= n_pages:
                    errors.append(f"{el.id}: prov page {p.page} is out of range")
            if el.continues_from == el.id:
                errors.append(f"{el.id}: continues from itself")
            if el.math_id in self.math and not self.math[el.math_id].display:
                errors.append(f"{el.id}: display_math points at inline math {el.math_id!r}")
            need_element(el.id, "continues_from", el.continues_from)
            need_element(el.id, "caption_id", el.caption_id)
            need_element(el.id, "target_id", el.target_id)
            if el.section_id is not None and el.section_id not in section_ids:
                errors.append(f"{el.id}.section_id -> unknown section {el.section_id!r}")
            if el.math_id is not None and el.math_id not in self.math:
                errors.append(f"{el.id}.math_id -> unknown math {el.math_id!r}")
            for s in el.sentences:
                sentence_ids.append(s.id)
                for span in s.spans:
                    if isinstance(span, MathRef) and span.math_id not in self.math:
                        errors.append(f"{s.id}: unknown math {span.math_id!r}")
                    elif isinstance(span, DisplayMathRef):
                        need_element(s.id, "display_math", span.element_id)
                        target = by_id.get(span.element_id)
                        if target is not None and target.kind is not Kind.DISPLAY_MATH:
                            errors.append(f"{s.id}: {span.element_id!r} is not display math")
                    elif isinstance(span, XRef):
                        need_element(s.id, "xref", span.target_element_id)
                    elif isinstance(span, FootnoteMark):
                        need_element(s.id, "footnote", span.footnote_element_id)
                    elif isinstance(span, Cite):
                        for b in span.bib_ids:
                            if b not in bib_ids:
                                errors.append(f"{s.id}: unknown bibliography entry {b!r}")

        if len(set(sentence_ids)) != len(sentence_ids):
            errors.append("sentence ids are not unique")

        parents = {s.id: s.parent_id for s in self.sections}
        for s in self.sections:
            if s.parent_id is not None and s.parent_id not in section_ids:
                errors.append(f"section {s.id}: unknown parent {s.parent_id!r}")
            seen, cur = {s.id}, s.parent_id
            while cur is not None and cur in parents:
                if cur in seen:
                    errors.append(f"section {s.id}: parent chain loops")
                    break
                seen.add(cur)
                cur = parents[cur]
            need_element(f"section {s.id}", "heading_element_id", s.heading_element_id)
        for row in self.glossary:
            need_element("glossary", "defined_in", row.defined_in)
        for b in self.bibliography:
            need_element(f"bib {b.id}", "element_id", b.element_id)

        if errors:
            raise ValueError("; ".join(errors))
        return self


# --------------------------------------------------------------------------- narration


class Level(StrEnum):
    """How a piece of math is read."""

    L0_SKIP = "L0"  # announced only
    L1_GIST = "L1"  # one-sentence gist
    L2_NATURAL = "L2"  # natural reading
    L3_CLEARSPEAK = "L3"  # literal, ClearSpeak style
    L4_MATHSPEAK = "L4"  # literal, MathSpeak style


class UtteranceKind(StrEnum):
    SENTENCE = "sentence"
    ANNOUNCE = "announce"  # "Figure 3", "an equation is shown here ..."
    MATH = "math"
    CAPTION = "caption"
    DESCRIPTION = "description"  # generated figure description
    PROMPT = "prompt"  # the spoken "continue?" prompt


class SrcMap(Model):
    """Maps spoken characters [start, end) back to the span they came from."""

    start: int = Field(ge=0)
    end: int = Field(ge=0)
    element_id: str | None = Field(
        default=None,
        description=(
            "Element this range sits in, when it differs from the utterance's own element: "
            "a sentence that runs through a flow group is owned by its first element, and "
            "this says which element to highlight for each part."
        ),
    )
    sentence_id: str | None = None
    span_index: int | None = Field(default=None, ge=0)
    math_id: str | None = None

    @model_validator(mode="after")
    def _ordered(self) -> SrcMap:
        if self.end < self.start:
            raise ValueError("src_map end is before start")
        return self


class Verify(Model):
    check: str = Field(description="Name of the deterministic check that ran.")
    passed: bool
    fallback: bool = Field(default=False, description="True if the rule reading was used.")
    engine: str = Field(description='What produced the text, e.g. "sre" or "qwen3.8-27b".')


class Utterance(Model):
    """One thing to say.

    ``spoken`` must already be normalized: S7 has to map or strip the characters
    ``\\ $ ^ _ { }`` (for example "$5" to "five dollars") before building an utterance.
    """

    id: Id
    element_id: str
    sentence_id: str | None = None
    kind: UtteranceKind
    level: Level | None = None
    spoken: str
    src_map: list[SrcMap] = Field(default_factory=list)
    pause_after_ms: int = Field(default=0, ge=0)
    alt_of: str | None = Field(
        default=None, description="Utterance this is an alternative reading of."
    )
    verify: Verify | None = None

    @model_validator(mode="after")
    def _no_raw_latex(self) -> Utterance:
        if not self.spoken.strip():
            raise ValueError(f"{self.id}: spoken text is blank")
        if self.alt_of == self.id:
            raise ValueError(f"{self.id}: is an alternative of itself")
        bad = sorted(set(self.spoken) & set("\\$^_{}"))
        if bad:
            raise ValueError(f"{self.id}: spoken text contains LaTeX characters {bad}")
        for m in self.src_map:
            if not (m.start <= m.end <= len(self.spoken)):
                raise ValueError(f"{self.id}: src_map range [{m.start}, {m.end}) is out of bounds")
        return self


class NarrationPlan(Model):
    schema_version: Literal[0] = SCHEMA_VERSION
    doc_id: str
    profile: str = "default"
    utterances: list[Utterance]

    @model_validator(mode="after")
    def _unique(self) -> NarrationPlan:
        ids = [u.id for u in self.utterances]
        if len(set(ids)) != len(ids):
            raise ValueError("utterance ids are not unique")
        id_set = set(ids)
        for u in self.utterances:
            if u.alt_of is not None and u.alt_of not in id_set:
                raise ValueError(f"{u.id}.alt_of -> unknown utterance {u.alt_of!r}")
        return self


# --------------------------------------------------------------------------- timeline


class AudioSegment(Model):
    """One audio file, normally one per section."""

    id: Id
    section_id: str | None = None
    blob: str = Field(description="Content hash of the encoded audio.")
    sample_rate: int = Field(gt=0)
    n_samples: int = Field(ge=0)


class WordTime(Model):
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    start_sample: int = Field(ge=0)
    end_sample: int = Field(ge=0)

    @model_validator(mode="after")
    def _ordered(self) -> WordTime:
        if self.char_end < self.char_start or self.end_sample < self.start_sample:
            raise ValueError("word time runs backwards")
        return self


class UtteranceTime(Model):
    """Sample positions, here and in ``words``, are relative to the start of the segment."""

    utterance_id: str
    segment_id: str
    start_sample: int = Field(ge=0)
    end_sample: int = Field(ge=0)
    words: list[WordTime] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ordered(self) -> UtteranceTime:
        if self.end_sample < self.start_sample:
            raise ValueError(f"{self.utterance_id}: end before start")
        last = self.start_sample
        for w in self.words:
            if w.start_sample < last or w.end_sample > self.end_sample:
                raise ValueError(f"{self.utterance_id}: word times are unordered or out of range")
            last = w.end_sample
        return self


class ReferenceEvent(Model):
    """Fires when a cross-reference is spoken; drives "pause at figure reference"."""

    utterance_id: str
    target_element_id: str
    segment_id: str
    at_sample: int = Field(ge=0)


class Chapter(Model):
    title: str
    section_id: str | None = None
    segment_id: str
    start_sample: int = Field(ge=0)


class Timeline(Model):
    schema_version: Literal[0] = SCHEMA_VERSION
    doc_id: str
    voice: str
    segments: list[AudioSegment]
    utterances: list[UtteranceTime]
    reference_events: list[ReferenceEvent] = Field(default_factory=list)
    chapters: list[Chapter] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> Timeline:
        segs = {s.id: s for s in self.segments}
        if len(segs) != len(self.segments):
            raise ValueError("segment ids are not unique")
        cursor: dict[str, int] = dict.fromkeys(segs, 0)
        for u in self.utterances:
            seg = segs.get(u.segment_id)
            if seg is None:
                raise ValueError(f"{u.utterance_id}: unknown segment {u.segment_id!r}")
            if u.start_sample < cursor[seg.id]:
                raise ValueError(f"{u.utterance_id}: overlaps the previous utterance")
            if u.end_sample > seg.n_samples:
                raise ValueError(f"{u.utterance_id}: runs past the end of segment {seg.id}")
            cursor[seg.id] = u.end_sample
        for ev in self.reference_events:
            if ev.segment_id not in segs:
                raise ValueError(f"reference event: unknown segment {ev.segment_id!r}")
            if ev.at_sample > segs[ev.segment_id].n_samples:
                raise ValueError("reference event: lies past the end of its segment")
        for ch in self.chapters:
            if ch.segment_id not in segs:
                raise ValueError(f"chapter {ch.title!r}: unknown segment {ch.segment_id!r}")
            if ch.start_sample > segs[ch.segment_id].n_samples:
                raise ValueError(f"chapter {ch.title!r}: starts past the end of its segment")
        return self


class Playhead(Model):
    """Listener position. Never stored as seconds, so re-renders keep the place."""

    element_id: str
    sentence_id: str | None = None
    fraction: Unit = 0.0
