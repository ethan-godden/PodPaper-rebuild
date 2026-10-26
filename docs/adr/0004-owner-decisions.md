# 0004: Owner decisions

Status: accepted on 2026-11-23. The owner accepted the recommended default for
all six decisions in PLAN.md ("Open decisions for the owner"). M0 had already
proceeded on those defaults.

| # | Decision | Default in use | What M0 did on that basis | Owner answer |
|---|---|---|---|---|
| 1 | Public or private repository, and licence | Private, MIT | Local repository only, no remote. `LICENSE` is MIT. Legacy fixtures are kept out of git because they name private individuals and include third-party lecture notes. | Default accepted, 2026-11-23 |
| 2 | What "with PyTorch" binds | Every model we train is PyTorch; pretrained LLM and OCR inference may run in Ollama | Layout and speech run in PyTorch. Qwen3.8-27B and GLM-OCR run through Ollama. | Default accepted, 2026-11-23 |
| 3 | arXiv network fetching | Allowed for the training corpus after the terms check; off at runtime unless opted in | Terms check done (ADR 0001). No corpus fetch has been run. ADR 0001 adds a sub-question: proceed on the robots.txt reading, or ask arXiv first. | Default accepted, 2026-11-23 |
| 4 | Rented-GPU spend | Yes, capped at tens of dollars per run, after a local pilot | Nothing rented. | Default accepted, 2026-11-23 |
| 5 | How many owned models to commit to | MathSpan committed, DocStruct expected, the others on triggers | Nothing trained yet. | Default accepted, 2026-11-23 |
| 6 | Ship without a vector database if the M10 test shows no benefit | Yes | No vector database installed. | Default accepted, 2026-11-23 |

One point is not covered by that answer. ADR 0001 adds a sub-question to
decision 3: fetch from the arXiv website on the robots.txt reading (option a),
or ask arXiv first (option b). The record's recommendation, option (a) for the
400-paper slice in M4 and bulk-storage PDFs with website HTML for the
3,000-paper corpus in M7, is the working default. Confirm it with the owner
before the first corpus fetch in M4; no fetch has been run.

The repository stays private and local (no remote) and MIT-licensed. Legacy
fixtures stay out of git.
