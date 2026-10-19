# Licences and attribution

M0 licence table for every model, voice, dataset and tool that `PLAN.md` names for v1 and the bake-offs.
Checked on 2026-11-23. This is an engineering record, not legal advice.

How to read it:

- **Status** is `checked 2026-11-23` only where the primary source (repo LICENSE file, model or dataset card, PyPI/npm/Homebrew metadata) was opened on that date. Everything else is `unverified`.
- **Source** names what was opened: `PyPI` = `https://pypi.org/pypi/<name>/json`, `npm` = `https://registry.npmjs.org/<name>/latest`, `HF` = the Hugging Face card metadata and README of the named repo, `brew` = `https://formulae.brew.sh/api/formula/<name>.json`, `GH` = the LICENSE file in the named GitHub repo.
- **Commercial** = commercial use allowed by the licence. **Outputs** = whether what the tool or model produces (audio, text, embeddings, rendered pages) can be redistributed without the licence attaching to it. For software and model-weight licences here, outputs are not covered by the licence unless a row says otherwise; the content of the *input* paper still carries its own copyright.
- Versions are the latest seen in the registry on the check date, not pins. Pins live in `uv.lock` and `package.json` once the dependency is added.
- Transitive dependencies are not enumerated. The rows below are the things the plan names, plus the transitive parts that are copyleft.

PodPaper's own code is MIT (`LICENSE`). Attribution for the 2020 original is in `ATTRIBUTION.md`.

## Summary of findings

1. **The English speech path loads GPL code in-process.** `kokoro` hard-depends on `misaki[en]`, which hard-depends on `phonemizer-fork` (GPL-3.0-or-later), `espeakng-loader` and `num2words` (LGPL-2.1-or-later). `kokoro/pipeline.py` imports `misaki.espeak` at module import, and that module imports `phonemizer` and points it at an espeak-ng library (GPL-3.0-or-later). See "Copyleft in the speech stack".
2. **Homebrew ffmpeg is GPL-3.0-or-later**, not LGPL. The installed build is configured with `--enable-gpl --enable-version3` and links x264 and x265. PodPaper calls it as a separate program, so this binds only if ffmpeg itself is redistributed. `PLAN.md` does not list ffmpeg among the copyleft parts.
3. **Ghostscript is AGPL-3.0-or-later.** It is in the CDM scorer's dependency list. The plan excludes PyMuPDF for being AGPL; Ghostscript is the same licence family, kept acceptable only because it is an offline, evaluation-only command-line tool in its own environment and is never imported or shipped.
4. **MinerU is not under a standard open-source licence.** PyPI declares `LicenseRef-MinerU-Open-Source-License`: Apache-2.0 plus additional terms (commercial-licence thresholds, an attribution duty for online services, termination). This matters for the M3 adopt rule ("licence permitting").
5. **OmniDocBench data is research-only, non-commercial.** The repo code is Apache-2.0 but the dataset card and README say "for research purposes only and not for commercial use". The plan had "licence: verify".
6. **OvisOCR3 is Apache-2.0** (plan had "licence: verify").
7. **MathBridge's MIT tag has nothing behind it.** The dataset card README is empty: no provenance, no source list. The plan's "provenance: verify" remains open.
8. **unarXive's open subset is CC-BY-SA-4.0** (share-alike). Using it as the corpus fallback would put a share-alike duty on any redistributed derived dataset.
9. **Kokoro-82M names a StyleTTS 2 checkpoint as its base model.** The card metadata has `base_model: yl4579/StyleTTS2-LJSpeech`. That repo carries no licence, and the StyleTTS 2 README puts a disclosure condition on its pre-trained models (tell listeners the speech is synthesised, unless you have permission to use the voice). Whether Kokoro's weights were initialised from that checkpoint or only share the architecture is not stated. Labelling PodPaper audio as synthesised meets the condition either way.
10. **embeddinggemma-2 is Apache-2.0 plus a use policy.** Its card says deployments must adhere to the Gemma Prohibited Use Policy. Gemma 4 is different: Google's Gemma Terms of Use page says those terms do not apply to Gemma 4, which is Apache-2.0 only.
11. Small corrections to the plan's wording: espeak-ng is GPL-3.0-**or-later** (plan: "GPL-3"); num2words is LGPL-**2.1-or-later** (plan: "LGPL"). No licence in the plan was found to be outright wrong.

## Runtime dependencies

### Python and system

