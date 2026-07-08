# Legacy fixtures

Files taken from the 2020 PodPaper repository
(https://github.com/ethan-godden/PodPaper, commit `b966a89`, MIT licence).

They are **not committed**. They live in `data/fixtures-legacy/` (gitignored),
because the lab-report text and image crops name a real student and lab
partner, and `test.pdf` is third-party lecture notes. `MANIFEST.sha256` lists
the expected files and checksums; tests that need a file skip when it is absent.

To restore them, clone the old repository and copy:

| Old path | Into `data/fixtures-legacy/` as | Used for |
|---|---|---|
| `resources/static_web_files/test.pdf` | `test.pdf` | Crash, invariant and text-layer smoke input |
| `latextext.txt` | `latextext.txt` | Verbalizer and speech input |
| `Image to Latex/` | `image_to_latex/` | Formula and text recognition cases |
| `testtext.PNG` | `testtext.PNG` | Text recognition case |
| `TestFileConverted.mp3` | `TestFileConverted.mp3` | Reference for the old audio output |
| `TexToEnglish.py` | `TexToEnglish.py` | Mined for verbalizer test inputs, including ones that crashed it |

Verify with:

    cd data/fixtures-legacy && shasum -a 256 -c ../../tests/fixtures/legacy/MANIFEST.sha256
