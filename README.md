# PodPaper

Turn a PDF of a scientific article into an interactive audiobook, with the
math read aloud. Runs locally on Apple silicon. This is a from-scratch rebuild
of the 2020 project; see [PLAN.md](PLAN.md) for the design and milestones.

Status: milestone M0 (bootstrap) is complete; M1 (walking skeleton) is next. Nothing is usable yet.

## Setup

Needs macOS on Apple silicon, Homebrew, and Ollama 0.40.17 or newer (`ollama --version`).

    brew install uv node ffmpeg espeak-ng ollama
    uv sync --extra models             # plain `uv sync` is enough for the fast tests
    (cd podpaper/node && npm ci)
    uv run prek install                # pre-commit and pre-push hooks

## Checks

    uv run pytest                      # fast tests, no models
    uv run ruff format --check . && uv run ruff check . && uv run ty check

## Model smoke tests

These need about 37 GB of downloads and the legacy fixtures, which are not in git
(restore them as described in `tests/fixtures/legacy/README.md`).

    ollama serve &
    ollama pull glm-ocr
    ollama pull qwen3.8:27b-q4_K_M     # the default qwen3.8:27b tag cannot do JSON-schema output
    PODPAPER_SMOKE_DOWNLOAD=1 uv run pytest -m models tests/smoke    # first run: fetches PP-DocLayoutV3 and Kokoro-82M
    PODPAPER_SMOKE_STRICT=1 uv run pytest -m models tests/smoke      # the gate: nothing may skip

## Working offline

After the steps above everything runs without a network, but uv must be told not to look:

    uv sync --extra models --offline
    (cd podpaper/node && npm ci --offline)
    HF_HUB_OFFLINE=1 uv run --offline pytest -m models tests/smoke

Decision records are in `docs/adr/`; licences are in `LICENSES.md`.
