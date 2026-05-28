# CC2652R7 RAG Pipeline — Project Status

## What This Project Is

A Retrieval-Augmented Generation (RAG) pipeline over TI CC2652R7 hardware documentation,
built as a university mid-assignment. The system demonstrates that bare Llama 3.2 3B
hallucinates on device-specific questions while RAG grounds answers in TI documentation.

**Assignment:** Build, evaluate, and report on a RAG system.
**Submission state:** `main` is submission-safe and pushed to GitHub. `report.md` and a 2-page `report.pdf` reflect the latest verified report state. Future work must be done on short-lived branches, validated there, opened as a pull request, and merged into `main` only through the PR.
**Deadline:** Original deadline was 2026-05-26 at 12:00 noon Asia/Jerusalem. A one-week extension was granted; treat the working deadline as 2026-06-02, exact time TBD, assuming noon until clarified.
**Internal design note:** `SYSTEM_DESIGN_NOTES.md` explains the architecture, design tradeoffs, industry alignment, and modern retrieval/indexing alternatives beyond FAISS/Chroma.

## Branching and Change Policy

- `main` is the stable submission branch. Keep it runnable and do not force-push it.
- Session D (`fix/answerability-normalization`) was merged to `main` at commit `48dbd30`.
- Session E (`feature/negation-handling`) was verified and merged at commit `ab8b70c`.
- Current pushed `main` also includes updated failure-analysis and improvement-roadmap docs, including `RAG_EXPLICIT_DATA_FAILURE_CASE_STUDY.md`.
- Create `feature/source-label-eval` from `main` for the next metric improvement.
- Use short-lived branches for narrow optional improvements, for example `feature/negation-handling`, `feature/source-label-eval`, or `feature/tx-power-extractor`.
- Use experimental branches for major work, for example `exp/rf-driver-api-corpus` or `exp/competitor-datasheets`.
- Do not edit, commit, or push work directly on `main`.
- Open a pull request for every change and merge into `main` only through the PR after validation passes.
- Do not merge corpus expansion, gold-set rewrites, retrieval changes, or answer-generation behavior changes into `main` unless tests, `python eval/run_eval.py`, report updates, PDF regeneration, and `pdfinfo report.pdf` all pass.

---

## Corpus

Three TI documents, all indexed together:

| Document | File | Chunks | Notes |
|----------|------|--------|-------|
| CC2652R7 Datasheet | `data/raw/cc2652r7.pdf` | 60 | Features list in `datasheet_hier_chunk_0000` |
| TI TRM (Technical Reference Manual) | `data/raw/swcu192.pdf` | 2237 | Bulk of corpus |
| SimpleLink SDK User's Guide | `data/raw/Users_Guide.html` | 64 | SDK-level docs |
| **Total** | | **2361 chunks** | |

**Critical corpus gap:** RF driver API (RF_open, RF_close, RFCCpePatchFxp,
RF_EventLastCmdDone, CPE patch) is in a separate TI SDK RF Driver API Reference PDF
**not indexed**. All questions about these symbols correctly return "not found."

---

## System Architecture

```
Question
    │
    ├── Stage 1: Dense retrieval (FAISS, BAAI/bge-large-en-v1.5, k=20)
    ├── Stage 2: BM25 retrieval (BM25Okapi, k=20)
    ├── Stage 3: Hybrid merge (max-score dedup → top 20)
    ├── Stage 4: Identifier pin detection (firmware symbols, hex addresses)
    ├── Stage 5: Cross-encoder rerank (ms-marco-MiniLM-L-6-v2, +3.0 identifier boost)
    ├── Stage 5b: Anchor chunk injection (prepend datasheet_hier_chunk_0000 for spec/support Qs)
    ├── Stage 6: Deduplicate + token budget (max 2000 words)
    └── Stage 7: Generation
                ├── TOC filter (remove table-of-contents chunks)
                ├── Deterministic extractors (15 regex-based extractors, run first)
                └── LLM fallback (Llama 3.2 3B via Ollama, temp=0, top_p=0.1)
```

---

## File-by-File Guide

### `src/build_index.py`
Builds and saves FAISS + BM25 indexes. Call once, indexes persist to `data/processed/`.
- `build_faiss_index()` — embeds chunks with `BAAI/bge-large-en-v1.5`, saves `faiss.index` + `chunks.json`
- `build_bm25_index()` — tokenizes + saves `bm25.pkl` + `bm25_chunks.json`
- `load_faiss_index()` / `load_bm25_index()` — used at startup by `load_rag_system()`

