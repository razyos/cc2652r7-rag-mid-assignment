# New Session Brief - CC2652R7 RAG Pipeline

Paste the prompt at the end of this file into a new session to continue safely from the
current state.

## Goal for the New Session

Continue from the current local branch state on `feature/source-label-eval`.

The branch now contains the first source-label evaluation increment: focused metric
tests, source-labeled Hit@5/MRR reporting, and 14 obvious `datasheet_hier_chunk_0000`
labels without changing gold Q/A text. Current local branch HEAD is `d7ce7d9`
(`Add source-labeled retrieval metrics`), one commit ahead of `main`/`origin/main`.

An internal architecture/tradeoff note now exists at `SYSTEM_DESIGN_NOTES.md`. Read it
before proposing retrieval or indexing changes; it explains why the current FAISS+BM25
design fits the assignment and also documents more modern alternatives such as RRF,
Qdrant, Weaviate, Milvus, pgvector, sparse+dense retrieval, BGE-M3, ColBERT-style late
interaction, and GraphRAG.

## Project Location

`/Users/razyosef/AI_course/mid_ass/`

## Git Repository and Branching

Standalone GitHub repo: `https://github.com/razyos/cc2652r7-rag-mid-assignment`

Branch policy:

- `main` is the stable submission branch. It should remain runnable and submission-ready.
- Current pushed `main`: post-Session E handoff docs are current.
- Current work branch: `feature/source-label-eval` at local commit `d7ce7d9`.
- Session E commit chain on `main`: `93789fb Handle unsupported connectivity anchors`, `d9a2fe6 Update next session handoff`, `ab8b70c Refresh Session E verification artifacts`.
- The current workspace should be clean, but inspect `git status` first.
- Do not make risky changes directly on `main`.
- Do not force-push `main`.
- Use short-lived branches for narrow improvements:
  - `feature/source-label-eval`
  - `feature/tx-power-extractor`
- Use experimental branches for corpus/index/gold-set scope changes:
  - `exp/rf-driver-api-corpus`
  - `exp/competitor-datasheets`

## Deadline

Original deadline: Tuesday, May 26, 2026 at 12:00 noon Asia/Jerusalem.

Extension: one week from May 26, 2026. Treat the working deadline as Tuesday,
June 2, 2026, with exact time still to confirm. If no time is provided, plan as if the
deadline is June 2, 2026 at 12:00 noon Asia/Jerusalem.

## Current State as of 2026-05-26

This is a university mid-assignment RAG project over TI CC2652R7 technical documentation.
The system uses a manual 7-stage pipeline: dense FAISS retrieval with
`BAAI/bge-large-en-v1.5`, BM25 retrieval, hybrid merge, identifier-aware reranking,
datasheet anchor injection, context budgeting, deterministic extractors, and local
Ollama `llama3.2` fallback.

Sessions A-E are complete and merged to `main`. The Session E verification artifact commit is `ab8b70c`, and the post-Session E handoff docs are current on `main`:

- Unsupported connectivity questions now force `datasheet_hier_chunk_0000` into the final context:
  - Wi-Fi
  - USB
  - LTE / cellular
  - Ethernet
  - Bluetooth Classic / BR/EDR
- `src/rag_system.py` extends Stage 5b anchor injection to unsupported connectivity/support terms.
- `src/generation.py` keeps the existing yes/no unsupported-feature path, but labels the combined LTE/cellular question as `LTE or cellular connectivity`.
- `tests/test_generation.py` adds focused LTE/cellular wording coverage.
- `tests/test_rag_system.py` adds focused anchor-injection coverage for the five unsupported connectivity questions.
- `eval/eval_results.json` was refreshed.
- `report.md` was updated to describe unsupported-connectivity extraction behavior.
- `report.pdf` was regenerated and remains 2 A4 pages.

Latest verified Session E command results before merge:

```text
python -m pytest tests/test_generation.py -q
12 passed

python -m pytest tests/test_rag_system.py::test_answer_injects_datasheet_anchor_for_unsupported_connectivity_questions -q
5 passed

python eval/run_eval.py
Hit@5 = 1.000 (50/50)
Answerable@Context = 0.560 (28/50)

python scripts/render_report.py
completed

pdfinfo report.pdf
Pages: 2
```

Full `python -m pytest tests/ -q` was attempted but stopped after the same model-heavy
stall/no-output behavior noted in previous project docs. Do not report it as passed.

Latest verified `feature/source-label-eval` branch results:

```text
python -m pytest tests/test_eval_metrics.py -q
5 passed

python -m pytest tests/test_eval_metrics.py tests/test_generation.py tests/test_utils.py -q
27 passed

python eval/run_eval.py
Legacy Hit@5 = 1.000 (50/50)
Source-labeled Hit@5 = 1.000 (14 labeled)
Source-labeled MRR@5 = 0.964
Answerable@Context = 0.560 (28/50)

python scripts/render_report.py
completed

pdfinfo report.pdf
Pages: 2
```