| Name (version seen) | Role in PodPaper | Licence (SPDX) | Source | Commercial | Outputs | Duties | Status |
|---|---|---|---|---|---|---|---|
| CPython 3.12 | Interpreter | PSF-2.0 | GH `python/cpython` `3.12/LICENSE` | Yes | Yes | Keep notice if redistributed | checked 2026-11-23 |
| uv (0.13.9) | Environment and lockfile | MIT OR Apache-2.0 | PyPI `uv`; brew `uv` | Yes | Yes | Notice | checked 2026-11-23 |
| torch (2.15.0) | Framework for layout, speech, embeddings, training | PyPI licence expression for the wheel: `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND ISC AND MIT AND Zlib` (PyTorch plus bundled parts; all permissive) | PyPI `torch` | Yes | Yes | Notices if the wheel is redistributed | checked 2026-11-23 |
| transformers (5.24.0) | Model loading, layout inference, HF Trainer | Apache-2.0 | PyPI `transformers` | Yes | Yes | Notice; state changes | checked 2026-11-23 |
| torchvision (0.29.2) | Image processor backend required by the PP-DocLayoutV3 transformers port | BSD-3-Clause (wheel metadata says "BSD") | Installed wheel metadata | Yes | Yes | Notice | metadata read 2026-11-23; LICENSE file not opened |
| opencv-python-headless (5.1.0.95) | Polygon post-processing required by the PP-DocLayoutV3 transformers port | Apache-2.0; the wheel is reported to bundle LGPL FFmpeg libraries | Installed wheel metadata | Yes | Yes | Notice; LGPL terms for bundled libraries if redistributed | metadata read 2026-11-23; bundled libraries unverified |
| pillow (13.0.0) | Image handling | MIT-CMU | Installed wheel metadata | Yes | Yes | Notice | metadata read 2026-11-23 |
| soundfile (0.14.0) | Audio file writing | BSD-3-Clause; the wheel is reported to bundle libsndfile (LGPL-2.1) | Installed wheel metadata | Yes | Yes | Notice; LGPL terms for libsndfile if redistributed | metadata read 2026-11-23; bundled library unverified |
| httpx (0.28.1) | HTTP client for the Ollama API | BSD-3-Clause | Installed wheel metadata | Yes | Yes | Notice | metadata read 2026-11-23 |
| en-core-web-sm (3.8.0) | spaCy English pipeline that Kokoro's text front end loads | MIT (package metadata); licences of its training sources not checked | Installed wheel metadata | Yes | Yes | Notice | metadata read 2026-11-23 |
| peft (0.22.0) | LoRA, only if a verbalizer larger than 0.8B is trained | Apache-2.0 | PyPI `peft` | Yes | Yes | Notice | checked 2026-11-23 |
| lightning (2.6.6) | Lightning Fabric loops for MathSpan, DocStruct, TrustGate | Apache-2.0 | PyPI `lightning` | Yes | Yes | Notice | checked 2026-11-23 |
| trackio (0.45.1) | Experiment tracking | MIT | PyPI `trackio`; GH `gradio-app/trackio` LICENSE (copyright line is the placeholder "Your Name") | Yes | Yes | Notice | checked 2026-11-23 |
| huggingface_hub (2.4.0) | Model download, private backup | Apache-2.0 | PyPI `huggingface_hub` | Yes | Yes | Notice | checked 2026-11-23 |
| pypdfium2 (5.15.2) | S0 rendering and text layer | Apache-2.0 OR BSD-3-Clause for the binding; the wheel bundles PDFium (BSD-style) and about 30 third-party licence texts (FreeType, HarfBuzz, ICU, libjpeg-turbo, OpenJPEG, libpng, libtiff, lcms, zlib, abseil and others) | PyPI `pypdfium2` (`license_files` list); GH `pypdfium2-team/pypdfium2` README "Licensing" | Yes | Yes | PDFium and dependency licence texts must ship with any binary redistribution | checked 2026-11-23 |
| pydantic (2.14.4), pydantic-settings (2.16.3), typer (0.29.2) | IR models, config, CLI | MIT | PyPI | Yes | Yes | Notice | checked 2026-11-23 |
| fastapi (0.165.0) | API | MIT | PyPI `fastapi` | Yes | Yes | Notice | checked 2026-11-23 |
| uvicorn (0.54.0) | ASGI server | BSD-3-Clause | PyPI `uvicorn` | Yes | Yes | Notice | checked 2026-11-23 |
| SSE library | Progress events | Not chosen. `sse-starlette` (3.7.1) is BSD-3-Clause per PyPI | PyPI `sse-starlette` | Yes | Yes | Notice | checked 2026-11-23 (candidate only) |
| SQLite (3.54.1) | Jobs, events, caches, FTS5 | Public domain (Homebrew id: `blessing`) | `https://www.sqlite.org/copyright.html`; brew `sqlite` | Yes | Yes | None | checked 2026-11-23 |
| Ollama (0.40.17) | Local LLM/VLM server | MIT | GH `ollama/ollama` LICENSE; brew `ollama` | Yes | Yes | Notice | checked 2026-11-23 |
| llama.cpp | Fallback runner for GGUF OCR models | MIT | GH `ggml-org/llama.cpp` LICENSE; brew `llama.cpp` | Yes | Yes | Notice | checked 2026-11-23 |
| mlx-vlm (0.8.0) | Fallback runner, GLM-OCR only | MIT | PyPI `mlx-vlm`; GH `Blaizzy/mlx-vlm` LICENSE | Yes | Yes | Notice | checked 2026-11-23 |
| mlx-audio (0.6.7) | Speech bake-off runner | MIT | PyPI `mlx-audio`; GH `Blaizzy/mlx-audio` LICENSE | Yes | Yes | Notice | checked 2026-11-23 |
| kokoro (0.9.4) | S8 speech inference library | Apache-2.0 | PyPI `kokoro`; GH `hexgrad/kokoro` LICENSE | Yes | Yes | Notice. Pulls in the copyleft rows below | checked 2026-11-23 |
| misaki (0.9.4) | Grapheme-to-phoneme, pronunciation overrides | Apache-2.0 | PyPI `misaki`; GH `hexgrad/misaki` LICENSE | Yes | Yes | Notice. `misaki[en]` requires phonemizer-fork, espeakng-loader, num2words, spacy | checked 2026-11-23 |
| **num2words** (0.5.14) | Number normalisation (ours and inside misaki) | **LGPL-2.1-or-later** | PyPI `num2words`; GH `savoirfairelinux/num2words` COPYING and source header | Yes | Yes | Weak copyleft: see below | checked 2026-11-23 |
| **phonemizer-fork** (3.3.2) | espeak wrapper imported by misaki | **GPL-3.0-or-later** | PyPI `phonemizer-fork` classifier ("GNU General Public License v3 or later (GPLv3+)"); the PyPI project URLs all point to the upstream `bootphon/phonemizer`, whose LICENSE and README were read and agree. The fork's own repo LICENSE was not located (`thewh1teagle/phonemizer-fork` LICENSE returns 404 on `main` and `master`) | Yes | Yes | Strong copyleft: see below | checked 2026-11-23 |
| **espeakng-loader** (0.2.4) | Provides the espeak-ng shared library and data path to misaki | MIT for the loader code (GH LICENSE, (c) 2025 thewh1teagle). PyPI metadata has no licence field and no classifiers. The wheels are platform-specific and about 10 MB each (macOS arm64 9,892,565 bytes; manylinux x86_64 10,078,484; win_amd64 9,437,292), and the README says the package "loads the espeak-ng shared library" and exposes `get_library_path()` and `get_data_path()`. **Treat the wheel as carrying GPL-3.0-or-later espeak-ng binaries and data** | GH `thewh1teagle/espeakng-loader` LICENSE; PyPI `espeakng-loader` (file list and README) | Yes | Yes | Strong copyleft on the wheel's contents: see below. Remaining check: list the installed wheel's files in M0 to confirm the bundled library and whether a GPL notice ships with it | checked 2026-11-23 (loader licence and registry metadata; wheel contents not listed) |
| **espeak-ng** (1.52.0) | Pronunciation fallback for out-of-dictionary words | **GPL-3.0-or-later** (a BSD-2-Clause `getopt` file aside) | GH `espeak-ng/espeak-ng` COPYING and README "License Information"; brew `espeak-ng` | Yes | Yes | Strong copyleft: see below | checked 2026-11-23 |
| spacy (3.8.18), spacy-curated-transformers (2.1.2) | Tokeniser and tagger inside misaki | MIT | PyPI | Yes | Yes | Notice | checked 2026-11-23 |
| spaCy English pipeline (`en_core_web_sm` or `_trf`) | Model data loaded by misaki | MIT is what spaCy publishes; not opened | n/a | n/a | n/a | n/a | unverified |
| **ffmpeg** (9.0.2, Homebrew) | S9 audio assembly and export | Upstream default LGPL-2.1-or-later; the **Homebrew build is GPL-3.0-or-later** (`--enable-gpl --enable-version3`, libx264, libx265) | brew `ffmpeg`; local `ffmpeg -version`; GH `FFmpeg/FFmpeg` LICENSE.md | Yes | Yes | Called as a subprocess. Binds only if the binary is redistributed. AAC/MP3 patent questions are separate from copyright and not assessed | checked 2026-11-23 |
| lancedb (0.41.0) | Library index, only if it wins the M10 test | Apache-2.0 | PyPI `lancedb`; GH `lancedb/lancedb` LICENSE | Yes | Yes | Notice | checked 2026-11-23 |
| Hugging Face Hub, HF Jobs, Modal | Backup and rented GPU | Services under terms of use, not licences. The `modal` client (1.6.4) is Apache-2.0 per PyPI | PyPI `modal` | n/a | n/a | Service terms not read | unverified (terms) |
| DBOS (`dbos` 3.6.0) | Named upgrade path for orchestration, not used | MIT | PyPI `dbos`; GH `dbos-inc/dbos-transact-py` LICENSE | Yes | Yes | Notice | checked 2026-11-23 |

