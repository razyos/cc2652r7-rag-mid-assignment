# New Session Brief - CC2652R7 RAG Pipeline

Paste this into a new session to continue safely from the current state.

## Goal for the New Session

Continue from the stable submission state on `main`. Session D is complete: the `Answerable@Context` hyphen/spacing normalization fix was merged to `main`, pushed, and reflected in `report.md`/`report.pdf`.

Recommended next work, if any, is a new branch from `main`. Keep `main` stable unless the branch passes verification and the report remains accurate.

## Project Location

`/Users/razyosef/AI_course/mid_ass/`

## Git Repository and Branching

Standalone GitHub repo: `https://github.com/razyos/cc2652r7-rag-mid-assignment`

Branch policy:

- `main` is the stable submission branch. It should remain runnable and submission-ready.
- Do not make risky changes directly on `main`.
- Use short-lived branches for optional work, for example `feature/negation-handling` or `feature/tx-power-extractor`.
- Use experimental branches for major changes, for example `exp/rf-driver-api-corpus` or `exp/competitor-datasheets`.
- Corpus expansion, gold-set rewrites, retrieval changes, or answer-generation behavior changes must not merge to `main` unless tests, eval, report updates, PDF regeneration, and page-count verification all pass.
- If the eval metric or report text changes, update `report.md`, regenerate `report.pdf` with `python scripts/render_report.py`, and verify `pdfinfo report.pdf` is still 4 pages or fewer.
- Do not force-push `main`.

## Current State as of 2026-05-23

This is a university mid-assignment RAG project over TI CC2652R7 technical documentation. The system uses a manual 7-stage pipeline: dense FAISS retrieval with `BAAI/bge-large-en-v1.5`, BM25 retrieval, hybrid merge, identifier-aware reranking, datasheet anchor injection, context budgeting, deterministic extractors, and local Ollama `llama3.2` fallback.

Sessions A-D are complete:

- `REPORT_NOTES.md` exists and contains the evidence pack.
- `report.md` exists as the editable report source.
- `report.pdf` exists and is 2 A4 pages; the assignment limit is "up to 4 pages."
- `scripts/render_report.py` regenerates `report.pdf` from `report.md`.
- README was updated to include the exact assignment commands:
  - `pip install -r requirements.txt`
  - `python src/build_index.py`
  - `python eval/run_eval.py`
- Latest completed eval on `main`: Hit@5 = 1.000 (50/50), Answerable@Context = 0.560 (28/50).
- Focused tests passed on `main`: `python -m pytest tests/test_generation.py tests/test_utils.py -q` passed 21 tests.
- `pdfinfo report.pdf` reports 2 pages.
- A full latest pytest run was attempted but stalled during model-heavy tests and was stopped without a pass/fail result. `PROJECT_STATUS.md` still records 37 tests passing from the earlier project state.

## Files to Read First

Read these before changing code:

1. `WORK_PLAN.md`
2. `REPORT_NOTES.md`
3. `FOR_AI_MODELS.md`
4. `PROJECT_STATUS.md`
5. `src/generation.py`
6. `tests/test_generation.py`
7. `eval/run_eval.py`
8. `report.md`

## Why Answerable@Context Is 0.560

The 28/50 result is mostly not a general architecture failure:

- 8 comparison misses require competitor datasheets that are not indexed.
- 6 debugging misses are dominated by missing RF Driver API documentation.
- 4 negation misses expose metric limitations for absence questions.
- remaining factual misses include TX-power retrieval/extraction error, RF API corpus gap, and a wrong temperature gold answer.
- 1 numerical miss is the ambiguous standard-mode TX-power question.

Session D fixed the voltage false negative by normalizing spaces and hyphens in `check_answerability()`.

## Constraints

- Do not change answer generation behavior, retrieval, corpus, prompts, or gold-set content on `main` directly.
- Do not add RF Driver API docs, competitor datasheets, or broad refactors before submission unless they are isolated in an experimental branch and the user explicitly accepts the rebuild/report-update risk.
- Keep local inference only: Ollama Llama 3.2 3B. No hosted LLM APIs.
- Preserve the report's honest caveats about empty `must_cite_chunk_ids`, corpus gaps, and gold-set mistakes.

## Safe Next Branches

- `feature/negation-handling`: preferred next narrow improvement. Improve unsupported-feature answers for Wi-Fi, USB, LTE/cellular, Ethernet, Bluetooth Classic, and related absence questions without changing corpus.
- `feature/tx-power-extractor`: targeted answer-quality improvement for max RF output power and standard-mode TX-power questions.
- `exp/rf-driver-api-corpus`: major corpus expansion for RF API questions. Requires source-document approval, index rebuild, eval rerun, manifest/report updates, and full submission audit before merge.
- `exp/competitor-datasheets`: major corpus expansion or gold-set redesign for comparison questions. Requires the same full re-audit before merge.

## Copy-Paste Prompt for Next Narrow Session

```text
We are continuing the CC2652R7 RAG mid-assignment project in:
/Users/razyosef/AI_course/mid_ass/

Deadline: Tuesday, May 26, 2026 at 12:00 noon Asia/Jerusalem.

Repository: https://github.com/razyos/cc2652r7-rag-mid-assignment
Keep main as the stable submission branch. Create a new branch from main for any optional work.

Sessions A-D are complete. report.md and report.pdf exist; report.pdf is 2 pages and within the assignment's "up to 4 pages" limit. Latest eval on main: Hit@5 = 1.000, Answerable@Context = 0.560 (28/50).

First read:
1. WORK_PLAN.md
2. REPORT_NOTES.md
3. FOR_AI_MODELS.md
4. PROJECT_STATUS.md
5. src/generation.py
6. tests/test_generation.py
7. eval/run_eval.py
8. report.md

Task:
- Preferred: start feature/negation-handling and improve unsupported-feature answers only.
- Do not add RF Driver API docs, competitor datasheets, broad retrieval changes, or gold-set rewrites unless explicitly asked to use an experimental branch.
- Run targeted tests, then full tests if feasible, then python eval/run_eval.py.
- If metrics or report claims change, update report.md, regenerate report.pdf using python scripts/render_report.py, and verify pdfinfo report.pdf is still <= 4 pages.
```
