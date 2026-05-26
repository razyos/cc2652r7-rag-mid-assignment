# New Session Brief - CC2652R7 RAG Pipeline

Paste the prompt at the end of this file into a new session to continue safely from the
current state.

## Goal for the New Session

Continue from the current local branch state, stabilize the completed
`feature/negation-handling` work, and prepare the next controlled improvement under the
new one-week extension.

The next session should not start risky new work until Session E is committed and either
merged to `main` or explicitly left parked. After that, the highest-value improvement is
`feature/source-label-eval`: make retrieval evaluation meaningful by adding real source
labels or an anchor-style metric, inspired by the comparison `insurance-rag` repo.

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
- Latest known stable `main` commit before Session E: `9b6a725 Document post-Session D branch policy`.
- Current work branch: `feature/negation-handling`.
- The current workspace may be dirty with Session E changes; inspect `git status` before assuming anything is committed.
- Do not make risky changes directly on `main`.
- Do not force-push `main`.
- Merge `feature/negation-handling` into `main` only after reviewing the diff, rerunning verification, and ensuring report artifacts remain current.
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

Sessions A-D are complete and merged to `main`. Session E is complete locally on
`feature/negation-handling`:

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

Latest verified Session E command results:

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

1. **Stabilize Session E**
   Review, verify, commit, and optionally merge `feature/negation-handling`.

2. **Source-label evaluation**
   Create `feature/source-label-eval`. Add meaningful retrieval evidence labels or
   anchor-style matching so Hit@5 is no longer vacuous. Add MRR if feasible.

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
- Current local branch may be feature/negation-handling with uncommitted Session E plus handoff/design-note changes.

Current state:
- Sessions A-D are complete and merged to main.
- Stable main before Session E: 9b6a725 Document post-Session D branch policy.
- Session E was implemented locally on feature/negation-handling.
- The workspace may still contain uncommitted Session E, report, handoff-doc, and SYSTEM_DESIGN_NOTES.md changes; inspect git status first.
- Session E changes:
  - Unsupported connectivity/support questions now anchor datasheet_hier_chunk_0000.
  - Wi-Fi, USB, LTE/cellular, Ethernet, and Bluetooth Classic absence answers cite the CC2652R7 feature/protocol list.
  - LTE/cellular combined wording now says "LTE or cellular connectivity."
- eval/eval_results.json, report.md, and report.pdf were refreshed.
- SYSTEM_DESIGN_NOTES.md was added as an internal architecture/tradeoff note covering current design, industry alignment, and modern alternatives beyond FAISS/Chroma.
- Latest verified metrics on the branch:
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

Task:
1. Inspect git status and the feature/negation-handling diff.
2. Verify the branch still contains only the narrow Session E changes plus handoff/internal documentation updates.
3. Rerun targeted tests:
   - python -m pytest tests/test_generation.py -q
   - python -m pytest tests/test_rag_system.py::test_answer_injects_datasheet_anchor_for_unsupported_connectivity_questions -q
4. Rerun python eval/run_eval.py if feasible.
5. Run python scripts/render_report.py and verify pdfinfo report.pdf is <= 4 pages if report.md or metrics changed.
6. If everything is clean, commit feature/negation-handling.
7. Ask before merging to main. If user approves merge, merge only after verification.
8. After Session E is handled, prepare feature/source-label-eval as the next branch. Goal: make Hit@5 meaningful by adding source labels or anchor-style source matching, preferably with MRR. Do not change the gold Q/A content unless explicitly necessary and documented.
9. Do not migrate from FAISS or BM25 yet. If retrieval modernization is considered, first use SYSTEM_DESIGN_NOTES.md to frame options, then wait until source-label evaluation exists so alternatives can be measured.

Constraints:
- Do not add RF Driver API docs except on exp/rf-driver-api-corpus.
- Do not add competitor datasheets except on exp/competitor-datasheets.
- Do not rebuild indexes unless on an experimental corpus/index branch.
- Do not do broad retrieval/corpus refactors.
- Do not start feature/tx-power-extractor until Session E is committed/merged or explicitly parked.
- Do not treat FAISS/Chroma as the full design space; SYSTEM_DESIGN_NOTES.md lists stronger modern options. Still, no backend migration should happen before measurable source-label eval.
- If full pytest stalls in model-heavy tests, stop it and report the attempt; do not claim full-suite pass.
```
