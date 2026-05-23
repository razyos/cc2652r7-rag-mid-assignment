# CC2652R7 RAG Assignment Work Plan

**Created:** 2026-05-23  
**Submission deadline:** 2026-05-26 at 12:00 noon, Asia/Jerusalem  
**Planning decision:** The report was the critical path and is now submission-safe. Code improvements are optional and should remain narrow unless the report is re-audited afterward.

**Status update, 2026-05-23:** Sessions A-D are complete and merged to `main`. `REPORT_NOTES.md`, `report.md`, and `report.pdf` exist; `report.pdf` is 2 A4 pages, which satisfies the assignment's "up to 4 pages" limit. Session C audit verified required files, README commands, manifest fields, and `RAGSystem.answer(question: str) -> dict`. Session D fixed the Answerable@Context hyphen/spacing normalization false negative and refreshed eval/report evidence. `main` is the stable submission branch.

## Repository and Branching Strategy

Standalone repository:

- GitHub: `https://github.com/razyos/cc2652r7-rag-mid-assignment`
- Local path: `/Users/razyosef/AI_course/mid_ass`
- Default branch: `main`
- Current stable branch: `main`
- Session D branch: `fix/answerability-normalization` was merged and pushed to `main` at commit `48dbd30`.

DevOps policy:

- Treat `main` as the stable submission branch. It should always be runnable and contain a valid `report.pdf`.
- Do optional work on short-lived branches named by intent, such as `feature/negation-handling`, `feature/tx-power-extractor`, `exp/rf-driver-api-corpus`, or `exp/competitor-datasheets`.
- Major or risky work is allowed only away from `main`. Corpus expansion, gold-set rewrites, retrieval changes, or answer-generation behavior changes must stay on separate branches until fully verified.
- Before merging a branch into `main`, run the smallest relevant tests and record the result in the final session summary.
- If code changes can affect metrics, run `python eval/run_eval.py`.
- If metrics, report claims, or report source change, update `report.md`, regenerate `report.pdf` with `python scripts/render_report.py`, and verify `pdfinfo report.pdf` reports 4 pages or fewer.
- For corpus expansion or gold-set changes, also rebuild indexes as needed, rerun eval from scratch, re-audit `report.md`/`report.pdf`, and only merge if the new result is clearly submission-safe.
- Do not force-push `main`. Prefer a pull request or a fast-forward/merge commit.
- Do not commit local caches, `.DS_Store`, `.claude/`, `__pycache__/`, `.pytest_cache/`, or stale eval artifacts ignored by `.gitignore`.

## Current Project State

The project already has a working 7-stage RAG pipeline over TI CC2652R7 documentation:

1. Dense retrieval with FAISS and `BAAI/bge-large-en-v1.5`
2. BM25 retrieval
3. Hybrid merge
4. Identifier pin detection
5. Cross-encoder reranking with identifier boost
6. Datasheet anchor injection and token budgeting
7. Deterministic extractor-first generation with Llama 3.2 fallback through Ollama

Current verified project status:

- 2361 indexed chunks from three documents: CC2652R7 datasheet, TI TRM, and SimpleLink SDK User's Guide
- 50-question gold set
- Hit@5 = 1.000
- Answerable@Context = 0.560
- Focused verification after Session D merge to `main`: `python -m pytest tests/test_generation.py tests/test_utils.py -q` passed 21 tests; `python eval/run_eval.py` completed with Hit@5 = 1.000 and Answerable@Context = 0.560; `pdfinfo report.pdf` reports 2 pages.
- Full 37-test suite was previously passing as of `PROJECT_STATUS.md`, but the latest full-suite audit attempt stalled during model-heavy tests and was stopped without a pass/fail result
- Stress test passing as of the project status note
- `demo.py` ready for live demo
- `report.md` and `report.pdf` are present; `scripts/render_report.py` regenerates the PDF from Markdown

Important constraints:

- Local inference only: Llama 3.2 3B via Ollama
- No OpenAI, Anthropic, or other hosted model APIs
- Python 3.12, no web framework
- The report is the primary deliverable
- Do not revisit known failed approaches from `FOR_AI_MODELS.md`
- Do not treat RF API failures as pipeline bugs; RF Driver API documentation is not indexed
- The gold set SRAM answer is wrong: CC2652R7 has 144 KB SRAM, not 256 KB

## Critical Path

The required order before the May 26 noon deadline was:

1. Freeze report evidence.
2. Write `report.pdf`.
3. Audit submission readiness.
4. Only then spend spare time on optional metric or answer-quality improvements.

Steps 1-4 are complete. Avoid merging corpus expansion or broad comparison support before submission unless there is enough time to rebuild indexes, rerun eval, update `report.md`, regenerate `report.pdf`, and redo the submission audit.

Recommended remaining order:

1. Keep `main` frozen and submission-safe unless a clearly verified improvement is ready.
2. If time remains, use `feature/negation-handling` for Session E because it is narrow and does not require corpus/index changes.
3. Use experimental branches for major work: `exp/rf-driver-api-corpus`, `exp/competitor-datasheets`, or similar.
4. Merge an improvement branch into `main` only after targeted tests, eval, report regeneration if needed, `pdfinfo report.pdf`, and a clean final status.

## Session A - Report Evidence Freeze

**Goal:** Collect the exact numbers and examples needed for the 4-page report without changing code.

**Inputs:**

- `PROJECT_STATUS.md`
- `FOR_AI_MODELS.md`
- `mid_term_assignment.pdf`
- `eval/eval_results.json`
- `eval/gold_set.jsonl`
- `src/utils.py`
- `src/build_index.py`
- `eval/run_eval.py`
- `eval/run_eval_dense_only.py`
- `eval/run_eval_no_rerank.py`

**Outputs:**

- `REPORT_NOTES.md` or equivalent report evidence notes
- Current metric table
- Ablation table inputs
- Per-category results table
- At least 10 manually inspected answers labeled as Correct, Partially correct, Incorrect, or Unsupported/Hallucinated
- Failure-analysis examples

**Time estimate:** 1.5-3 hours

**Dependencies:** None

**Notes:**

- Treat `eval/eval_results_annotated.json` as stale unless verified. It reports `k=8` and appears to describe an older pre-extractor, LLM-heavy run.
- Do not change code in this session.
- Running eval/ablation scripts is acceptable if time allows and local model/index dependencies are ready.

**Copy-paste prompt:**

```text
Read PROJECT_STATUS.md, FOR_AI_MODELS.md, mid_term_assignment.pdf, eval/eval_results.json, src/utils.py, and src/build_index.py.
Do not change code. Build a report evidence pack for the May 26 noon deadline.
Run current eval and the existing ablation scripts if feasible: eval/run_eval.py, eval/run_eval_dense_only.py, eval/run_eval_no_rerank.py.
Manually inspect at least 10 latest answers from eval/eval_results.json and classify them as Correct, Partial, Incorrect, or Unsupported/Hallucinated.
Produce concise notes with metrics, ablation table inputs, chunking explanation, and failure examples for the report.
```

## Session B - Write `report.pdf`

**Goal:** Produce the required up-to-4-page final report.

**Inputs:**

- `mid_term_assignment.pdf`
- `REPORT_NOTES.md` from Session A
- `PROJECT_STATUS.md`
- `FOR_AI_MODELS.md`
- `data/MANIFEST.md`
- Latest eval and ablation results

**Outputs:**

- `report.pdf`
- Editable report source file, such as `report.md`, `report.tex`, or another reproducible source

**Time estimate:** 3-5 hours

**Dependencies:** Session A

**Priority:** Highest. Target completion by May 24 or May 25 morning.

**Required report sections from the assignment:**

1. Corpus description
2. System architecture
3. Chunking strategy
4. Embedding and vector index choice
5. Retrieval method
6. Prompt design
7. Evaluation results
8. Ablation table
9. Failure analysis
10. What to improve next

