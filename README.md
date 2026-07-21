# PodPaper

Turn a PDF of a scientific article into an interactive audiobook, with the
math read aloud. Runs locally on Apple silicon. This is a from-scratch rebuild
of the 2020 project; see [PLAN.md](PLAN.md) for the design and milestones.

Status: milestone M0 (bootstrap). Nothing is usable yet.

## Setup

    brew install uv node ffmpeg espeak-ng ollama
    uv sync
    uv run pytest