### Node and web player

| Name (version seen) | Role in PodPaper | Licence (SPDX) | Source | Commercial | Outputs | Duties | Status |
|---|---|---|---|---|---|---|---|
| Node.js (26.13.1) | Runs the MathJax/SRE bridge and the web build | MIT (with bundled third-party notices) | GH `nodejs/node` LICENSE; brew `node` | Yes | Yes | Notice | checked 2026-11-23 |
| MathJax 4 (`mathjax` 4.1.3, `@mathjax/src` 4.1.3) | LaTeX to MathML, parse check, semantic tree | Apache-2.0 | npm; GH `mathjax/MathJax` LICENSE | Yes | Yes | Notice. `@mathjax/src` depends on `speech-rule-engine` 5.0.0-rc.4 and `@mathjax/mathjax-newcm-font` (font licence not opened) | checked 2026-11-23 |
| speech-rule-engine (4.1.5 standalone) | Rule readings (ClearSpeak, MathSpeak) | Apache-2.0 | npm; GH `Speech-Rule-Engine/speech-rule-engine` LICENSE | Yes | Yes | Notice | checked 2026-11-23 |
| react, react-dom (19.3.1) | Player UI | MIT | npm | Yes | Yes | Notice | checked 2026-11-23 |
| vite (8.3.8) | Web build | MIT | npm | Yes | Yes | Notice | checked 2026-11-23 |
| react-pdf (11.1.0) | PDF view | MIT | npm | Yes | Yes | Notice | checked 2026-11-23 |
| pdfjs-dist (6.5.438) | PDF rendering in the browser | Apache-2.0 | npm | Yes | Yes | Notice | checked 2026-11-23 |
| katex (0.19.1) | Math rendering in the player | MIT (bundled KaTeX fonts: licence not opened) | npm | Yes | Yes | Notice | checked 2026-11-23 |
| Player fonts ("fonts bundled locally") | UI typography | Not chosen | n/a | n/a | n/a | n/a | unverified |
| Tauri 2 (`@tauri-apps/api` 2.12.5) | M11 conditional desktop wrapper | Apache-2.0 OR MIT | npm | Yes | Yes | Notice | checked 2026-11-23 |

### Development tools

| Name (version seen) | Role | Licence (SPDX) | Source | Status |
|---|---|---|---|---|
| pytest (9.2.0) | Tests | MIT | PyPI | checked 2026-11-23 |
| ruff (0.17.6) | Lint and format | MIT | PyPI | checked 2026-11-23 |
| ty (0.0.108) | Type check | MIT | PyPI classifier | checked 2026-11-23 |
| prek (0.5.11) | Git hooks | MIT | PyPI | checked 2026-11-23 |
| hatchling (1.33.0) | Build backend | MIT | PyPI | checked 2026-11-23 |
| Playwright (`playwright` 1.65.2, `@playwright/test` 1.65.1) | End-to-end player test | Apache-2.0 (browser binaries it downloads carry their own licences, not opened) | PyPI; npm | checked 2026-11-23 |

All are development-time only, allow commercial use, and put no condition on outputs.

## Models and voices

All rows are weights downloaded at first run and not committed to the repo. "HF" means the licence field in the card metadata and the licence text in the README were read; the commit shown is the repo head at check time. None of the repos is gated.