**Content to include:**

- Corpus: three TI documents, 2361 chunks, PDF/HTML loaders, public TI documentation
- Chunking: fixed 512-word chunks with 64-word overlap as baseline; hierarchical section-aware chunks with 600-word cap and 500-word sub-splits as chosen strategy
- Architecture: 7-stage pipeline table or compact diagram
- Embedding/index: `BAAI/bge-large-en-v1.5`, normalized embeddings, FAISS `IndexFlatIP`, BM25Okapi
- Retrieval: dense + BM25 hybrid, max-score dedup, identifier-aware reranking
- Generation: TOC filtering, deterministic extractors before LLM, Llama 3.2 fallback, strict cited output format
- Evaluation: Hit@5 = 1.000, Answerable@Context = 0.560 after Session D
- Failures: RF API corpus gap, competitor-device corpus gap, negation/unsupported feature handling, TX-power extraction, gold-set mistakes
- Future work: RF Driver API corpus, competitor datasheets or reframed comparison questions, source-label evaluation, negation extractor improvements

**Copy-paste prompt:**

```text
Write the final 4-page report.pdf for the CC2652R7 RAG assignment.
First read mid_term_assignment.pdf, PROJECT_STATUS.md, FOR_AI_MODELS.md, data/MANIFEST.md, and REPORT_NOTES.md.
Cover exactly: corpus, architecture, chunking strategies, embedding/index choice, retrieval, prompt/generation design, evaluation, ablations, failure analysis, and future work.
Use current numbers: Hit@5=1.000 and Answerable@Context=0.560 unless REPORT_NOTES.md has newer verified results.
Keep it concise, technical, and honest about corpus gaps, metric limitations, stale/incorrect gold answers, and local Llama 3.2 constraints.
Produce report.pdf and leave the editable source file in the repo.
```

## Session C - Submission Audit

**Goal:** Verify the submission is complete and runnable before the deadline.

**Inputs:**

- `report.pdf`
- Editable report source
- `README.md`
- `requirements.txt`
- `data/MANIFEST.md`
- `eval/gold_set.jsonl`
- Current code
- `mid_term_assignment.pdf`

**Outputs:**

- Final submission checklist
- Tiny documentation-only fixes if required
- Verification results or explicit note if a command could not be run

**Time estimate:** 45-90 minutes

**Dependencies:** Session B

**Priority:** Must happen before optional code work.

**Checks:**

- `report.pdf` exists and is <= 4 pages
- Required files exist: code, data manifest, `gold_set.jsonl`, `README.md`, `requirements.txt`, final report
- README has exact running instructions:
  - `pip install -r requirements.txt`
  - `python src/build_index.py`
  - `python eval/run_eval.py`
- `data/MANIFEST.md` satisfies the assignment fields
- `answer(question: str) -> dict` interface exists through `RAGSystem.answer`
- Tests and eval are run if feasible

**Copy-paste prompt:**

```text
Audit the project for assignment submission readiness.
Read mid_term_assignment.pdf, README.md, requirements.txt, data/MANIFEST.md, PROJECT_STATUS.md, and confirm report.pdf exists.
Run tests and eval only if feasible within time: python -m pytest tests/ -q and python eval/run_eval.py.
Do not start risky refactors. Fix only tiny documentation mismatches needed for submission instructions.
Produce a short final checklist of required files and any remaining risks.
```

## Session D - Metric Fix, Completed

**Goal:** Fix the Answerable@Context hyphen normalization false negatives.

**Inputs:**

- `src/generation.py`
- `tests/test_generation.py`
- `eval/eval_results.json`

**Outputs:**

- Focused tests for hyphen/spacing normalization
- Minimal `check_answerability()` fix
- Refreshed eval result showing old and new Answerable@Context

**Time estimate:** 45-75 minutes

**Dependencies:** Sessions B and C are complete; report is already submission-safe.

