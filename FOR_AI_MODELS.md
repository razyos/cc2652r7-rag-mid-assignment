# Context for AI Models Working on This Project

This file is a self-contained briefing for any AI model (ChatGPT, Gemini, Codex, Claude, etc.)
asked to help with this project. Read this file first before touching any code.

---

## What This Is

A RAG (Retrieval-Augmented Generation) pipeline for a university assignment.
Domain: TI CC2652R7 wireless microcontroller firmware documentation.
Goal: Show that bare Llama 3.2 3B hallucinates on hardware questions; RAG with TI docs
gives accurate, cited answers.

Language: Python 3.12. No web framework. Local inference via Ollama (Llama 3.2 3B).

Repository: https://github.com/razyos/cc2652r7-rag-mid-assignment

Branching policy:
- `main` is the stable submission branch. Keep it runnable and submission-ready.
- Use short-lived branches for optional work. Current Session D branch: `fix/answerability-normalization`.
- Before merging to `main`, run relevant tests; run `python eval/run_eval.py` for metric-affecting changes.
- If `report.md`, metrics, or report claims change, regenerate `report.pdf` with `python scripts/render_report.py` and verify it is <= 4 pages.
- Do not force-push `main`, and do not commit ignored local artifacts.

---

## The Pipeline (7 Stages)

```
Question
 → [1] Dense retrieval: FAISS (BAAI/bge-large-en-v1.5), k=20
 → [2] BM25 retrieval: BM25Okapi, k=20
 → [3] Hybrid merge: max-score dedup, top 20
 → [4] Identifier detection: firmware symbols, hex addresses
 → [5] Cross-encoder rerank: ms-marco-MiniLM-L-6-v2, +3.0 boost for identifier matches, k=5
 → [5b] Anchor injection: PREPEND datasheet_hier_chunk_0000 for spec-term questions
 → [6] Token budget: deduplicate by chunk_id, max 2000 words
 → [7] Generation:
         TOC filter → 15 deterministic extractors → LLM fallback (Llama 3.2 3B)
 → Answer
```

---

## Directory Structure

```
mid_ass/
├── src/
│   ├── build_index.py      # Build/load FAISS + BM25 indexes
│   ├── retrieval.py        # Dense, BM25, hybrid, rerank, Retriever class
│   ├── generation.py       # Extractors, LLM prompt, TOC filter, budget, validation
│   └── rag_system.py       # RAGSystem class: orchestrates all 7 stages
├── eval/
│   ├── gold_set.jsonl      # 50 Q&A pairs (factual/numerical/negation/comparison/debugging)
│   ├── run_eval.py         # Main eval: Hit@5 + Answerable@Context
│   ├── run_eval_dense_only.py  # Ablation: dense retrieval only
│   ├── run_eval_no_rerank.py   # Ablation: no cross-encoder rerank
│   ├── stress_test.py      # 13 adversarial questions
│   └── eval_results.json   # Latest eval output
├── data/
│   ├── raw/                # Source PDFs + HTML (cc2652r7.pdf, swcu192.pdf, Users_Guide.html)
│   └── processed/          # faiss.index, chunks.json (2361 chunks), bm25.pkl
├── tests/                  # pytest suite (37 tests, all passing)
├── demo.py                 # Two-demo comparison: bare LLM vs RAG
├── PROJECT_STATUS.md       # Full project status, results, known issues
└── FOR_AI_MODELS.md        # This file
```

---

## Corpus Facts

- **2361 total chunks:** 2237 TRM, 64 datasheet, 60 SDK guide
- **Key chunk:** `datasheet_hier_chunk_0000` — the CC2652R7 features list.
  Contains: 704KB flash, 144KB SRAM, 48 MHz Cortex-M4F, 31 GPIO, 1.8-V to 3.8-V supply, etc.
- **Corpus gap:** RF Driver API (RF_open, RFCCpePatchFxp, RF_EventLastCmdDone) is in
  a separate TI document **not indexed**. Questions about these correctly return "not found."
- **Gold answer bug:** Gold set says "256KB SRAM" but corpus says 144KB (correct for CC2652R7).
  256KB is the CC2652R1. The system returning 144KB is correct, not a bug.

---

## Current Eval Results

Run: `python eval/run_eval.py`

| Metric | Score |
|--------|-------|
| Hit@5 | 1.000 (50/50) |
| Answerable@Context | 0.540 (27/50) |

