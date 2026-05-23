# New Session Brief - CC2652R7 RAG Pipeline

Paste this into a new session to continue safely from the current state.

## Goal for the New Session

Run Session D from `WORK_PLAN.md`: fix only the `Answerable@Context` hyphen/spacing normalization bug, then rerun eval and update the report only if the metric changes.

## Project Location

`/Users/razyosef/AI_course/mid_ass/`

## Git Repository and Branching

Standalone GitHub repo: `https://github.com/razyos/cc2652r7-rag-mid-assignment`

Branch policy:

- `main` is the stable submission branch. It should remain runnable and submission-ready.
- `fix/answerability-normalization` is the branch prepared for Session D.
- Do not make risky changes directly on `main`.
- Commit Session D work to `fix/answerability-normalization`, push it, and merge to `main` only after verification.
- If the eval metric or report text changes, update `report.md`, regenerate `report.pdf` with `python scripts/render_report.py`, and verify `pdfinfo report.pdf` is still 4 pages or fewer.
- Do not force-push `main`.

## Current State as of 2026-05-23

This is a university mid-assignment RAG project over TI CC2652R7 technical documentation. The system uses a manual 7-stage pipeline: dense FAISS retrieval with `BAAI/bge-large-en-v1.5`, BM25 retrieval, hybrid merge, identifier-aware reranking, datasheet anchor injection, context budgeting, deterministic extractors, and local Ollama `llama3.2` fallback.

Sessions A-C are complete:

- `REPORT_NOTES.md` exists and contains the evidence pack.
- `report.md` exists as the editable report source.
- `report.pdf` exists and is 2 A4 pages; the assignment limit is "up to 4 pages."
- `scripts/render_report.py` regenerates `report.pdf` from `report.md`.
- README was updated to include the exact assignment commands:
  - `pip install -r requirements.txt`
  - `python src/build_index.py`
  - `python eval/run_eval.py`
- Latest completed eval: Hit@5 = 1.000 (50/50), Answerable@Context = 0.540 (27/50).
- Focused tests passed: `python -m pytest tests/test_generation.py tests/test_utils.py -q` and two BM25-only build-index tests.
- A full latest pytest run was attempted but stalled during model-heavy tests and was stopped without a pass/fail result. `PROJECT_STATUS.md` still records 37 tests passing from the earlier project state.

## Files to Read First

Read these before changing code:

1. `WORK_PLAN.md`
2. `REPORT_NOTES.md`
3. `FOR_AI_MODELS.md`
4. `PROJECT_STATUS.md`
5. `src/generation.py`, especially `check_answerability()`
6. `tests/test_generation.py`
7. `eval/run_eval.py`
8. `report.md`

## Why Answerable@Context Is 0.540

The 27/50 result is mostly not a general architecture failure:

- 8 comparison misses require competitor datasheets that are not indexed.
- 6 debugging misses are dominated by missing RF Driver API documentation.
- 4 negation misses expose metric limitations for absence questions.
- 4 factual misses include TX-power retrieval/extraction error, RF API corpus gap, voltage normalization, and a wrong temperature gold answer.
- 1 numerical miss is the ambiguous standard-mode TX-power question.

Session D is expected to fix only the voltage false negative, likely improving Answerable@Context from 27/50 = 0.540 to about 28/50 = 0.560. That is still worthwhile because it removes a known metric bug.

## Constraints

- Do not change answer generation behavior in Session D.
- Do not add RF Driver API docs, competitor datasheets, or broad refactors before submission unless the user explicitly accepts the rebuild/report-update risk.
- Keep local inference only: Ollama Llama 3.2 3B. No hosted LLM APIs.
- Preserve the report's honest caveats about empty `must_cite_chunk_ids`, corpus gaps, and gold-set mistakes.

## Copy-Paste Prompt for Session D

```text
We are continuing the CC2652R7 RAG mid-assignment project in:
/Users/razyosef/AI_course/mid_ass/

Deadline: Tuesday, May 26, 2026 at 12:00 noon Asia/Jerusalem.

Repository: https://github.com/razyos/cc2652r7-rag-mid-assignment
Use branch fix/answerability-normalization for this work. Keep main as the stable submission branch.

Sessions A-C are complete. report.md and report.pdf exist; report.pdf is 2 pages and within the assignment's "up to 4 pages" limit. The current priority is Session D only: fix the Answerable@Context hyphen/spacing normalization bug.

First read:
1. WORK_PLAN.md
2. REPORT_NOTES.md
3. FOR_AI_MODELS.md
4. PROJECT_STATUS.md
5. src/generation.py, especially check_answerability()
6. tests/test_generation.py
7. eval/run_eval.py
8. report.md

Task:
- Add focused tests showing key terms like "1.8V" and "3.8V" match retrieved context containing "1.8-V" and "3.8-V".
- Implement the minimal fix in check_answerability() by normalizing terms and context for whitespace/hyphens.
- Do not change generation behavior, retrieval, corpus, prompts, or gold-set content.
- Run targeted tests, then full tests if feasible, then python eval/run_eval.py.
- Report old and new Answerable@Context.
- If the metric changes, update report.md, regenerate report.pdf using python scripts/render_report.py, and verify pdfinfo report.pdf is still <= 4 pages.

Expected impact: probably 27/50 -> 28/50, not a broad quality jump. Do not start RF Driver API corpus expansion or competitor datasheet work in this session.
```