**Priority:** Completed and merged to `main` at commit `48dbd30`. This stayed limited to the metric bug and did not change generation behavior.

**Known issue:**

Before Session D, `check_answerability()` checked terms such as `1.8V` and `3.8V`, but the corpus often has `1.8-V` and `3.8-V`. This created false negatives even when the system answer was correct.

Actual impact: Answerable@Context improved from 27/50 = 0.540 to 28/50 = 0.560. This removed the known voltage false negative, but did not solve the broader misses from corpus gaps, out-of-corpus comparison questions, negation metric limitations, or gold-set mistakes.

**Likely implementation direction:**

- Normalize both key terms and context by removing whitespace and hyphens before matching.
- Keep this limited to the answerability metric.
- Do not change answer generation behavior.

**Copy-paste prompt:**

```text
Fix only the Answerable@Context normalization bug.
Read WORK_PLAN.md, REPORT_NOTES.md, FOR_AI_MODELS.md, and src/generation.py, especially check_answerability().
Add focused tests showing "1.8V" matches context text containing "1.8-V", and similarly for "3.8V".
Implement minimal normalization in check_answerability() without changing generation behavior.
Run targeted tests, then full tests if feasible, then python eval/run_eval.py.
Report the old and new Answerable@Context numbers.
If the metric changes, update report.md, regenerate report.pdf with python scripts/render_report.py, and verify pdfinfo report.pdf is still <= 4 pages.
```

## Session E - Negation Quote/Answer Fix, Optional

**Goal:** Make unsupported-feature questions answer cleanly with the authoritative CC2652R7 feature list.

**Inputs:**

- `src/generation.py`
- `src/rag_system.py`
- `tests/test_generation.py`
- Negation entries in `eval/eval_results.json`

**Outputs:**

- Focused tests for Wi-Fi, USB, LTE/cellular, Ethernet, Bluetooth Classic, and Wi-SUN style questions
- Minimal generation fix
- Refreshed tests, stress test, and eval if feasible

**Time estimate:** 1.5-2.5 hours

**Dependencies:** Session B draft exists; preferably after Session D

**Priority:** Optional before deadline, useful only if time remains.

**Important context:**

- `_try_yes_no_answer()` already contains some unsupported-feature logic.
- Future work should first reproduce the current failures before adding a new extractor.
- Do not reintroduce the old `_should_refuse_without_extractor()` gate.
- Do not revisit the anchor injection placement decision.

**Likely implementation direction:**

- Add or refine a small negative-feature extractor for unsupported connectivity features.
- Prefer grounding in `datasheet_hier_chunk_0000` or the CC2652R7-specific support list.
- Return the established `QUOTE`, `ANSWER`, `SOURCE` format.

**Copy-paste prompt:**

```text
Fix negation handling for unsupported features without revisiting prior failed approaches.
Read FOR_AI_MODELS.md, PROJECT_STATUS.md, src/generation.py, and src/rag_system.py.
Reproduce behavior for Wi-Fi, USB, LTE/cellular, Ethernet, Bluetooth Classic, and Wi-SUN questions.
Add focused tests requiring a clear No answer grounded in the CC2652R7 support/features list, preferably datasheet_hier_chunk_0000.
Use the smallest change: likely a negative-feature extractor and/or anchor injection for unsupported connectivity terms.
Run targeted tests, full tests, stress test, and eval if feasible.
```

## Session F - RF Driver API Corpus Expansion, Post-Deadline Unless Report Is Done Early

**Goal:** Add the missing RF Driver API reference corpus and rebuild indexes.

**Inputs:**

- TI RF Driver API Reference PDF, supplied or approved by the user
- `src/build_index.py`
- `src/utils.py`
- `data/raw/`
- `data/MANIFEST.md`
- `eval/gold_set.jsonl`

**Outputs:**

- RF Driver API PDF added to `data/raw/`
- Updated corpus manifest
- Rebuilt FAISS and BM25 indexes
- Refreshed eval results
- Documented chunk-count and metric changes

