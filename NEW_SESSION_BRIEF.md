# New Session Brief - CC2652R7 RAG Pipeline

Paste the prompt at the end of this file into a new session to continue safely from the
current state.

## Goal for the New Session

Continue from pushed `main`, which now includes the failure-analysis case study and
updated improvement roadmap.

The highest-value next improvement is `feature/source-label-eval`: make retrieval
evaluation meaningful by adding real source labels or an anchor-style metric, inspired
by the comparison `insurance-rag` repo.

After source-label evaluation, the next narrow answer-quality branch is
`feature/tx-power-extractor`. Treat the standard-mode TX-power failure as an
answer-present retrieval/extraction problem, not as missing corpus evidence.

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
- Current pushed `main`: post-Session E handoff docs plus updated RAG failure-analysis docs are current.
- Current work branch: `main`; create a short-lived feature branch before code or metric changes.
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

## Current State as of 2026-05-28

This is a university mid-assignment RAG project over TI CC2652R7 technical documentation.
The system uses a manual 7-stage pipeline: dense FAISS retrieval with
`BAAI/bge-large-en-v1.5`, BM25 retrieval, hybrid merge, identifier-aware reranking,
datasheet anchor injection, context budgeting, deterministic extractors, and local
Ollama `llama3.2` fallback.

Sessions A-E are complete and merged to `main`. The Session E verification artifact commit is `ab8b70c`. Later documentation commits added `RAG_EXPLICIT_DATA_FAILURE_CASE_STUDY.md` and updated the report roadmap:

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
- `RAG_EXPLICIT_DATA_FAILURE_CASE_STUDY.md` explains the standard-mode TX-power failure: the answer exists in the datasheet, but retrieval selects misleading TRM evidence about `CMD_SET_TX20_POWER` and the `20 dBm PA` path.
- `report.md`, `REPORT_NOTES.md`, `PROJECT_STATUS.md`, `WORK_PLAN.md`, `SYSTEM_DESIGN_NOTES.md`, `README.md`, and `FOR_AI_MODELS.md` now distinguish missing-source failures from answer-present retrieval/extraction failures.

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

- Hit@5 = 1.000
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
16. `RAG_EXPLICIT_DATA_FAILURE_CASE_STUDY.md`

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

1. **Source-label evaluation**
   Continue `feature/source-label-eval`. Add meaningful retrieval evidence labels or
   anchor-style matching so Hit@5 is no longer vacuous. Add MRR if feasible.

2. **Failure taxonomy**
   Classify failures as missing-source, retrieval miss, generation/validation error, or
   gold mismatch. This prevents treating safe refusals and retriever mistakes as the
   same kind of failure.

3. **TX-power extractor**
   Create `feature/tx-power-extractor`. Fix the max RF output power / standard-mode TX-power
   behavior without corpus expansion. Prefer datasheet `dBm` chunks, parse Table 7-1,
   penalize contradictory `20 dBm PA` evidence for "without PA" queries, and normalize
   `4.8 dBm` typical output to the `+5 dBm` specification answer.

4. **Report refresh**
   Update `report.md`, regenerate `report.pdf`, and verify `pdfinfo report.pdf` is 4 pages or fewer.

5. **Experimental only if time remains**
   Consider `exp/rf-driver-api-corpus`. Do not start competitor datasheets unless everything
   else is complete and the user explicitly accepts the scope risk.

## Optimal Prompt for the Next Session

```text
We are continuing the CC2652R7 RAG mid-assignment project in:
/Users/razyosef/AI_course/mid_ass/

Current date: May 28, 2026 Asia/Jerusalem.
Original deadline: Tuesday, May 26, 2026 at 12:00 noon Asia/Jerusalem.
Extension: one week. Treat the working deadline as Tuesday, June 2, 2026, exact time TBD; assume 12:00 noon Asia/Jerusalem until clarified.

Repository:
https://github.com/razyos/cc2652r7-rag-mid-assignment

Branch policy:
- main is the stable submission branch.
- Do not make risky changes directly on main.
- Do not force-push main.
- Current local branch may be main. Create feature/source-label-eval before code or metric changes.

Current state:
- Sessions A-E are complete and merged to main.
- Current pushed main has current post-Session E handoff docs plus updated failure-analysis and roadmap docs.
- The workspace should be clean, but inspect git status first.
- Merged Session E changes:
  - Unsupported connectivity/support questions now anchor datasheet_hier_chunk_0000.
  - Wi-Fi, USB, LTE/cellular, Ethernet, and Bluetooth Classic absence answers cite the CC2652R7 feature/protocol list.
  - LTE/cellular combined wording now says "LTE or cellular connectivity."
- eval/eval_results.json, report.md, and report.pdf were refreshed.
- SYSTEM_DESIGN_NOTES.md was added as an internal architecture/tradeoff note covering current design, industry alignment, and modern alternatives beyond FAISS/Chroma.
- RAG_EXPLICIT_DATA_FAILURE_CASE_STUDY.md documents the standard-mode TX-power failure where the answer exists in the datasheet but retrieval selects misleading TRM evidence.
- Latest verified metrics on `main`:
  - Hit@5 = 1.000 (50/50)
  - Answerable@Context = 0.560 (28/50)
  - report.pdf is 2 pages.

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
16. RAG_EXPLICIT_DATA_FAILURE_CASE_STUDY.md

Task:
1. Inspect git status and confirm the current branch/commit.
2. Continue feature/source-label-eval. Goal: make Hit@5 meaningful by adding source labels or anchor-style source matching, preferably with MRR. Do not change the gold Q/A content unless explicitly necessary and documented.
3. Label the TX-power questions with their true answer-bearing chunks, especially datasheet_hier_chunk_0001_sub0 and datasheet_hier_chunk_0030, so eval can distinguish retrieval misses from missing-source failures.
4. If present locally, use docs/superpowers/plans/2026-05-26-source-label-eval.md as the detailed implementation plan for source-label evaluation; otherwise follow WORK_PLAN.md Session F.
5. Add focused tests for source-labeled Hit@k/MRR behavior before implementation.
6. Run targeted tests and python eval/run_eval.py.
7. If metrics or report claims change, update report.md, regenerate report.pdf with python scripts/render_report.py, and verify pdfinfo report.pdf is <= 4 pages.
8. Do not migrate from FAISS or BM25 yet. If retrieval modernization is considered, first use SYSTEM_DESIGN_NOTES.md to frame options, then wait until source-label evaluation exists so alternatives can be measured.

Constraints:
- Do not add RF Driver API docs except on exp/rf-driver-api-corpus.
- Do not add competitor datasheets except on exp/competitor-datasheets.
- Do not rebuild indexes unless on an experimental corpus/index branch.
- Do not do broad retrieval/corpus refactors.
- Do not start feature/tx-power-extractor until source-label evaluation is handled or intentionally deferred. When it starts, treat TX power as a targeted retrieval/table-extraction/validation fix, not a corpus expansion.
- Do not treat FAISS/Chroma as the full design space; SYSTEM_DESIGN_NOTES.md lists stronger modern options. Still, no backend migration should happen before measurable source-label eval.
- If full pytest stalls in model-heavy tests, stop it and report the attempt; do not claim full-suite pass.
```