| Name | Role in PodPaper | Licence (SPDX) | Source | Commercial | Outputs | Duties | Status |
|---|---|---|---|---|---|---|---|
| PP-DocLayoutV3 | S1 layout and reading order | Apache-2.0 | HF `PaddlePaddle/PP-DocLayoutV3_safetensors` @ `e4f489dc53` (card tag and badge; the repo has no LICENSE file) | Yes | Yes | Notice if weights are redistributed | checked 2026-11-23 |
| Kokoro-82M v1.0 (weights) | S8 speech, default candidate | Apache-2.0 | HF `hexgrad/Kokoro-82M` @ `f3ff357179` | Yes | Yes. The card states it is deployed in commercial APIs | Notice if weights are redistributed. The card lists CC BY training audio (Koniwa `tnc`, CC BY 3.0, under 1 h; SIWIS, CC BY 4.0, under 11 h): credit both in `ATTRIBUTION.md`. The card metadata also declares `base_model: yl4579/StyleTTS2-LJSpeech`; see the next row | checked 2026-11-23 (card); relation to the StyleTTS 2 checkpoint unverified |
| StyleTTS2-LJSpeech (declared base model of Kokoro-82M) | Upstream lineage of the speech model; not downloaded by PodPaper | Code: MIT (`yl4579/StyleTTS2` LICENSE, (c) 2023 Aaron (Yinghao) Li). **Pre-trained models: a non-standard condition in the README**: users agree to tell listeners that speech is synthesised by the pre-trained models unless they have permission to use the voice. The HF checkpoint repo has no licence tag, no card and no LICENSE file. LJSpeech audio is usually described as public domain; not opened | HF `yl4579/StyleTTS2-LJSpeech` @ `359e81ba0d` (API metadata: licence none); GH `yl4579/StyleTTS2` README "License" and LICENSE; HF `hexgrad/Kokoro-82M` card metadata | Yes for the code. For the checkpoint: no stated restriction other than the disclosure condition | Yes, subject to the disclosure condition if it reaches Kokoro | The Kokoro README cites StyleTTS 2 only as its architecture and does not say whether the weights were initialised from this checkpoint, so whether the condition passes to Kokoro is open. Disclosing PodPaper audio as synthesised (in the player and in exported file metadata) satisfies it either way | checked 2026-11-23 (README condition, missing tag, Kokoro `base_model`); weight derivation and LJSpeech licence unverified |
| Kokoro voices (American `af_*`/`am_*`, British `bf_*`/`bm_*` voice packs) | Narration voices | Apache-2.0, as part of the Kokoro-82M repo. `VOICES.md` gives no per-voice licence for the English voices; a "CC BY" column appears only in non-English tables. The card says training audio was public-domain, permissively licensed, or synthetic audio from closed TTS providers | HF `hexgrad/Kokoro-82M` `VOICES.md` and README "Training Details" | Yes | Yes | None beyond the row above. Which voice ships as default is not decided | checked 2026-11-23 |
| Kokoro-82M MLX build | Speech bake-off through mlx-audio | Apache-2.0 | HF `mlx-community/Kokoro-82M-bf16` @ `a71e4d38b2` | Yes | Yes | Notice | checked 2026-11-23 |
| Qwen3-TTS (12Hz 0.6B / 1.7B, CustomVoice) | Speech bake-off candidate | Apache-2.0 | HF `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` @ `0c0e3051f1`, `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` @ `85e237c12c`; GH `QwenLM/Qwen3-TTS` LICENSE | Yes | Yes | Notice. The plan does not say which variant or preset voice; preset-voice terms were not looked for | checked 2026-11-23 |
| Qwen3-ForcedAligner-0.6B-hf | Fallback for word timestamps | Apache-2.0 | HF `Qwen/Qwen3-ForcedAligner-0.6B-hf` @ `c07281df29` | Yes | Yes | Notice | checked 2026-11-23 |
| Qwen3.8-27B | Structure call, glossary, natural and gist readings, figure descriptions, ask-the-paper, distillation teacher | Apache-2.0 | HF `Qwen/Qwen3.8-27B` @ `37561816e6` (LICENSE file: Apache 2.0, "Copyright 2026 Alibaba Cloud") | Yes | Yes, including use of outputs as training targets | Notice. Ollama library build `qwen3.8:27b`: the registry manifest has a licence layer `sha256:4c6a8e842ef0d8504549facfb03f1273a8d0022991519bc1888522cc1a5517d1` whose content is the Apache License 2.0 text (model layer `sha256:f5f1dd8920d4...`). Any other quantisation or MLX build must be checked separately | checked 2026-11-23 (HF card and Ollama `27b` manifest) |
| Gemma 4 31B-it | Judge, evaluation and data filtering only | Apache-2.0 | HF `google/gemma-4-31B-it` @ `842da3794e` (card: "License: Apache 2.0", `license_link` redirects to `https://gemma.ai/resources/apache-2/`, which is the Apache 2.0 text) | Yes | Yes | Notice. Apache-2.0 only: Google's Gemma Terms of Use page (`https://gemma.ai/resources/terms/`) says "The terms below apply to Gemma models listed in the Appendix" and "For Gemma 4 terms, see the Gemma 4 license"; the appendix does not list Gemma 4, and the model card does not mention the terms or the prohibited-use policy. Ollama library build `gemma4:31b`: licence layer `sha256:7339fa418c9ad3e8e12e74ad0fd26a9cc4be8703f9c110728a992b193be85cb2`, content is the Apache License 2.0 text (model layer `sha256:cd20f2b3f2e3...`) | checked 2026-11-23 (HF card, Gemma terms page, Ollama `31b` manifest) |
| GLM-OCR | OCR bake-off candidate | MIT (weights); the GitHub pipeline code is Apache-2.0 | HF `zai-org/GLM-OCR` @ `2e85a62840`; GH `zai-org/GLM-OCR` LICENSE | Yes | Yes | Notice. The card asks users to comply with both MIT and PP-DocLayoutV3's Apache-2.0 when using the full pipeline | checked 2026-11-23 |
| GLM-OCR GGUF and Ollama build | Same, llama.cpp/Ollama path | Neither build declares a licence. The HF conversion repo has no licence field. The Ollama library manifest `glm-ocr:latest` has model, projector, template and params layers only, with no licence layer. MIT status rests on the upstream `zai-org/GLM-OCR` card alone | HF `ggml-org/GLM-OCR-GGUF` @ `65a42de114`; `registry.ollama.ai/v2/library/glm-ocr/manifests/latest` (model layer `sha256:33a72e292f12...`) | Presumed yes (MIT upstream) | Presumed yes | Record which build is pulled; carry the MIT notice from the upstream card ourselves | checked 2026-11-23 (absence of a licence declaration in both builds) |
| MiniCPM-OCR 1.0 (and `-gguf`) | OCR bake-off candidate | Apache-2.0 | HF `openbmb/MiniCPM-OCR-1.0` @ `883ca368d1`, `openbmb/MiniCPM-OCR-1.0-gguf` @ `0133ad8db6`; GH `OpenBMB/MiniCPM-OCR` LICENSE | Yes | Yes | Notice | checked 2026-11-23 |
| PaddleOCR-VL-1.6 (and `-GGUF`) | OCR bake-off candidate | Apache-2.0 | HF `PaddlePaddle/PaddleOCR-VL-1.6` @ `132c45f52c` (LICENSE file present), `PaddlePaddle/PaddleOCR-VL-1.6-GGUF` @ `511b09642b` | Yes | Yes | Notice | checked 2026-11-23 |
| OvisOCR3 | Optional OCR bake-off candidate | Apache-2.0 | HF `ATH-MaaS/OvisOCR3` @ `5b252386ba` (LICENSE file; README states `SPDX-License-Identifier: Apache-2.0`; base model `Qwen/Qwen3.5-0.8B`) | Yes | Yes | Notice | checked 2026-11-23 |
| LightOnOCR-3-1B (or 4B) | M11 hard-scan fallback | Apache-2.0 | HF `lightonai/LightOnOCR-3-1B` @ `23d544085c`, `lightonai/LightOnOCR-3-4B` @ `b71010f095` | Yes | Yes | Notice | checked 2026-11-23 |
| embeddinggemma-2 | S10 embedder (library milestone) | Apache-2.0 | HF `google/embeddinggemma-2` @ `f9972ac22e` | Yes | Yes | Apache-2.0 notice, and **the card requires adherence to the Gemma Prohibited Use Policy** (README: "Deployments must adhere to the Gemma Prohibited Use Policy", linking `https://ai.google.dev/gemma/prohibited_use_policy`, which redirects to `https://gemma.ai/resources/prohibited-use/`; the policy text itself was not read). Unverified: whether the Gemma Terms of Use also apply. Their appendix lists "EmbeddingGemma" with no version, so it is unclear whether version 2 is covered | checked 2026-11-23 (licence tag and card statement); Gemma Terms coverage unverified |
| Qwen3-Embedding-0.6B | One-off embedder comparison | Apache-2.0 | HF `Qwen/Qwen3-Embedding-0.6B` @ `97b0c614be` | Yes | Yes | Notice | checked 2026-11-23 |
| Qwen3-Reranker-0.6B | Conditional reranker | Apache-2.0 | HF `Qwen/Qwen3-Reranker-0.6B` @ `e61197ed45` | Yes | Yes | Notice | checked 2026-11-23 |
| granite-embedding-english-r2 | Frozen block embeddings for DocStruct | Apache-2.0 | HF `ibm-granite/granite-embedding-english-r2` @ `47ea694b25` | Yes | Yes | Notice | checked 2026-11-23 |
| Qwen3.5-0.8B-Base | Verbalizer base (full fine-tune) | Apache-2.0 | HF `Qwen/Qwen3.5-0.8B-Base` @ `dc7cdfe2ee` (LICENSE file) | Yes | Yes | Fine-tuned weights are a derivative: keep the Apache notice and state changes if they are ever published | checked 2026-11-23 |
| Qwen3.5-2B-Base | Larger verbalizer base (LoRA) | Apache-2.0 | HF `Qwen/Qwen3.5-2B-Base` @ `b1485b2fa6` (LICENSE file) | Yes | Yes | Same | checked 2026-11-23 |
| Flan-T5-base | Verbalizer ablation baseline | Apache-2.0 | HF `google/flan-t5-base` @ `7bcac572ce` | Yes | Yes | Notice | checked 2026-11-23 |
| Docling heron layout detector | M11 conditional layout fine-tune base | Apache-2.0 | HF `docling-project/docling-layout-heron` @ `8f39ad3c0b` (card tag only; README has no licence section). Its training-data licences were not checked | Yes | Yes | Notice; fine-tuned weights are a derivative | checked 2026-11-23 |
| Whisper weights | Speech round-trip check (evaluation) | `openai/whisper-large-v3`: Apache-2.0 on its card; `openai/whisper-large-v3-turbo`: MIT on its card. The code repo is MIT | HF `openai/whisper-large-v3` @ `06f233fe06`, `openai/whisper-large-v3-turbo` @ `41f01f3fe8` | Yes | Yes | Notice. Which checkpoint is used is not decided | checked 2026-11-23 |
| MathSpan, verbalizer, DocStruct, TrustGate | Owned models | Ours. Private until the owner decides. Their licence options depend on the training-data rows below | n/a | n/a | n/a | See "Datasets" | n/a |