### `src/retrieval.py`
All retrieval logic.
- `retrieve_dense()` — FAISS inner-product search, returns scored chunks
- `retrieve_bm25()` — BM25Okapi keyword search
- `hybrid_retrieve()` — merges dense + BM25, max-score dedup, returns top 20
- `is_identifier_token()` — detects firmware symbols (hex, ALLCAPS_WITH_UNDERSCORE, camelCase identifiers)
- `rerank()` — cross-encoder `ms-marco-MiniLM-L-6-v2` + +3.0 boost for identifier token matches, returns top k=5
- `Retriever` — convenience class wrapping all of the above

### `src/generation.py`
~985 lines. Core generation logic.

**Key functions:**

| Function | Purpose |
|----------|---------|
| `generate_answer(question, chunks)` | Main entry. Runs TOC filter → extractors → LLM fallback |
| `_answer_from_context(qn, chunks)` | Runs refusal check, yes/no support logic, then all 15 extractors |
| `_refuse_unanswerable_question()` | Returns "not found" for RF API, price, cross-device comparisons |
| `deduplicate_and_budget(chunks, max_words=2000)` | Dedup by chunk_id, enforce word budget |
| `filter_toc_chunks(chunks)` | Removes table-of-contents chunks (≥4 dot-leader occurrences) |
| `format_context(chunks)` | Formats chunks as `[chunk_id | source | location]\ntext` |
| `validate_answer(answer, chunks)` | Checks technical literals (hex, units) are present in context |
| `check_answerability(ref, chunks)` | Eval metric: checks if reference key terms appear in context |
| `_rank_chunks(question, chunks)` | Query-aligned reordering before LLM (datasheet boosted +12) |

**The 15 deterministic extractors** (checked in this order before LLM):
1. `_try_memory_answer` — flash, SRAM, ROM sizes
2. `_try_protocol_answer` — wireless protocol list
3. `_try_cpu_answer` — CPU type (skips clock/frequency questions)
4. `_try_clock_answer` — CPU clock frequency (48 MHz)
5. `_try_voltage_answer` — supply voltage range
6. `_try_package_answer` — package type/size
7. `_try_temperature_answer` — operating temperature range (-40 to +105°C)
8. `_try_rf_core_answer` — RF coprocessor type (Cortex-M0)
9. `_try_ble_sensitivity_answer` — BLE receive sensitivity (-99 dBm)
10. `_try_gpio_answer` — GPIO count (31 for VQFN48)
11. `_try_adc_answer` — ADC resolution/sample rate
12. `_try_serial_answer` — UART/SPI/I2C/I2S counts
13. `_try_timer_answer` — hardware timer count/configuration
14. `_try_tx_power_answer` — RF TX power levels
15. `_try_rf_command_chain_answer` — RF command chaining

**PROMPT_TEMPLATE** has hard rules against:
- Wi-Fi/Wi-SUN conflation from SimpleLink family lists
- Inferring device support from nearby platform mentions
- Fabricating symbols (must appear verbatim in context)
- Hedging / "however" / guesses

### `src/rag_system.py`
Orchestrates the full pipeline. `RAGSystem.answer(question)` runs all 7 stages and
returns `{"answer", "sources", "retrieved_chunks", "trace", "validation"}`.

**Stage 5b anchor injection** (key design decision):
For spec-term and unsupported-connectivity questions (uart, spi, clock, voltage,
flash, sram, gpio, Wi-Fi, USB, LTE/cellular, Ethernet, Bluetooth Classic, etc.),
`datasheet_hier_chunk_0000` (features list) is **prepended** to reranked results before
the token budget is applied. This guarantees it survives `deduplicate_and_budget`.
**Important:** injection happens AFTER reranking — the cross-encoder demotes chunk_0000
for specific peripheral queries if injected before.

`load_rag_system()` — loads all indexes from `data/processed/`, returns ready `RAGSystem`.

### `eval/run_eval.py`
Runs 50 gold-set questions, reports Hit@k and Answerable@Context per category.
Results saved to `eval/eval_results.json`.

