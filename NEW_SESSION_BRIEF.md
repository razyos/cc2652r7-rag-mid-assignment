# New Session Brief - CC2652R7 RAG Pipeline

Paste the prompt at the end of this file into a new session to continue safely from the
current state.

## Goal for the New Session

Continue from the current local branch state on `feature/source-label-eval`.

The branch now contains the first source-label evaluation increment plus the follow-up
test-infrastructure stabilization work. It has focused metric tests, source-labeled
Hit@5/MRR reporting, 14 obvious `datasheet_hier_chunk_0000` labels without changing
gold Q/A text, deterministic fake embedding/reranker unit-test helpers, and a tiny
`build_faiss_index(..., model=...)` injection seam for tests. The latest implementation
commit is `60d40f1` (`Stabilize model-heavy unit tests`); the branch may also contain a
documentation-only handoff commit above it.

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
- Current work branch: `feature/source-label-eval`; latest implementation commit is `60d40f1`.
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
python -m pytest tests/ -q
50 passed

python eval/run_eval.py
Legacy Hit@5 = 1.000 (50/50)
Source-labeled Hit@5 = 1.000 (14 labeled)
Source-labeled MRR@5 = 0.964
Answerable@Context = 0.560 (28/50)

pdfinfo report.pdf
Pages: 2
```

Full pytest is now reliable on the source-label branch:

- `tests/test_build_index.py` uses an injected `FakeEmbeddingModel` instead of creating a
  real `SentenceTransformer`.
- `tests/test_retrieval.py` and `tests/test_rag_system.py` use deterministic fake
  embeddings plus a fake cross-encoder via monkeypatching.
- `src/build_index.py` keeps production behavior unchanged when `model` is not supplied:
  it still constructs `SentenceTransformer(model_name)`.
- Historical note: before commit `60d40f1`, full pytest crashed or stalled during real
  torch/SentenceTransformer startup in model-heavy unit tests.

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
10. `src/build_index.py`
11. `src/retrieval.py`
12. `tests/fakes.py`
13. `tests/test_build_index.py`
14. `tests/test_retrieval.py`
15. `tests/test_generation.py`
16. `tests/test_rag_system.py`
17. `eval/run_eval.py`
18. `eval/gold_set.jsonl`
19. `eval/eval_results.json`
20. `report.md`

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

1. **Source-label branch finish**
   Review, PR, or merge `feature/source-label-eval` now that full pytest is reliable.
   Optional later work can expand labels and rerun
   dense-only/no-rerank ablations with source-labeled metrics.

2. **TX-power extractor**
   Create `feature/tx-power-extractor`. Fix the max RF output power / standard-mode TX-power
   behavior without corpus expansion.

3. **Report refresh**
   Update `report.md`, regenerate `report.pdf`, and verify `pdfinfo report.pdf` is 4 pages or fewer.

4. **Experimental only if time remains**
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
- feature/source-label-eval was branched from main and now contains source-label eval changes plus test-infrastructure stabilization.
- Latest implementation commit should be 60d40f1 (`Stabilize model-heavy unit tests`):
  - d7ce7d9 Add source-labeled retrieval metrics
  - 7103b4f Update handoff for source-label test status
  - 60d40f1 Stabilize model-heavy unit tests
- The current local HEAD may be a documentation-only handoff commit above 60d40f1.
- The workspace should be clean, but inspect git status first.
- Merged Session E changes:
  - Unsupported connectivity/support questions now anchor datasheet_hier_chunk_0000.
  - Wi-Fi, USB, LTE/cellular, Ethernet, and Bluetooth Classic absence answers cite the CC2652R7 feature/protocol list.
  - LTE/cellular combined wording now says "LTE or cellular connectivity."
- Source-label eval branch changes:
  - eval/run_eval.py reports legacy Hit@k, source-labeled Hit@k, and source-labeled MRR.
  - eval/gold_set.jsonl has 14 obvious datasheet_hier_chunk_0000 labels.
  - Gold Q/A content was not changed.
  - tests/fakes.py provides deterministic FakeEmbeddingModel and FakeCrossEncoder.
  - tests/test_build_index.py, tests/test_retrieval.py, and tests/test_rag_system.py no longer start real SentenceTransformer/torch models.
  - src/build_index.py has a tiny optional model injection seam; production behavior is unchanged when model is omitted.
- eval/eval_results.json, report.md, report.pdf, and handoff docs were refreshed.
- SYSTEM_DESIGN_NOTES.md was added as an internal architecture/tradeoff note covering current design, industry alignment, and modern alternatives beyond FAISS/Chroma.
- Latest verified branch metrics:
  - Legacy Hit@5 = 1.000 (50/50)
  - Source-labeled Hit@5 = 1.000 (14 labeled)
  - Source-labeled MRR@5 = 0.964
  - Answerable@Context = 0.560 (28/50)
  - report.pdf is 2 pages.
- Latest verified commands:
  - python -m pytest tests/ -q -> 50 passed
  - python eval/run_eval.py -> completed with the metrics above
  - pdfinfo report.pdf -> Pages: 2
- Historical note: before 60d40f1, full pytest crashed/stalled during real torch/SentenceTransformer startup in model-heavy unit tests. Treat that as resolved on the current branch unless a fresh run proves otherwise.

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
10. src/build_index.py
11. src/retrieval.py
12. tests/fakes.py
13. tests/test_build_index.py
14. tests/test_retrieval.py
15. tests/test_generation.py
16. tests/test_rag_system.py
17. eval/run_eval.py
18. eval/gold_set.jsonl
19. eval/eval_results.json
20. report.md

Task:
1. Inspect git status and confirm the current branch/commit.
2. Review the source-label/test-stabilization branch and decide whether to merge/PR it or expand labels first.
3. If preparing to merge, run python -m pytest tests/ -q, python eval/run_eval.py, and pdfinfo report.pdf.
4. Regenerate report.pdf with python scripts/render_report.py only if report.md, metrics, or report claims change.
5. If expanding source labels, preserve gold Q/A content unless a specific correction is explicitly necessary and documented.
6. Do not migrate from FAISS or BM25 yet. If retrieval modernization is considered, first use SYSTEM_DESIGN_NOTES.md to frame options, then wait until source-label evaluation can measure alternatives.

Constraints:
- Do not add RF Driver API docs except on exp/rf-driver-api-corpus.
- Do not add competitor datasheets except on exp/competitor-datasheets.
- Do not rebuild indexes unless on an experimental corpus/index branch.
- Do not do broad retrieval/corpus refactors.
- Do not start feature/tx-power-extractor until source-label evaluation is reviewed/merged or intentionally deferred.
- Do not treat FAISS/Chroma as the full design space; SYSTEM_DESIGN_NOTES.md lists stronger modern options. Still, no backend migration should happen before measurable source-label eval.
- If full pytest stalls or segfaults again, stop it, isolate the blocker, and document the fresh attempt; do not claim full-suite pass unless it actually exits cleanly.
```
