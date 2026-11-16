"""Data passed between stages before a PaperDoc exists, and the engine interfaces.

All geometry is in PDF points, origin at the top-left of the page, like the IR.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import Field

from podpaper.ir import BBox, Confidence, Model, Source, Unit

if TYPE_CHECKING:
    import numpy as np
    from PIL.Image import Image

Route = Literal["text_layer", "text_layer+math", "full_ocr", "escalate"]


# --------------------------------------------------------------------------- S0 ingest


class Glyph(Model):
    """One character of the PDF text layer."""

    c: str
    bbox: BBox
    font: str = ""
    size: float = 0.0


class TextLine(Model):
    """A visual line of the text layer, glyphs in reading order."""

    bbox: BBox
    text: str = Field(description="Ligatures expanded, spaces reconstructed.")
    glyphs: list[Glyph]


class PageText(Model):
    index: int = Field(ge=0)
    width: float = Field(gt=0, description="PDF points.")
    height: float = Field(gt=0)
    dpi: int = Field(gt=0)
    image_blob: str = Field(description="Blob hash of the rendered page, PNG, RGB.")
    lines: list[TextLine]
    score: Unit = Field(description="Text-layer sanity score: 1 is clean text, 0 is unusable.")


class IngestResult(Model):
    doc_id: str = Field(description="sha256 of the input PDF bytes.")
    source_name: str
    n_pages_total: int = Field(ge=0, description="Pages in the file, before any page range.")
    pages: list[PageText]
    arxiv_id: str | None = None
    outline: list[tuple[int, str, int]] = Field(
        default_factory=list, description="PDF bookmarks as (level, title, page index)."
    )


# --------------------------------------------------------------------------- S1 layout


class BlockClass(StrEnum):
    """Our layout classes; the layout model's labels are mapped onto these."""

    TITLE = "title"
    HEADING = "heading"
    TEXT = "text"
    ABSTRACT = "abstract"
    FORMULA = "formula"  # display formula
    INLINE_FORMULA = "inline_formula"
    FORMULA_NUMBER = "formula_number"
    FIGURE = "figure"
    TABLE = "table"
    CAPTION = "caption"
    ALGORITHM = "algorithm"
    FOOTNOTE = "footnote"
    REFERENCE = "reference"
    FURNITURE = "furniture"  # headers, footers, page numbers, side text
    OTHER = "other"


class LayoutBlock(Model):
    page: int = Field(ge=0)
    bbox: BBox
    cls: BlockClass
    label: str = Field(description="The layout model's own label, kept for debugging.")
    score: Unit
    order: int = Field(ge=0, description="Reading order within the page.")


class PageLayout(Model):
    page: int = Field(ge=0)
    blocks: list[LayoutBlock] = Field(description="Sorted by order.")


# --------------------------------------------------------------------------- S3 recognise


class RecognizedBlock(Model):
    """One layout block with its content resolved.

    ``text`` is prose with inline math written as ``$...$`` (LaTeX inside, a literal
    dollar sign escaped as ``\\$``). For a display formula ``tex`` holds the LaTeX and
    ``text`` is empty. Figures carry ``image_blob`` only.
    """

    page: int = Field(ge=0)
    bbox: BBox
    cls: BlockClass
    order: int = Field(ge=0)
    text: str = ""
    tex: str | None = None
    label: str | None = Field(default=None, description='Printed number, e.g. "(4)".')
    table_html: str | None = None
    image_blob: str | None = None
    font_size: float | None = Field(default=None, description="Median glyph size, for headings.")
    source: Source = Source.TEXT_LAYER
    confidence: Confidence = Field(default_factory=Confidence)


class RecognizedPage(Model):
    page: int = Field(ge=0)
    route: Route
    blocks: list[RecognizedBlock] = Field(description="Sorted by order; furniture removed.")


# --------------------------------------------------------------------------- S8 synthesis


class SynthWord(Model):
    """A word of the spoken text; samples are relative to the start of the utterance."""

    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    start_sample: int = Field(ge=0)
    end_sample: int = Field(ge=0)


class SynthUtterance(Model):
    utterance_id: str
    audio_blob: str = Field(description="Blob hash: mono float32 little-endian PCM samples.")
    sample_rate: int = Field(gt=0)
    n_samples: int = Field(ge=0)
    words: list[SynthWord] = Field(default_factory=list)


# --------------------------------------------------------------------------- engines


class LayoutEngine(Protocol):
    """Detects blocks on one rendered page."""

    revision: str

    def detect(self, image: Image, page: int, width: float, height: float) -> PageLayout: ...


class OcrEngine(Protocol):
    """Reads one image crop. ``kind`` selects the prompt."""

    revision: str

    def recognize(self, image: Image, kind: Literal["text", "formula", "table"]) -> str: ...


class TtsEngine(Protocol):
    """Speaks one short piece of normalized text."""

    revision: str
    sample_rate: int

    def synthesize(self, text: str) -> tuple[np.ndarray, list[SynthWord]]:
        """Return mono float32 samples and word times relative to the start."""
        ...