### `eval/stress_test.py`
13 adversarial questions: out-of-corpus, exact symbol, negation, hallucination traps, ambiguous.
Results saved to `eval/stress_test_results.json`.

### `demo.py`
Two-demo script showing bare LLM vs RAG:
- Demo 1 (always): "How much flash / CPU clock?" — bare Llama hallucinates, RAG cites 704KB/48MHz
- Demo 2 (optional): Live UART capture from CC2652R7 board, or RF power domain fallback question

### `eval/gold_set.jsonl`
50 Q&A pairs across 5 categories (10 each): factual, numerical, negation, comparison, debugging.
Each entry: `{"question", "reference_answer", "must_cite_chunk_ids", "category"}`.

---

## Evaluation Results (as of 2026-05-26 on `main`; Session E verified at `ab8b70c`)

| Metric | Score | Detail |
|--------|-------|--------|
| Hit@5 | **1.000** | 50/50 — perfect retrieval |
| Answerable@Context | **0.560** | 28/50 — measures if reference key terms appear in retrieved context |

**Per-category Answerable@Context:**

| Category | Hit@5 | Answerable | Notes |
|----------|-------|------------|-------|
| numerical | 1.000 | 0.900 | 9/10 — remaining miss is an RF TX-power retrieval/extraction error |
| factual | 1.000 | 0.700 | 7/10 — one voltage normalization false negative fixed; remaining misses are TX-power/gold/corpus issues |
| negation | 1.000 | 0.600 | 6/10 — LTE/USB/Ethernet/Wi-Fi are corpus-absent |
| debugging | 1.000 | 0.400 | 4/10 — RF API symbols absent from corpus |
| comparison | 1.000 | 0.200 | 2/10 — needs CC2652R1/CC2652P specs not in corpus |

**Note on Answerable@Context metric:** Session D fixed the known voltage normalization bug:
`check_answerability()` now normalizes spaces and hyphens so "1.8V" / "3.8V" match
corpus text such as "1.8-V" / "3.8-V". The metric still checks reference key-term
presence, not full answer correctness.

Session E did not change headline metrics, but it improved unsupported-connectivity answer
grounding. The saved eval answers for Wi-Fi, USB, LTE/cellular, Ethernet, and Bluetooth
Classic now answer from `datasheet_hier_chunk_0000` instead of nearby application text.

Session E verification before merging to `main`:

- `python -m pytest tests/test_generation.py -q` passed 12 tests.
- `python -m pytest tests/test_rag_system.py::test_answer_injects_datasheet_anchor_for_unsupported_connectivity_questions -q` passed 5 tests.
- `python eval/run_eval.py` completed with Hit@5 = 1.000 and Answerable@Context = 0.560.
- `python scripts/render_report.py` completed, and `pdfinfo report.pdf` reports 2 pages.
- Full `python -m pytest tests/ -q` was attempted but stopped after model-heavy no-output behavior.

## Extension Plan

The one-week extension should be used for controlled, reportable improvements:

1. Continue `feature/source-label-eval` to add meaningful source labels or anchor-style source-hit evaluation. This addresses the biggest current evaluation weakness: Hit@5 is non-discriminative because `must_cite_chunk_ids` is empty.
2. Add labeled retrieval metrics on the labeled subset only: `Source Hit@1`, `Source Hit@5`, `MRR`, `Precision@5`, and `Recall@5`. Do not report these for unlabeled questions.
3. Classify each failure as a missing-source issue, retrieval miss, generation/validation error, or gold-set mismatch. This prevents optimizing the wrong part of the pipeline.
4. Create `feature/tx-power-extractor` for the narrow max RF output power / standard-mode TX-power failures after source-label evaluation is handled.
5. Refresh `report.md` and `report.pdf` after metric or claim changes.
6. Treat RF Driver API corpus expansion as experimental only (`exp/rf-driver-api-corpus`), because it requires source approval, index rebuild, manifest/report updates, and a full audit.

---

## Known Failures and Improvement Opportunities

### 1. Corpus Gap — RF Driver API (Impact: ~12 questions)
**Problem:** RF_open, RF_close, RFCCpePatchFxp, RF_EventLastCmdDone are in a separate
TI SDK RF Driver API Reference PDF, not indexed.
**Fix:** Add the RF Driver API Reference PDF to `data/raw/`, re-run chunking and indexing.
This would unlock the debugging category (currently 4/10) and several factual/negation questions.