Per category:
- numerical: Hit=1.0, Answerable=0.90 (9/10)
- factual: Hit=1.0, Answerable=0.60 (6/10)
- negation: Hit=1.0, Answerable=0.60 (6/10)
- debugging: Hit=1.0, Answerable=0.40 (4/10)
- comparison: Hit=1.0, Answerable=0.20 (2/10)

Answerable@Context checks if reference answer key terms appear in retrieved context.
**Known metric bug:** it matches "1.8V" but corpus has "1.8-V" → false negatives on
voltage/temperature questions (the answers are actually correct).

---

## Known Issues and What to Improve

### High Priority

**1. Negation questions — LLM quotes irrelevant context instead of saying "No"**
Questions like "Does CC2652R7 support Wi-Fi/USB/LTE/Ethernet?" retrieve a product-applications
list chunk ("smart speakers, wearables...") and the 3B LLM quotes it instead of saying No.
- Location: `src/generation.py` — `_refuse_unanswerable_question()` and/or a new extractor
- Fix: Add `_try_negative_feature_answer()` mapping {"wifi", "wi-fi", "usb", "lte", "ethernet",
  "cellular", "bt classic", "br/edr"} → "No, the CC2652R7 does not support {feature}."
  Evidence: check that the feature word does NOT appear in the features list of chunk_0000.

**2. Answerable metric — hyphen normalization**
- Location: `src/generation.py` — `check_answerability()`
- Fix: normalize key terms and corpus text by stripping hyphens before substring matching
  `key_term_normalized = key_term.replace("-", "").replace(" ", "").lower()`
  `corpus_normalized = corpus.replace("-", "").replace(" ", "").lower()`

**3. Report not written** — 4-page PDF required by assignment. Sections needed:
  corpus, architecture, chunking, embedding, retrieval, prompt, eval results, ablation, failures, future work

### Medium Priority

**4. Add RF Driver API PDF to corpus**
Adding TI's RF Driver API Reference would fix ~12 failing questions (debugging + factual + negation categories).
Steps: place PDF in `data/raw/`, re-run `src/build_index.py` with the new document.

**5. Comparison questions**
8/10 comparison questions require CC2652R1/CC2652P/CC1352R specs not in corpus.
Either add those datasheets or rewrite the comparison questions to be self-referential.

---

## Code Conventions

- All imports inside `src/generation.py` use `import re as _re` (leading underscore = module-private)
- Extractors return `None` (no match) or a string in `QUOTE: ...\nANSWER: ...\nSOURCE: ...` format
- `_Evidence` is a frozen dataclass: `(score: float, quote: str, answer: str, chunk_id: str)`
- `_best_regex(chunks, patterns, answer_builder, base_score)` — iterates all chunks,
  finds the highest-scoring regex match, returns `_Evidence`
- `_format_evidence(evidence)` — formats `_Evidence` into the QUOTE/ANSWER/SOURCE string

---

## Running the Project

```bash
# Activate virtualenv first (if using one)
# All commands from mid_ass/ directory

# Full evaluation
python eval/run_eval.py

# Single question test
python -c "
from src.rag_system import load_rag_system
system = load_rag_system()
result = system.answer('How much flash memory does the CC2652R7 have?')
print(result['answer'])
"

# Run all tests
python -m pytest tests/ -q

# Demo (no hardware)
python demo.py
```

---

## What Was Already Tried (Don't Repeat)

- **One-shot example in prompt:** Removed. The 3B model pattern-matched the example
  and answered "704KB" for every unrelated question.
- **Injecting chunk_0000 before reranking:** Cross-encoder demotes it below top-5 for
  specific peripheral queries. Must inject AFTER reranking.
- **Appending anchor chunk instead of prepending:** Gets cut off by token budget.
  Must prepend so it's always within the 2000-word limit.
- **`_should_refuse_without_extractor()` gating:** Was blocking all debugging questions.
  Removed from `generate_answer()` call path.
- **85°C temperature:** Incorrect (commercial grade). Corpus operating ambient is 105°C.
- **256KB SRAM:** Gold set is wrong. CC2652R7 has 144KB; extractor correctly returns 144KB.

---

## File Size Reference

| File | Lines | Notes |
|------|-------|-------|
| src/generation.py | ~990 | Largest file; contains all 15 extractors |
| src/retrieval.py | ~150 | Clean, stable |
| src/rag_system.py | ~150 | Orchestrator |
| src/build_index.py | ~80 | Run once |
| eval/run_eval.py | ~92 | Eval harness |
| tests/ | 37 tests | All passing |
