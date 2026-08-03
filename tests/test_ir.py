"""IR v0: a small valid document round-trips, and broken references are rejected."""

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