### 2. Corpus Gap — Competitor Device Specs (Impact: 8 comparison questions)
**Problem:** All CC2652R1, CC2652P, CC1352R, CC2652RB spec comparisons fail because
those datasheets are not indexed.
**Fix:** Either add competitor datasheets or reframe gold-set comparison questions to
be self-referential (CC2652R7 properties only).

### 3. Answerable Metric Bug — Hyphen Normalization (Fixed in Session D)
**Problem:** `check_answerability` matched "1.8V" but corpus has "1.8-V".
**Status:** Fixed in `main` at commit `48dbd30`. The latest eval improved from 0.540 (27/50)
to 0.560 (28/50).

### 4. Unsupported Connectivity Negation — Merged in Session E
**Problem:** For "Does CC2652R7 support Wi-Fi?", the system previously retrieved or quoted
nearby product-application text rather than the authoritative support list.
**Status:** Merged to `main` at `ab8b70c`. Unsupported Wi-Fi, USB, LTE/cellular,
Ethernet, and Bluetooth Classic answers now cite `datasheet_hier_chunk_0000`. This has not
changed Answerable@Context because the metric checks gold reference key terms, not answer
quality or citation quality.

### 5. RF TX Power — Answer Present, Retrieval/Extraction Fails
**Problem:** The standard-mode answer is present, but not in the same wording as the
question. `datasheet_hier_chunk_0001_sub0` states `+5 dBm TX at 9.7 mA`, and
`datasheet_hier_chunk_0030` lists TX power setting `5` with `4.8 dBm` typical output
power. The system retrieves TRM chunks about `CMD_SET_TX20_POWER` and the `20 dBm PA`
path instead.
**Fix:** Add source labels for the TX-power questions, then add TX-power-specific
retrieval/reranking, table-aware extraction for Table 7-1, normalization of `4.8 dBm`
to `+5 dBm`, and numeric answer validation against cited `dBm` evidence.

### 6. Evaluation Metric Weakness — Source Labels Missing
**Problem:** `must_cite_chunk_ids` is empty for all current gold entries, making Hit@5
non-discriminative.
**Fix:** Use `feature/source-label-eval` to add source labels or a separate anchor-style
metric. Preserve Q/A content unless a specific gold error must be documented.

### 7. Report Status
`report.md` and `report.pdf` are complete. `report.pdf` is 2 A4 pages, within the
assignment's 4-page limit. If future branches change metrics, corpus, or claims, update
`report.md`, regenerate with `python scripts/render_report.py`, and verify
`pdfinfo report.pdf` before merging to `main`.

---

## How to Run

```bash
# Run full evaluation
python eval/run_eval.py

# Run demo (no board)
python demo.py

# Run tests
python -m pytest tests/ -q

# Run stress test
python eval/stress_test.py

# Ablation: dense only
python eval/run_eval_dense_only.py

# Ablation: no rerank
python eval/run_eval_no_rerank.py
```

---

## Design Decisions Worth Knowing

1. **Extractors before LLM:** The 15 deterministic extractors run before the LLM for
   all spec questions. This avoids 3B hallucination entirely for ~40% of questions.

2. **Anchor injection after reranking:** Injecting chunk_0000 before the cross-encoder
   causes the encoder to demote it (it's a features list, not a focused answer).
   Injecting after reranking and prepending (not appending) ensures budget survival.

3. **TOC filter:** TRM contains table-of-contents chunks (page refs like `......123`)
   that score well in BM25 but contain no useful content. Detected by ≥4 dot-leader
   occurrences. Removed before generation.

4. **Gold set SRAM answer is wrong:** Gold says "256KB SRAM" but corpus says "144KB
   ultra-low leakage SRAM." The extractor returning 144KB is correct. The gold
   answer confusion is CC2652R1's SRAM (256KB) vs CC2652R7's (144KB).

5. **Temperature: 105°C not 85°C:** Some sources cite 85°C (commercial grade).
   The CC2652R7 datasheet operating ambient spec is -40 to +105°C. Extractor uses 105°C.

6. **Ollama settings:** `temperature=0, top_p=0.1, num_predict=180`. Temperature=0
   is critical for reproducibility; num_predict=180 caps runaway generation.