**Time estimate:** 4-8 hours

**Dependencies:** User provides or approves the exact RF Driver API PDF; `report.pdf` is already safe.

**Priority:** Not before report unless there is unexpected spare time.

**Important context:**

- RF API failures involving `RF_open`, `RF_close`, `RFCCpePatchFxp`, `RF_EventLastCmdDone`, and CPE patch are expected corpus gaps.
- Do not debug these as retrieval or generation bugs before indexing the missing document.

**Copy-paste prompt:**

```text
Add the TI RF Driver API reference to the corpus to address RF_open/RFCCpePatchFxp/RF_EventLastCmdDone gaps.
First read PROJECT_STATUS.md, FOR_AI_MODELS.md, src/build_index.py, src/utils.py, and eval/gold_set.jsonl.
Do not treat current RF API failures as pipeline bugs; they are corpus gaps.
Add the PDF to data/raw, update loading/indexing as needed, rebuild FAISS and BM25, and rerun tests/eval.
Document changed chunk counts and category-level eval changes.
```

## Session G - Competitor Datasheets, Low Priority

**Goal:** Decide whether to support comparison questions by indexing competitor device datasheets.

**Inputs:**

- Comparison failures in `eval/eval_results.json`
- `eval/gold_set.jsonl`
- Candidate datasheets for CC2652R1, CC2652P, CC1352R, and CC2652RB
- `data/MANIFEST.md`
- `src/build_index.py`

**Outputs:**

- Either expanded corpus and refreshed eval, or a recommendation to remove/reframe those gold questions
- Updated manifest if new datasheets are added
- Updated report only if done before submission and time permits

**Time estimate:** 6-10 hours

**Dependencies:** Report done; user approves adding broader corpus.

**Priority:** After submission.

**Important context:**

- Most comparison failures are not CC2652R7 RAG failures; the comparison device specs are not in the current corpus.
- Adding comparison datasheets changes the project scope from CC2652R7-only documentation to a broader device-family corpus.

**Copy-paste prompt:**

```text
Investigate the comparison-question corpus gap.
Read PROJECT_STATUS.md, FOR_AI_MODELS.md, eval/eval_results.json, and eval/gold_set.jsonl comparison entries.
Decide whether to add competitor datasheets or reframe the comparison gold set.
If adding corpus, update MANIFEST, rebuild indexes, rerun eval, and report the category-level impact.
Keep this separate from the CC2652R7 report unless there is time after report.pdf is complete.
```

## Recommended Timeline

**May 23-24**

- Complete Session A.
- Start and preferably complete Session B.

**May 25 morning**

- Finish Session B if needed.
- Run Session C.
- At this point, `report.pdf` should be submission-ready.

**May 25 afternoon/evening**

- If the report is safe, run Session D.
- If Session D is done and there is still time, run Session E.
- Avoid Session F or G unless the report is already finalized and the user explicitly wants the risk.

**May 26 morning**

- Final submission audit only.
- No risky code or corpus changes.

## Decision Rules for Future Sessions

- If `report.pdf` does not exist, do Session A or B only.
- If `report.pdf` exists but has not been audited, do Session C before optional code work.
- If less than 6 hours remain before the deadline, do not start corpus expansion.
- If an optional fix changes metrics, rerun eval and update the report source before regenerating `report.pdf`.
- If eval results conflict with `PROJECT_STATUS.md`, use the most recent verified command output and document the command/date.
- If a result depends on stale files, say so explicitly rather than reporting it as current.

## Open Questions / User Decisions

1. Should the final report source be Markdown, LaTeX, or another format?
2. If spare time remains, should optional effort go first to the metric fix or the negation fix?
3. Should RF Driver API expansion wait until after submission unless the report is already finished early?

Recommended answers:

1. Use whichever format can reliably produce a clean <=4-page PDF fastest on this machine.
2. Do the metric fix first; it is smaller and improves reported evaluation honesty.
3. Yes, wait on RF Driver API expansion unless the report is finished and audited early.