## Datasets and benchmarks

| Name | Role in PodPaper | Licence (SPDX) | Source | Commercial | Redistribution | Duties | Status |
|---|---|---|---|---|---|---|---|
| arXiv papers (PDF and HTML) | Training corpus (400, then 3,000 papers), gold set G1 | Per paper, chosen by the author: CC-BY-4.0, CC-BY-SA-4.0, CC-BY-NC-SA-4.0, CC-BY-NC-ND-4.0, CC0-1.0, or the arXiv non-exclusive licence 1.0. The plan uses only CC-BY and CC0 papers | `https://info.arxiv.org/help/license/index.html` | CC-BY and CC0: yes. Non-exclusive licence: reuse by others is limited | CC-BY and CC0: yes. Everything else: no | CC-BY: credit authors, link the licence, mark changes, for every paper whose text reaches a redistributed dataset or gold file. Hence the attribution manifest. The licence must be read per paper and per version from metadata | checked 2026-11-23 |
| arXiv metadata | Licence filter, attribution manifest | CC0-1.0 | Same page; `https://info.arxiv.org/help/api/tou.html` | Yes | Yes | None | checked 2026-11-23 |
| arXiv access terms | Fetch budget | Not a licence. API terms: at most one request every 3 seconds on one connection for the legacy APIs; e-prints may be retrieved and stored for personal or research use; serving them from our own servers needs the copyright holder's permission or a licence that allows it; no claim of arXiv endorsement. `robots.txt`: `Crawl-delay: 15` for `User-agent: *`, `/html` allowed | `https://info.arxiv.org/help/api/tou.html`; `https://arxiv.org/robots.txt` | n/a | n/a | Keep the 15 s delay. The bulk-data (requester-pays S3) terms were not opened | checked 2026-11-23 |
| MathBridge | Equation and context columns for verbalizer training (spoken column discarded) | MIT per the card tag. The card README is empty: no source, no provenance. Columns: `context_before`, `equation`, `context_after`, `spoken_English`; about 23.2M rows | HF dataset `Kyudan/MathBridge` | Stated yes | Stated yes | The contexts look like text from academic papers. An MIT tag from the dataset authors cannot grant rights in third-party paper text. Treat as usable for private training only until provenance is established | checked 2026-11-23 (licence tag); provenance unverified |
| Speech2Latex | Spoken-form and LaTeX pairs for verbalizer training. Only part is human-annotated: the card says "over 66,000 human-annotated audio samples" against splits of 142,846 + 2,880 + 89,013 + 2,850 examples, and has an `is_tts` column marking TTS-generated audio. Filter on `is_tts` to get the human subset | CC-BY-4.0 | HF dataset `marsianin500/Speech2Latex` | Yes | Yes, with attribution | Credit the dataset and authors; link the licence; mark changes. The origin of the equations and sentences was not traced: the card metadata gives `source_datasets` as `original` and an extension of `math_dataset` with no further detail, and the same author publishes the companion `Speech2LatexMathBridge` set, which inherits the MathBridge provenance question and is not planned for use | checked 2026-11-23 (licence and card); equation and sentence sources unverified |
| DocGenome | Optional second source of structure labels for DocStruct | CC-BY-4.0 | HF dataset `U4R/DocGenome`; GH `UniModal4Reasoning/DocGenome` LICENSE | Yes | Yes, with attribution | Credit. It is built from 500K arXiv papers under one blanket licence; whether every underlying paper allows that was not checked | checked 2026-11-23 |
| unarXive (open subset) | Corpus fallback if the arXiv terms or markup check fails | Data: **CC-BY-SA-4.0**, open access. Code: MIT. The full dataset is a separate Zenodo record whose access terms were not opened | `https://zenodo.org/records/7752615`; GH `IllDepence/unarXive` LICENSE | Yes | Yes, share-alike | Attribution and share-alike: a redistributed dataset derived from it must be CC-BY-SA-4.0. Whether trained weights are "adapted material" is unsettled | checked 2026-11-23 |
| OmniDocBench (v1.6; README changelog mentions v1.7) | Sanity check only; nothing trains on it | Code: Apache-2.0. **Data: no licence tag; the copyright statement says "for research purposes only and not for commercial use"** | HF dataset `opendatalab/OmniDocBench` README; GH `opendatalab/OmniDocBench` LICENSE and README | No | No | Keep out of the repo and out of training data; report numbers only | checked 2026-11-23 |
| olmOCR-bench | Sanity check only | ODC-By-1.0. The card adds that it is "intended for research and educational use" under AI2's Responsible Use Guidelines (not opened) | HF dataset `allenai/olmOCR-bench` | Licence text: yes; stated intent: research | Yes, with attribution | Credit the source; keep the notice | checked 2026-11-23 |
| UniMER-Test | Sanity check only | Apache-2.0 on the card. The card's table gives the test set's sources: SPE (6,762) from Pix2tex validation, CPE (5,921) from arXiv, SCE (4,742) from PDF screenshots, and **HWE (6,332) from CROHME and HME100K**. The card flags HME100K with "For copyright compliance, please manually download this dataset portion", so the Apache tag does not cover every source and the restricted source is inside the test split. The licences of Pix2tex validation data, CROHME and HME100K were not opened | HF dataset `wanderkid/UniMER_Dataset` | Stated yes | Stated yes | Do not redistribute. Restrict the sanity check to the SPE, CPE and SCE subsets; if HWE is run (handwriting is out of scope for PodPaper anyway), note the HME100K caveat beside the number | checked 2026-11-23 (card); source licences unverified |
| G2 off-distribution documents | Gold set: open-access journal PDFs, scans, textbook chapters | Per document; not selected yet | n/a | n/a | Anything not redistributable stays in `data/gold-private/` with a URL manifest | Record the licence of each when chosen | unverified |
| Legacy fixtures from the 2020 repo | G0 tests | Repo code MIT per `ATTRIBUTION.md` (upstream repo not opened). `test.pdf` is third-party copyrighted lecture notes; the `latextext.txt` files and crops derive from a lab report naming real people | Local `ATTRIBUTION.md`; `PLAN.md` risk table | n/a | `test.pdf`: no. Lab-report files: only with redaction or consent | Owner decision 1 | unverified |

