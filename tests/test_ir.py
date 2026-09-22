"""IR v0: valid documents round-trip, and each consistency check rejects its broken case."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from podpaper import ir


def box(y: float = 0.0) -> list[ir.Prov]:
    return [ir.Prov(page=0, bbox=ir.BBox(x0=72, y0=y, x1=540, y1=y + 20))]


def make_doc() -> ir.PaperDoc:
    """Heading, then "We obtain [display equation] where x is small." as one flow group."""
    fields: dict[str, object] = dict(
        doc_id="0" * 64,
        pages=[ir.Page(index=0, width=612, height=792)],
        sections=[ir.Section(id="s1", title="Method", level=1, heading_element_id="e0")],
        math={
            "m0": ir.Math(id="m0", display=True, tex=r"E = mc^2", number="(1)"),
            "m1": ir.Math(id="m1", display=False, tex="x", leaves=["x"]),
        },
        elements=[
            ir.Element(
                id="e0",
                kind=ir.Kind.HEADING,
                order=0,
                prov=box(0),
                source=ir.Source.TEXT_LAYER,
                section_id="s1",
                sentences=[ir.Sentence(id="e0.s0", spans=[ir.Text(text="Method")])],
            ),
            ir.Element(
                id="e1",
                kind=ir.Kind.PARAGRAPH,
                order=1,
                prov=box(30),
                source=ir.Source.TEXT_LAYER,
                flow_id="f0",
                display_no=1,
                section_id="s1",
                sentences=[
                    ir.Sentence(
                        id="e1.s0",
                        spans=[
                            ir.Text(text="We obtain "),
                            ir.DisplayMathRef(element_id="e2"),
                            ir.Text(text=" where "),
                            ir.MathRef(math_id="m1"),
                            ir.Text(text=" is small, see "),
                            ir.XRef(text="Eq. (1)", target_element_id="e2"),
                            ir.Text(text="."),
                        ],
                    )
                ],
            ),
            ir.Element(
                id="e2",
                kind=ir.Kind.DISPLAY_MATH,
                order=2,
                prov=box(60),
                source=ir.Source.VLM,
                flow_id="f0",
                label="(1)",
                math_id="m0",
            ),
        ],
    )
    return ir.PaperDoc.model_validate(fields)


def test_paperdoc_round_trips_through_json() -> None:
    doc = make_doc()
    again = ir.PaperDoc.model_validate_json(doc.model_dump_json())
    assert again == doc
    spans = again.element("e1").sentences[0].spans
    assert isinstance(spans[1], ir.DisplayMathRef)
    assert isinstance(spans[3], ir.MathRef)


def test_schema_version_is_written() -> None:
    assert make_doc().model_dump()["schema_version"] == ir.SCHEMA_VERSION


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ir.Page.model_validate({"index": 0, "width": 612, "height": 792, "colour": "red"})


def test_dangling_math_reference_is_rejected() -> None:
    doc = make_doc()
    data = doc.model_dump()
    del data["math"]["m1"]
    with pytest.raises(ValidationError, match="unknown math 'm1'"):
        ir.PaperDoc.model_validate(data)


def test_dangling_element_reference_is_rejected() -> None:
    data = make_doc().model_dump()
    data["elements"][1]["sentences"][0]["spans"][5]["target_element_id"] = "e99"
    with pytest.raises(ValidationError, match="unknown element 'e99'"):
        ir.PaperDoc.model_validate(data)


def test_reading_order_must_be_contiguous() -> None:
    data = make_doc().model_dump()
    data["elements"][2]["order"] = 5
    with pytest.raises(ValidationError, match="reading order"):
        ir.PaperDoc.model_validate(data)


def test_prov_page_must_exist() -> None:
    data = make_doc().model_dump()
    data["elements"][0]["prov"][0]["page"] = 3
    with pytest.raises(ValidationError, match="out of range"):
        ir.PaperDoc.model_validate(data)


def test_display_math_needs_math_id() -> None:
    with pytest.raises(ValidationError, match="needs math_id"):
        ir.Element(id="e9", kind=ir.Kind.DISPLAY_MATH, order=0, prov=box(), source=ir.Source.VLM)


def test_bbox_corners_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        ir.BBox(x0=10, y0=0, x1=5, y1=1)


@pytest.mark.parametrize("bad", [r"x \alpha", "$x$", "x^2", "x_1", "{x}"])
def test_spoken_text_never_contains_latex(bad: str) -> None:
    with pytest.raises(ValidationError, match="LaTeX characters"):
        ir.Utterance(id="u0", element_id="e1", kind=ir.UtteranceKind.MATH, spoken=bad)


def test_narration_plan_checks_alternatives() -> None:
    u0 = ir.Utterance(
        id="u0",
        element_id="e2",
        kind=ir.UtteranceKind.MATH,
        level=ir.Level.L2_NATURAL,
        spoken="E equals m c squared",
        src_map=[ir.SrcMap(start=0, end=20, math_id="m0")],
        verify=ir.Verify(check="leaf_coverage", passed=True, engine="sre"),
    )
    literal = u0.model_copy(update={"id": "u1", "level": ir.Level.L3_CLEARSPEAK, "alt_of": "u0"})
    plan = ir.NarrationPlan(doc_id="0" * 64, utterances=[u0, literal])
    assert ir.NarrationPlan.model_validate_json(plan.model_dump_json()) == plan

    orphan = u0.model_copy(update={"id": "u2", "alt_of": "nope"})
    with pytest.raises(ValidationError, match="unknown utterance"):
        ir.NarrationPlan(doc_id="0" * 64, utterances=[u0, orphan])


def make_timeline(second_start: int = 24_000, n_samples: int = 48_000) -> ir.Timeline:
    return ir.Timeline(
        doc_id="0" * 64,
        voice="af_heart",
        segments=[ir.AudioSegment(id="a0", blob="b" * 64, sample_rate=24_000, n_samples=n_samples)],
        utterances=[
            ir.UtteranceTime(utterance_id="u0", segment_id="a0", start_sample=0, end_sample=24_000),
            ir.UtteranceTime(
                utterance_id="u1", segment_id="a0", start_sample=second_start, end_sample=48_000
            ),
        ],
        chapters=[ir.Chapter(title="Method", segment_id="a0", start_sample=0)],
    )


def test_timeline_round_trips() -> None:
    tl = make_timeline()
    assert ir.Timeline.model_validate_json(tl.model_dump_json()) == tl


def test_timeline_rejects_overlap_and_overrun() -> None:
    with pytest.raises(ValidationError, match="overlaps"):
        make_timeline(second_start=10_000)
    with pytest.raises(ValidationError, match="past the end"):
        make_timeline(n_samples=40_000)


def test_playhead_fraction_is_bounded() -> None:
    assert ir.Playhead(element_id="e1").fraction == 0.0
    with pytest.raises(ValidationError):
        ir.Playhead(element_id="e1", fraction=1.5)


# ----------------------------------------------------------------- broken documents


def _set(path: list[str | int], value: object):
    def mutate(data: dict) -> None:
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return mutate


def _dup(key: str):
    def mutate(data: dict) -> None:
        data[key].append(dict(data[key][0]))

    return mutate


def _bib(data: dict) -> None:
    data["bibliography"] = [{"id": "b1", "text": "A. Author, 2020."}] * 2


PAPERDOC_MUTATIONS = [
    (_set(["elements", 2, "id"], "e1"), "element ids are not unique"),
    (_set(["math", "m0", "id"], "zz"), "does not match id"),
    (_set(["pages", 0, "index"], 1), "pages must be listed"),
    (_set(["elements", 0, "section_id"], "s9"), "unknown section"),
    (_set(["elements", 2, "math_id"], "m9"), "unknown math 'm9'"),
    (_set(["elements", 2, "math_id"], "m1"), "points at inline math"),
    (_set(["elements", 0, "sentences", 0, "id"], "e1.s0"), "sentence ids are not unique"),
    (_set(["elements", 1, "sentences", 0, "spans", 1, "element_id"], "e0"), "is not display math"),
    (_set(["elements", 1, "sentences", 0, "spans", 1, "element_id"], "e77"), "unknown element"),
    (_set(["elements", 1, "continues_from"], "e1"), "continues from itself"),
    (_set(["elements", 1, "prov"], []), "needs at least one box"),
    (_set(["sections", 0, "parent_id"], "s9"), "unknown parent"),
    (_set(["sections", 0, "parent_id"], "s1"), "parent chain loops"),
    (_dup("sections"), "section ids are not unique"),
    (_bib, "bibliography ids are not unique"),
    (_set(["elements", 0, "id"], ""), "at least 1 character"),
    (_set(["schema_version"], 1), "schema_version"),
    (_set(["elements", 0, "prov", 0, "bbox", "y1"], -1.0), "bbox corners"),
    (_set(["pages", 0, "width"], float("inf")), "finite"),
    (_set(["elements", 0, "confidence", "layout"], -0.1), "greater than or equal to 0"),
]


@pytest.mark.parametrize(("mutate", "message"), PAPERDOC_MUTATIONS)
def test_broken_paperdoc_is_rejected(mutate, message: str) -> None:
    data = make_doc().model_dump()
    mutate(data)
    with pytest.raises(ValidationError, match=message):
        ir.PaperDoc.model_validate(data)


def test_cite_must_resolve_to_bibliography() -> None:
    data = make_doc().model_dump()
    data["elements"][0]["sentences"][0]["spans"].append(
        {"type": "cite", "text": "[1]", "bib_ids": ["b1"]}
    )
    with pytest.raises(ValidationError, match="unknown bibliography entry"):
        ir.PaperDoc.model_validate(data)
    data["bibliography"] = [{"id": "b1", "text": "A. Author, 2020."}]
    ir.PaperDoc.model_validate(data)


def test_only_display_math_carries_math_id() -> None:
    with pytest.raises(ValidationError, match="only display_math"):
        ir.Element(
            id="e9",
            kind=ir.Kind.PARAGRAPH,
            order=0,
            prov=box(),
            source=ir.Source.RULE,
            math_id="m0",
        )


def test_geometry_free_reference_document() -> None:
    """A reference document parsed from HTML has no pages and no boxes."""
    doc = ir.PaperDoc(
        doc_id="html:2401.00001",
        pages=[],
        elements=[
            ir.Element(
                id="e0",
                kind=ir.Kind.PARAGRAPH,
                order=0,
                source=ir.Source.HTML,
                sentences=[ir.Sentence(id="e0.s0", spans=[ir.Text(text="Hello.")])],
            )
        ],
    )
    assert ir.PaperDoc.model_validate_json(doc.model_dump_json()) == doc


def test_sentence_through_a_three_element_flow_group() -> None:
    """ "We obtain [equation] where x is small." spans paragraph, equation, paragraph.

    The first element owns the whole sentence; the continuation paragraph has no sentences of
    its own. SrcMap.element_id says which element each spoken range sits in, so the player can
    highlight the continuation while its words are spoken.
    """
    data = make_doc().model_dump()
    data["elements"].append(
        {
            "id": "e3",
            "kind": "paragraph",
            "order": 3,
            "prov": [{"page": 0, "bbox": {"x0": 72, "y0": 90, "x1": 540, "y1": 110}}],
            "source": "textlayer",
            "flow_id": "f0",
            "continues_from": "e1",
        }
    )
    doc = ir.PaperDoc.model_validate(data)
    assert [el.id for el in doc.elements if el.flow_id == "f0"] == ["e1", "e2", "e3"]
    assert doc.element("e3").sentences == []

    spoken = "We obtain E equals m c squared where x is small."
    utterance = ir.Utterance(
        id="u0",
        element_id="e1",
        sentence_id="e1.s0",
        kind=ir.UtteranceKind.SENTENCE,
        spoken=spoken,
        src_map=[
            ir.SrcMap(start=0, end=10, sentence_id="e1.s0", span_index=0),
            ir.SrcMap(start=10, end=30, element_id="e2", math_id="m0", span_index=1),
            ir.SrcMap(start=30, end=len(spoken), element_id="e3", span_index=2),
        ],
    )
    assert [m.element_id or utterance.element_id for m in utterance.src_map] == ["e1", "e2", "e3"]


# ------------------------------------------------------- broken narration and timeline


def test_utterance_rejects_blank_text_bad_ranges_and_self_alternative() -> None:
    def make(**kw: object) -> ir.Utterance:
        base = {"id": "u0", "element_id": "e1", "kind": "sentence", "spoken": "Hello there."}
        return ir.Utterance.model_validate({**base, **kw})

    make()
    with pytest.raises(ValidationError, match="blank"):
        make(spoken="   ")
    with pytest.raises(ValidationError, match="out of bounds"):
        make(src_map=[{"start": 0, "end": 99}])
    with pytest.raises(ValidationError, match="before start"):
        make(src_map=[{"start": 5, "end": 2}])
    with pytest.raises(ValidationError, match="alternative of itself"):
        make(alt_of="u0")


def test_narration_plan_rejects_duplicate_utterance_ids() -> None:
    u = ir.Utterance(id="u0", element_id="e1", kind=ir.UtteranceKind.SENTENCE, spoken="Hi.")
    with pytest.raises(ValidationError, match="not unique"):
        ir.NarrationPlan(doc_id="0" * 64, utterances=[u, u])


TIMELINE_MUTATIONS = [
    (_dup("segments"), "segment ids are not unique"),
    (_set(["utterances", 0, "segment_id"], "a9"), "unknown segment"),
    (_set(["utterances", 0, "end_sample"], -5), "greater than or equal to 0"),
    (_set(["utterances", 1, "end_sample"], 20_000), "end before start"),
    (_set(["chapters", 0, "segment_id"], "a9"), "unknown segment"),
    (_set(["chapters", 0, "start_sample"], 99_000), "past the end"),
    (
        _set(
            ["reference_events"],
            [{"utterance_id": "u0", "target_element_id": "e2", "segment_id": "a9", "at_sample": 0}],
        ),
        "unknown segment",
    ),
    (
        _set(
            ["reference_events"],
            [
                {
                    "utterance_id": "u0",
                    "target_element_id": "e2",
                    "segment_id": "a0",
                    "at_sample": 99_000,
                }
            ],
        ),
        "past the end",
    ),
    (
        _set(
            ["utterances", 0, "words"],
            [{"char_start": 0, "char_end": 2, "start_sample": 100, "end_sample": 50}],
        ),
        "runs backwards",
    ),
    (
        _set(
            ["utterances", 0, "words"],
            [{"char_start": 0, "char_end": 2, "start_sample": 0, "end_sample": 30_000}],
        ),
        "out of range",
    ),
]


@pytest.mark.parametrize(("mutate", "message"), TIMELINE_MUTATIONS)
def test_broken_timeline_is_rejected(mutate, message: str) -> None:
    data = make_timeline().model_dump()
    mutate(data)
    with pytest.raises(ValidationError, match=message):
        ir.Timeline.model_validate(data)
