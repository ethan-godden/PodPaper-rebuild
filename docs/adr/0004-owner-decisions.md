# 0004: Owner decisions

Status: open. None of the six decisions in PLAN.md ("Open decisions for the
owner") has been answered yet. M0 proceeded on the recommended defaults below
so that work was not blocked; every one of them is cheap to reverse now.

| # | Decision | Default in use | What M0 did on that basis | Owner answer |
|---|---|---|---|---|
| 1 | Public or private repository, and licence | Private, MIT | Local repository only, no remote. `LICENSE` is MIT. Legacy fixtures are kept out of git because they name private individuals and include third-party lecture notes. | pending |
| 2 | What "with PyTorch" binds | Every model we train is PyTorch; pretrained LLM and OCR inference may run in Ollama | Layout and speech run in PyTorch. Qwen3.8-27B and GLM-OCR run through Ollama. | pending |
| 3 | arXiv network fetching | Allowed for the training corpus after the terms check; off at runtime unless opted in | Terms check done (ADR 0001). No corpus fetch has been run. ADR 0001 adds a sub-question: proceed on the robots.txt reading, or ask arXiv first. | pending |
| 4 | Rented-GPU spend | Yes, capped at tens of dollars per run, after a local pilot | Nothing rented. | pending |
| 5 | How many owned models to commit to | MathSpan committed, DocStruct expected, the others on triggers | Nothing trained yet. | pending |
| 6 | Ship without a vector database if the M10 test shows no benefit | Yes | No vector database installed. | pending |

Record each answer here with its date. When decision 1 is answered, drop
"pending owner decision" from the licence wording; when decision 3 is
answered, set ADR 0001 to Accepted.