Full pytest status after source-label commit:

```text
python -m pytest tests/ -q
FAILED: Python process crashed with a segmentation fault inside torch/nn/functional.py
after a long silent startup.
```

Follow-up isolation:

- `tests/test_eval_metrics.py tests/test_generation.py tests/test_utils.py` passed 27 tests.
- `tests/test_build_index.py`, `tests/test_retrieval.py`, and `tests/test_rag_system.py`
  stalled silently when run in isolation and were stopped.
- These files instantiate real `SentenceTransformer` / torch models. Treat this as
  existing test-infrastructure fragility, not as evidence that the source-label metric
  implementation failed.
- Recommended next technical task: refactor model-heavy unit tests to use fake
  embeddings/fake model injection so `python -m pytest tests/ -q` can become a reliable
  merge gate.

## Current Answer Behavior to Preserve

Saved eval output now shows these unsupported-feature answers cite
`datasheet_hier_chunk_0000`:

- `Does the CC2652R7 support Wi-Fi?`
- `Does the CC2652R7 support LTE or cellular connectivity?`
- `Does the CC2652R7 support USB?`
- `Does the CC2652R7 have an Ethernet interface?`

`Does the CC2652R7 support Bluetooth Classic (BR/EDR)?` also answers from
`datasheet_hier_chunk_0000`.

Headline metrics did not change:

- Legacy Hit@5 = 1.000
- Source-labeled Hit@5 = 1.000 over 14 labeled rows
- Source-labeled MRR@5 = 0.964
- Answerable@Context = 0.560
- Report remains 2 pages

## Comparison Repo Takeaways

The external repo `https://github.com/dudumrk2/insurance-rag.git` was inspected in an isolated
directory (`/private/tmp/insurance-rag`) for design comparison only.

Useful ideas to borrow conceptually:

- Add source-label or anchor-style retrieval evaluation so Hit@5 is meaningful.
- Report MRR in addition to Hit@k.
- Use dependency injection/fake embeddings in tests to avoid model-heavy stalls.

Do not copy code from that repo. Do not switch this project from FAISS to Chroma or any
other backend before source-label evaluation exists and the change can be measured. Chroma
is useful there for multi-tenant metadata filtering; this project has one public TI corpus
and already benefits from FAISS + BM25 + reranking. `SYSTEM_DESIGN_NOTES.md` documents
when more advanced alternatives would be worth testing.

## Files to Read First

Read these before changing code:

1. `NEW_SESSION_BRIEF.md`
2. `WORK_PLAN.md`
3. `README.md`
4. `SYSTEM_DESIGN_NOTES.md`
5. `PROJECT_STATUS.md`
6. `FOR_AI_MODELS.md`
7. `REPORT_NOTES.md`
8. `src/rag_system.py`
9. `src/generation.py`
10. `tests/test_generation.py`
11. `tests/test_rag_system.py`
12. `eval/run_eval.py`
13. `eval/gold_set.jsonl`
14. `eval/eval_results.json`
15. `report.md`

## Constraints

- Keep `main` stable.
- Do not force-push `main`.
- Do not add RF Driver API docs on a feature branch; use `exp/rf-driver-api-corpus` only.
- Do not add competitor datasheets on a feature branch; use `exp/competitor-datasheets` only.
- Do not rewrite the gold set casually. If source labels are added, keep Q/A content stable and document the change.
- Do not rebuild indexes unless working on an experimental corpus/index branch.
- Do not do broad retrieval/corpus refactors.
- Preserve local inference only: Ollama Llama 3.2 3B, no hosted LLM APIs for core answering.
- Preserve the report's caveats about corpus gaps and gold-set mistakes.
- Do not treat FAISS, Chroma, or any vector backend as dogma. Read `SYSTEM_DESIGN_NOTES.md`
  for modern alternatives, but do not migrate retrieval infrastructure until source-label
  evaluation can measure the change.

## Recommended Session Order Under the Extension

1. **Test-infrastructure stabilization**
   Keep working on `feature/source-label-eval`. Replace real `SentenceTransformer` /
   torch usage in unit tests with deterministic fake embeddings or injected fake models,
   then rerun `python -m pytest tests/ -q`.

2. **Source-label branch finish**
   After full pytest is reliable or the limitation is explicitly accepted, merge or PR
   `feature/source-label-eval`. Optional later work can expand labels and rerun
   dense-only/no-rerank ablations with source-labeled metrics.

3. **TX-power extractor**
   Create `feature/tx-power-extractor`. Fix the max RF output power / standard-mode TX-power
   behavior without corpus expansion.