## Evaluation-only tools

None of these is on the runtime path. Each runs in its own environment under `envs/`.

| Name (version seen) | Role in PodPaper | Licence (SPDX) | Source | Commercial | Outputs | Duties | Status |
|---|---|---|---|---|---|---|---|
| openai-whisper (20250625), mlx-whisper (0.4.3) | Speech round-trip check | MIT | PyPI; GH `openai/whisper` LICENSE | Yes | Yes | Notice | checked 2026-11-23 |
| jiwer (4.0.0) | Word error rate | Apache-2.0 | PyPI | Yes | Yes | Notice | checked 2026-11-23 |
| CDM scorer | Offline formula metric | Apache-2.0 | GH `opendatalab/UniMERNet` LICENSE (the `cdm/` directory is in that repo; its README lists Node.js, ImageMagick and pdflatex as requirements) | Yes | Yes | Notice | checked 2026-11-23 |
| TeX Live (20260301) | pdflatex for CDM | Mixed free-software licences per package (LPPL, GPL, public domain and others); Homebrew cannot express it as one id | brew `texlive`; `https://www.tug.org/texlive/copying.html` | Yes | Yes | None for use. Redistribution is per package | checked 2026-11-23 (summary pages only) |
| ImageMagick (7.1.2) | Image conversion for CDM | ImageMagick | brew `imagemagick`; GH `ImageMagick/ImageMagick` LICENSE | Yes | Yes | Notice if redistributed | checked 2026-11-23 |
| **Ghostscript** (10.08.0) | PDF rasterising for CDM (dependency list still to be verified) | **AGPL-3.0-or-later** (or an Artifex commercial licence) | brew `ghostscript`; GH `ArtifexSoftware/ghostpdl` LICENSE | Yes | Yes | Strong network copyleft. Acceptable only as a separate command-line program in the eval environment; never import, link, bundle or expose it behind the server | checked 2026-11-23 |
| **MinerU** (4.2.3) | Whole-pipeline reference in the bake-off; possible S1 to S5 front end under the M3 adopt rule | **`LicenseRef-MinerU-Open-Source-License`**: Apache-2.0 plus additional terms. (1) A separate commercial licence is required above 100 million monthly active users or USD 20 million monthly revenue, consolidated with affiliates. (2) Online services built on MinerU must prominently say so. (3) Breach terminates the licence | PyPI `mineru`; GH `opendatalab/MinerU` LICENSE.md | Yes, below the thresholds | Yes | Not an OSI licence. Attribution duty if PodPaper is ever offered as an online service on top of it. Licences of the model weights MinerU downloads were not checked | checked 2026-11-23 |
| Docling (2.151.1) | Whole-pipeline reference in the bake-off | MIT | PyPI `docling`; GH `docling-project/docling` LICENSE | Yes | Yes | Notice. Licences of the models it downloads, other than heron above, were not checked | checked 2026-11-23 |
| LaTeXML | Corpus fallback only (local HTML conversion) | Public domain (US Government work, NIST) | GH `brucemiller/LaTeXML` LICENSE | Yes | Yes | None | checked 2026-11-23 |
| MathCAT | Skipped by the plan (no macOS Python package) | MIT | GH `NSoiffer/MathCAT` LICENSE | n/a | n/a | n/a | checked 2026-11-23 |

