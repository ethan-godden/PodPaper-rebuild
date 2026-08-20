# 0003: M0 model smoke results

Date: 2026-11-23. Machine: Apple M3 Max, 128 GB, macOS.

## Context

M0 requires that each default model loads and produces output on this machine.
PLAN.md marked several of these as assumptions "(verify)". These are the
results of actually running them. Timings are single cold-ish runs taken while
other downloads were in progress; they show that a thing works, not how fast
it is. Proper measurements belong to the M1 spikes.

## Findings

Installed: uv 0.13.9, Python 3.12.16, Node 26.13.1, ffmpeg 9.0.2,
espeak-ng 1.52.0, Ollama 0.40.17, torch 2.15.0, transformers 5.24.0,
kokoro (PyPI, with `en-core-web-sm` 3.8.0 pinned so it is not fetched at run time).

| Check | Result |
|---|---|
| PyTorch on MPS | Works. |
| pypdfium2 on legacy `test.pdf` | Renders at 200 dpi (1700 x 2200) and returns a text layer. The file has 140 pages. |
| PP-DocLayoutV3 (`PaddlePaddle/PP-DocLayoutV3_safetensors`, transformers) | Loads and runs on CPU and on MPS without the MPS fallback flag. 25 class ids. Post-processing returns `order_seq` (reading order) and polygons. Needs `torchvision` and OpenCV, which the plan did not list. |
| Formula classes in PP-DocLayoutV3 | Two different class ids are both named `formula` in `id2label` (likely display and inline). Which is which is not yet confirmed. |
| Kokoro-82M, voice `af_heart` | Works on CPU and MPS, 24 kHz audio, word-level start and end times on both. In this one short test CPU was faster than MPS (about 3x real time against about 1x); first-call cost dominates, so this is not a benchmark. |
| GLM-OCR (`glm-ocr`, Ollama, llama.cpp runner) | Reads the title page text from a rendered page crop. About 1.9 GB loaded. |
| Qwen3.8-27B default tag (`qwen3.8:27b`) | This tag is an MLX build (nvfp4). Plain chat and `think: false` work. Any `format` value (JSON mode or a JSON schema) returns HTTP 501 "structured output is unavailable". |
| Qwen3.8-27B GGUF (`qwen3.8:27b-q4_K_M`, llama.cpp runner) | Schema-constrained output works, including with one image attached and `think: false`. About 15 GB loaded at an 8K context. About 20 tokens per second generation in one run. |
| Offline | Local-model smoke tests pass with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` and `uv run --offline`. Not yet tested with the network interface actually disabled. |

## Decision

- Use `qwen3.8:27b-q4_K_M` (GGUF) as the LLM for every schema-constrained
  call. The MLX default tag cannot be used for those in Ollama 0.40.17.
- Keep PP-DocLayoutV3 through transformers on MPS as the layout default.
- Keep Kokoro-82M as the default speech candidate. Choose CPU or MPS from a
  real measurement in the M1 spike.

## Consequences

- The plan's memory figure for the 27B model (18 GB) applies to the MLX tag;
  the GGUF build is 17 GB on disk. Both are currently downloaded; the MLX tag
  can be removed with `ollama rm qwen3.8:27b` if it is not wanted for free-text calls.
- Ollama is started by hand (`ollama serve`); it is not installed as a login service.
- Open for M1: which `formula` id is inline; throughput of each model;
  a true network-off run; the 40k-token prompt test.

Reproduce with `uv sync --extra models && uv run pytest -m models tests/smoke`.
