# PodPaper

Turn a PDF of a scientific article into an interactive audiobook, with the
math read aloud. Runs locally on Apple silicon. This is a from-scratch rebuild
of the 2020 project; see [PLAN.md](PLAN.md) for the design and milestones.

Status: milestone M0 (bootstrap). Nothing is usable yet.

## Setup

    brew install uv node ffmpeg espeak-ng ollama
    uv sync --extra models
    (cd podpaper/node && npm ci)
    uv run prek install && uv run prek install --hook-type pre-push
    uv run pytest                      # fast tests, no models

Model smoke tests need Ollama running and about 20 GB of downloads:

    ollama serve &
    ollama pull glm-ocr && ollama pull qwen3.8:27b-q4_K_M
    uv run pytest -m models tests/smoke

Decision records are in `docs/adr/`; licences are in `LICENSES.md`.