## Excluded

| Name | Why excluded | Licence | Source | Status |
|---|---|---|---|---|
| **PyMuPDF** (2.1) | AGPL. As an imported library it would put the whole worker, and any network service built on it, under AGPL terms unless a commercial licence is bought from Artifex. pypdfium2 covers rendering and the text layer under permissive terms | AGPL-3.0 or Artifex commercial ("Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License") | PyPI `PyMuPDF`; GH `pymupdf/PyMuPDF` COPYING | checked 2026-11-23 |

Keep it excluded transitively too: a dependency that pulls PyMuPDF in (some PDF toolkits do) brings the same terms. Check `uv.lock` for `pymupdf` whenever a document-processing dependency is added.

## Copyleft in the speech stack

What is there, as checked:

- `kokoro` 0.9.4 requires `misaki[en]>=0.9.4`.
- `misaki[en]` requires `phonemizer-fork`, `espeakng-loader`, `num2words`, `spacy`.
- `misaki/en.py` imports `num2words` unconditionally.
- `misaki/espeak.py` imports `phonemizer` and `espeakng_loader` and sets the espeak library path at import time.
- `kokoro/pipeline.py` begins with `from misaki import en, espeak`, and for English builds `espeak.EspeakFallback(...)` inside a `try`. So importing kokoro imports phonemizer-fork, and a normal English pipeline loads the espeak-ng shared library into the worker process.

What each licence means:

| Part | Licence | While the repo is private and nothing is distributed | If the repo or an app is distributed |
|---|---|---|---|
| phonemizer-fork | GPL-3.0-or-later | No duty. The GPL conditions attach to conveying copies, not to running the program | PodPaper's MIT source can still be published: MIT is GPL-compatible, and a `uv` install fetches phonemizer-fork from PyPI under its own licence. But anything that ships the combined program (a Tauri app, a wheel or image with dependencies vendored, a frozen binary) is a work that includes GPL code and must as a whole be offered under GPL-3.0-or-later with complete corresponding source. Publishing only a dependency declaration is the lower-risk form; whether an importing program is itself a derivative work is a legal question this table does not settle |
| espeak-ng (library loaded through phonemizer, or the Homebrew binary) | GPL-3.0-or-later | No duty | Same as above when the shared library is loaded in-process and shipped. If only the separately installed `espeak-ng` command were used as a subprocess, it would be a separate program and only its own redistribution would be bound |
| espeakng-loader | MIT loader code; the roughly 10 MB platform wheel provides the espeak-ng library and data, so treat its contents as GPL-3.0-or-later (wheel file list still to be confirmed in M0) | No duty | Redistributing the wheel, or a bundle containing it, is redistributing GPL code: the same duties as the espeak-ng row, including the GPL text and corresponding source for espeak-ng |
| num2words | LGPL-2.1-or-later | No duty | Weak copyleft. Using it as an unmodified, separately installed library puts no condition on PodPaper's licence. A bundle must include the LGPL text, let the user replace the library (trivially true for a Python package left as plain files), and offer source for any changes made to num2words itself |
| ffmpeg (Homebrew build) | GPL-3.0-or-later | No duty | Run as a subprocess, so PodPaper is not bound. Bundling this binary means complying with the GPL for ffmpeg; an LGPL build without x264/x265 would be the alternative for a bundled app |

Generated audio is not a derivative of the GPL or LGPL code. No licence above claims the output.

