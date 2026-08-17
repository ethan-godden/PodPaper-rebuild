"""M0 smoke tests: every default model loads and produces output.

Slow, and they need downloaded weights plus a running Ollama server, so they
are excluded by default. Run with:

    uv sync --extra models
    uv run pytest -m models tests/smoke
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.models

ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT / "data" / "fixtures-legacy"
LAYOUT_MODEL = "PaddlePaddle/PP-DocLayoutV3_safetensors"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
LLM = "qwen3.8:27b-q4_K_M"  # GGUF build: the default MLX tag refuses structured output
OCR = "glm-ocr"


def test_torch_runs_on_mps() -> None:
    torch = pytest.importorskip("torch")
    assert torch.backends.mps.is_available()
    x = torch.randn(256, 256, device="mps")
    assert torch.isfinite((x @ x).sum()).item()


def _legacy_page(index: int):
    pdfium = pytest.importorskip("pypdfium2")
    path = LEGACY / "test.pdf"
    if not path.exists():
        pytest.skip("legacy fixtures are not present (see tests/fixtures/legacy/README.md)")
    pdf = pdfium.PdfDocument(path)
    try:
        page = pdf[index]
        image = page.render(scale=200 / 72).to_pil().convert("RGB")
        text = page.get_textpage().get_text_range()
        page.close()
    finally:
        pdf.close()
    return image, text


def test_pdf_renders_and_has_a_text_layer() -> None:
    image, text = _legacy_page(0)
    assert image.size == (1700, 2200)
    assert "Fermat" in text or "FERMAT" in text


@pytest.mark.parametrize("device", ["cpu", "mps"])
def test_layout_model_detects_blocks_with_reading_order(device: str) -> None:
    torch = pytest.importorskip("torch")
    from transformers import AutoImageProcessor, AutoModelForObjectDetection

    image, _ = _legacy_page(9)
    processor = AutoImageProcessor.from_pretrained(LAYOUT_MODEL)
    model = AutoModelForObjectDetection.from_pretrained(LAYOUT_MODEL).to(device).eval()
    assert len(model.config.id2label) == 25

    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    result = processor.post_process_object_detection(
        outputs, threshold=0.5, target_sizes=[image.size[::-1]]
    )[0]

    labels = {model.config.id2label[int(i)] for i in result["labels"]}
    assert len(result["boxes"]) >= 3
    assert "text" in labels
    assert "order_seq" in result, "the transformers port should return reading order"
    assert len(result["order_seq"]) == len(result["boxes"])


@pytest.mark.parametrize("device", ["cpu", "mps"])
def test_kokoro_speaks_with_word_timestamps(device: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    kokoro = pytest.importorskip("kokoro")

    pipeline = kokoro.KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device=device)
    results = list(pipeline("The energy equals m c squared.", voice="af_heart"))

    n_samples = sum(len(r.audio) for r in results)
    assert n_samples > 24_000, "expected more than one second of 24 kHz audio"
    words = [t for r in results for t in (r.tokens or []) if t.start_ts is not None]
    assert [w.text for w in words][:3] == ["The", "energy", "equals"]
    assert all(w.end_ts >= w.start_ts for w in words)


def _ollama(payload: dict) -> dict:
    httpx = pytest.importorskip("httpx")
    try:
        tags = httpx.get(f"{OLLAMA}/api/tags", timeout=5).json()
    except httpx.HTTPError:
        pytest.skip("Ollama is not running (start it with `ollama serve`)")
    names = {m["name"] for m in tags["models"]}
    model = payload["model"]
    if model not in names and f"{model}:latest" not in names:
        pytest.skip(f"model {model} is not pulled (run `ollama pull {model}`)")
    response = httpx.post(f"{OLLAMA}/api/chat", json={**payload, "stream": False}, timeout=600)
    response.raise_for_status()
    return response.json()


def test_llm_returns_schema_constrained_json() -> None:
    schema = {
        "type": "object",
        "properties": {
            "spoken": {"type": "string"},
            "symbols": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["spoken", "symbols"],
    }
    reply = _ollama(
        {
            "model": LLM,
            "think": False,
            "format": schema,
            "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [
                {
                    "role": "user",
                    "content": "Read this LaTeX aloud in plain English words and list its symbols: "
                    r"\frac{a}{b} = c",
                }
            ],
        }
    )
    data = json.loads(reply["message"]["content"])
    assert set(data) == {"spoken", "symbols"}
    assert data["spoken"].strip()
    assert not set(data["spoken"]) & set("\\$^_{}")


def test_ocr_model_reads_a_rendered_page_region() -> None:
    image, _ = _legacy_page(0)
    crop = image.crop((0, 0, image.width, image.height // 2))
    buffer = io.BytesIO()
    crop.save(buffer, format="PNG")
    reply = _ollama(
        {
            "model": OCR,
            "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [
                {
                    "role": "user",
                    "content": "Text Recognition:",
                    "images": [base64.b64encode(buffer.getvalue()).decode()],
                }
            ],
        }
    )
    out = reply["message"]["content"]
    assert "Fermat" in out or "FERMAT" in out, out[:300]