4. **Report refresh**
   Update `report.md`, regenerate `report.pdf`, and verify `pdfinfo report.pdf` is 4 pages or fewer.

5. **Experimental only if time remains**
   Consider `exp/rf-driver-api-corpus`. Do not start competitor datasheets unless everything
   else is complete and the user explicitly accepts the scope risk.

## Optimal Prompt for the Next Session

```text
We are continuing the CC2652R7 RAG mid-assignment project in:
/Users/razyosef/AI_course/mid_ass/

Current date: May 26, 2026 Asia/Jerusalem.
Original deadline: Tuesday, May 26, 2026 at 12:00 noon Asia/Jerusalem.
Extension: one week. Treat the working deadline as Tuesday, June 2, 2026, exact time TBD; assume 12:00 noon Asia/Jerusalem until clarified.

Repository:
https://github.com/razyos/cc2652r7-rag-mid-assignment

Branch policy:
- main is the stable submission branch.
- Do not make risky changes directly on main.
- Do not force-push main.
- Current local branch should be feature/source-label-eval.

Current state:
- Sessions A-E are complete and merged to main.
- Current pushed main has current post-Session E handoff docs.
- feature/source-label-eval was branched from main and now contains source-label eval changes.
- Current local HEAD should be d7ce7d9 (`Add source-labeled retrieval metrics`), one commit ahead of main/origin/main.
- The workspace should be clean, but inspect git status first.
- Merged Session E changes:
  - Unsupported connectivity/support questions now anchor datasheet_hier_chunk_0000.
  - Wi-Fi, USB, LTE/cellular, Ethernet, and Bluetooth Classic absence answers cite the CC2652R7 feature/protocol list.
  - LTE/cellular combined wording now says "LTE or cellular connectivity."
- eval/eval_results.json, report.md, and report.pdf were refreshed.
- SYSTEM_DESIGN_NOTES.md was added as an internal architecture/tradeoff note covering current design, industry alignment, and modern alternatives beyond FAISS/Chroma.
- Latest verified branch metrics:
  - Legacy Hit@5 = 1.000 (50/50)
  - Source-labeled Hit@5 = 1.000 (14 labeled)
  - Source-labeled MRR@5 = 0.964
  - Answerable@Context = 0.560 (28/50)
  - report.pdf is 2 pages.
- Full pytest was attempted after the source-label commit and crashed with a Python
  segmentation fault inside torch/nn/functional.py after a long silent startup.
- Isolated non-model tests passed: python -m pytest tests/test_eval_metrics.py tests/test_generation.py tests/test_utils.py -q -> 27 passed.
- Isolated model-heavy test files stalled silently: tests/test_build_index.py,
  tests/test_retrieval.py, and tests/test_rag_system.py. They instantiate real
  SentenceTransformer/torch models.

First read:
1. NEW_SESSION_BRIEF.md
2. WORK_PLAN.md
3. README.md
4. SYSTEM_DESIGN_NOTES.md
5. PROJECT_STATUS.md
6. FOR_AI_MODELS.md
7. REPORT_NOTES.md
8. src/rag_system.py
9. src/generation.py
10. tests/test_generation.py
11. tests/test_rag_system.py
12. eval/run_eval.py
13. eval/gold_set.jsonl
14. eval/eval_results.json
15. report.md

Task:
1. Inspect git status and confirm the current branch/commit.
2. Recommended next task: make full pytest reliable by refactoring model-heavy unit tests to use fake embeddings/fake model injection instead of real SentenceTransformer/torch startup.
3. Preserve production retrieval/index behavior; this should be a test-infrastructure change only.
4. After test refactoring, run python -m pytest tests/ -q, python eval/run_eval.py, python scripts/render_report.py if report claims change, and pdfinfo report.pdf.
5. If full pytest remains blocked, document the exact blocker and keep targeted verification explicit.
6. Do not change the gold Q/A content unless explicitly necessary and documented.
7. Do not migrate from FAISS or BM25 yet. If retrieval modernization is considered, first use SYSTEM_DESIGN_NOTES.md to frame options, then wait until source-label evaluation exists so alternatives can be measured.

Constraints:
- Do not add RF Driver API docs except on exp/rf-driver-api-corpus.
- Do not add competitor datasheets except on exp/competitor-datasheets.
- Do not rebuild indexes unless on an experimental corpus/index branch.
- Do not do broad retrieval/corpus refactors.
- Do not start feature/tx-power-extractor until source-label evaluation is reviewed/merged or intentionally deferred; preferably make full pytest reliable first.
- Do not treat FAISS/Chroma as the full design space; SYSTEM_DESIGN_NOTES.md lists stronger modern options. Still, no backend migration should happen before measurable source-label eval.
- If full pytest stalls or segfaults in model-heavy tests, stop it and report the attempt; do not claim full-suite pass.
```