Running a GPL-3 program as a hosted service does not trigger GPL duties (that is the AGPL's addition), so a private hosted deployment would also be unaffected. This is stated for completeness; a hosted service is a non-goal.

The plan's mitigation, "misaki without the espeak fallback if a permissive distribution is wanted", is not available by configuration with kokoro 0.9.4 as published: the import of `misaki.espeak`, and the `misaki[en]` requirement on phonemizer-fork, are unconditional. A permissive distribution would need one of: a patched or vendored Kokoro inference path that imports only `misaki.en` with `fallback=None`, installed without the `en` extra's GPL parts; a different engine from the M3 bake-off (the mlx-audio and Qwen3-TTS paths need their own dependency check); or accepting GPL-3.0-or-later for the distributed app. num2words remains either way unless our own number normaliser replaces it.

## Where the findings differ from PLAN.md

| Item | PLAN.md says | Found |
|---|---|---|
| espeak-ng | "GPL-3" | GPL-3.0-or-later |
| num2words | "LGPL" | LGPL-2.1-or-later |
| phonemizer-fork | "GPLv3+" | Confirmed. In addition it is a hard dependency of `misaki[en]` and imported at `kokoro` import, so it cannot be dropped by a setting |
| ffmpeg | "Standard; installed with Homebrew"; not in the copyleft list | The Homebrew build is GPL-3.0-or-later |
| CDM scorer dependencies | Ghostscript listed with no licence note | Ghostscript is AGPL-3.0-or-later, the licence family PyMuPDF was excluded for. Tolerable only as an eval-only subprocess |
| MinerU 4.2 | Adopted as front end "licence permitting" | Custom licence: Apache-2.0 with commercial thresholds, an online-service attribution duty and a termination clause |
| OmniDocBench | "licence: verify" | Code Apache-2.0; data research-only and non-commercial, with no licence tag |
| OvisOCR3 | "licence: verify" | Apache-2.0 |
| MathBridge | "MIT ... provenance: verify" | MIT tag confirmed; the card is empty, so provenance is undocumented at the source |
| unarXive | Fallback corpus, "verify" | Open subset is CC-BY-SA-4.0 (share-alike); tool code is MIT |
| pypdfium2 | "BSD-3-Clause/Apache-2.0" | Confirmed for the binding; the wheel also carries PDFium and about 30 third-party licence texts that must ship with any binary redistribution |
| Kokoro-82M | "Apache-2.0" | Apache-2.0 confirmed on the card. The card also declares `yl4579/StyleTTS2-LJSpeech` as base model, a checkpoint with no licence tag and a synthesis-disclosure condition in its README. Whether it reaches Kokoro's weights is unverified |
| embeddinggemma-2 | Named with no licence note | Apache-2.0, plus a card requirement to follow the Gemma Prohibited Use Policy |
| espeakng-loader | Not named | Transitive dependency of `misaki[en]`; MIT loader whose wheel provides the GPL-3.0-or-later espeak-ng library |
| PP-DocLayoutV3, LanceDB, Speech2Latex, DocGenome, heron | Apache-2.0, Apache-2.0, CC-BY-4.0, CC-BY-4.0, Apache-2.0 | All confirmed |

## Attribution to carry in ATTRIBUTION.md

Needed now or as soon as the item is used:

- Kokoro-82M (Apache-2.0, hexgrad) and the CC BY audio its card lists: Koniwa `tnc` (CC BY 3.0) and SIWIS (CC BY 4.0).
- A statement that the audio is synthesised speech (player and exported file metadata). This covers the StyleTTS 2 pre-trained-model condition in case it applies to Kokoro, and credits StyleTTS 2 (Li et al., MIT code) as the architecture.
- Speech2Latex (CC-BY-4.0), when its pronunciations enter training data.
- DocGenome (CC-BY-4.0), if used.
- Every CC-BY arXiv paper in the corpus and gold sets, through the per-paper attribution manifest (authors, title, arXiv ID and version, licence, changes made).
- olmOCR-bench (ODC-By-1.0), if results from it are published.
- Apache-2.0 NOTICE files, for any Apache-licensed component that has one, if that component is ever redistributed.

## Open questions

1. Is the project ever distributed as an installable app or bundle? If yes, choose between GPL-3.0-or-later for the bundle, a Kokoro path without phonemizer-fork and espeak-ng, or another speech engine. If it stays a private or source-only repo, no copyleft duty arises. (Owner decision 1.)
2. `espeakng-loader`: registry metadata (10 MB platform wheels, README) says the wheel provides the espeak-ng library and data. Confirm by listing the installed wheel in M0, and record whether it ships a GPL notice.
3. embeddinggemma-2: its card requires adherence to the Gemma Prohibited Use Policy; the policy text has not been read. Do the Gemma Terms of Use also apply? Their appendix lists "EmbeddingGemma" without a version. (Settled for Gemma 4: the terms page excludes it, so Apache-2.0 only.)
4. Ollama builds: `qwen3.8:27b` and `gemma4:31b` carry Apache-2.0 licence layers (digests in the model rows). `glm-ocr:latest` ships no licence layer and `ggml-org/GLM-OCR-GGUF` has no licence field, so GLM-OCR's MIT status rests on the upstream card. Still to do: record the tag and digest actually pulled per Modelfile, since library tags can be repointed, and check any third-party quantisation or MLX build before use.
5. Kokoro-82M lineage: were its weights initialised from `yl4579/StyleTTS2-LJSpeech`, or does `base_model` only record the architecture? If the former, does the StyleTTS 2 pre-trained-model disclosure condition carry over, and what licence covers that untagged checkpoint? Ask upstream or find a statement from the author. Disclosing audio as synthesised satisfies the condition either way.
6. MathBridge provenance: where do the equations and contexts come from, and under what terms? Until answered, keep anything derived from it private, or drop it and rely on our own equation pool.
7. If unarXive becomes the corpus, is CC-BY-SA-4.0 on derived datasets acceptable, and what position do we take on weights trained from it?
8. Does the MinerU licence's online-service attribution clause, and its non-OSI status, rule it out as the S1 to S5 front end under the M3 adopt rule? Which licences cover the model weights MinerU and Docling download?
9. Is Ghostscript really needed by the CDM scorer (the plan marks the dependency list "verify")? The CDM README names Node.js, ImageMagick and pdflatex; ImageMagick may call Ghostscript for PDF input.
10. Which Whisper checkpoint (large-v3 is tagged Apache-2.0, large-v3-turbo MIT), which Qwen3-TTS variant and voice, and which Kokoro default voice?
11. Fonts: which UI fonts are bundled in `web/`, and what are the licences of the KaTeX fonts and `@mathjax/mathjax-newcm-font`?
12. arXiv requester-pays bulk data terms, Hugging Face Hub/Jobs and Modal terms of use, the spaCy English pipeline licence, the LJSpeech licence, the Gemma Prohibited Use Policy text, and the licences of Pix2tex validation data, CROHME and HME100K were not opened. The origin of the Speech2Latex equations and sentences was not traced.
13. G2 documents: record a licence per document when the set is chosen. Legacy fixtures: redact, get consent, or replace (owner decision 1).
14. DocGenome and UniMER publish one blanket licence over material gathered from many sources. Is that enough for our use, given that DocGenome would be training data and UniMER-Test is a sanity check only?
15. AAC and MP3 encoding by ffmpeg raises patent-licensing questions separate from copyright. Not assessed; relevant only if an app that encodes audio is distributed commercially.
