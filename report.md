# CC2652R7 Technical Documentation RAG System

**Corpus:** Texas Instruments CC2652R7 wireless MCU documentation  
**System:** local retrieval-augmented generation pipeline, Python 3.12, Ollama Llama 3.2 3B fallback  
**Date:** May 2026

## 1. Corpus and Task

The corpus is public Texas Instruments documentation for the CC2652R7 SimpleLink wireless microcontroller. It was chosen because device-specific firmware and hardware questions are easy for a general LLM to confuse with nearby CC26xx variants, while the official documents contain exact values, register details, and SDK constraints. The indexed data contains three documents and 2361 processed chunks:

| Source | Role | Chunks |
|---|---:|---:|
| `data/raw/cc2652r7.pdf` | CC2652R7 datasheet | 60 |
| `data/raw/swcu192.pdf` | CC13x2x7/CC26x2x7 TRM | 2237 |
| `data/raw/Users_Guide.html` | SimpleLink SDK User's Guide | 64 |
| **Total** |  | **2361** |

The system is intended to answer firmware-debugging, hardware-specification, register-level, API-usage, absence, and comparison questions. The most important single chunk is `datasheet_hier_chunk_0000`, which contains the datasheet feature list: 48-MHz Arm Cortex-M4F, 704 KB flash, 144 KB SRAM, Bluetooth 5.2 Low Energy, IEEE 802.15.4/Zigbee/Thread/Matter support, 1.8-V to 3.8-V supply, and 31 GPIOs. Important corpus gaps remain: the TI RF Driver API Reference is not indexed, and competitor datasheets such as CC2652R1/CC2652P/CC1352R are not indexed.

## 2. System Architecture

The implementation exposes `RAGSystem.answer(question)` and returns `answer`, `sources`, `retrieved_chunks`, plus diagnostic trace and validation fields. The pipeline is manual rather than a black-box framework wrapper:

| Stage | Component | Purpose |
|---|---|---|
| 1 | Dense retrieval | FAISS search over normalized BGE embeddings, candidate `k=20` |
| 2 | BM25 retrieval | Keyword retrieval with `BM25Okapi`, candidate `k=20` |
| 3 | Hybrid merge | Deduplicate by `chunk_id`, keep the max score, top 20 |
| 4 | Identifier detection | Detect firmware symbols, hex addresses, register-like names, and all-caps identifiers |
| 5 | Reranking | Cross-encoder rerank with exact identifier-match boost |
| 6 | Anchor and budget | Prepend datasheet feature chunk for spec questions, deduplicate, keep about 2000 words |
| 7 | Generation | Remove table-of-contents chunks, run deterministic extractors, then use local Llama fallback |

The anchor step is intentionally after reranking. Earlier experiments showed that injecting the broad datasheet feature list before the cross-encoder could demote it for focused peripheral queries; prepending it after reranking ensures high-value feature facts survive the context budget.

## 3. Chunking

Two chunking strategies were implemented. The baseline fixed strategy uses 512-word chunks with 64-word overlap. It is simple and reproducible, but ignores document structure and can split tables or sections awkwardly.

The current indexed strategy is hierarchical and section-aware. PDF pages and HTML `h2`/`h3` sections are kept intact when they are at most 600 words; longer units are split into approximately 500-word subchunks. The code uses word counts, although some planning notes use the word "tokens." Each chunk stores `chunk_id`, `doc_id`, text, and metadata such as source file, page, section, and chunking strategy.

Chunking helped because the datasheet first-page feature list remains a compact chunk, allowing many spec answers to be cited from `datasheet_hier_chunk_0000`. It hurt in table-heavy cases: the "maximum RF output power" question currently retrieves a transmit-current table cell and answers `+0 dBm`, while the expected answer is `+20 dBm`. No chunking strategy can fix the RF Driver API failures because that source document is absent.

## 4. Embedding, Indexing, and Retrieval

Embeddings are produced with `BAAI/bge-large-en-v1.5`, normalized, and stored in a FAISS `IndexFlatIP`. Inner product over normalized vectors is equivalent to cosine similarity and is deterministic enough for a local reproducible index. A BM25 index is also built over the same chunks and stored with the processed data. `src/build_index.py` rebuilds the processed artifacts from the raw corpus.

Retrieval combines semantic and lexical evidence. Dense retrieval handles paraphrases such as "supply range" versus "single supply voltage"; BM25 preserves exact symbols and numeric strings. The merged candidate set is reranked by `cross-encoder/ms-marco-MiniLM-L-6-v2`. If the query contains identifiers such as `RF_open`, `RFCCpePatchFxp`, register names, or hex values, chunks with exact identifier matches receive an additional +3.0 boost. This is important for embedded documentation, where exact symbol identity matters more than general semantic similarity.

## 5. Prompt and Generation Design

Generation is extractor-first. Before calling the LLM, the system removes table-of-contents chunks and tries deterministic extractors for common device facts: memory sizes, protocols, unsupported connectivity, CPU, clock, voltage, package, temperature, RF core, BLE sensitivity, GPIO count, ADC, serial interfaces, timers, TX power, and RF command chaining. These extractors return a strict cited format:

```text
QUOTE: ...
ANSWER: ...
SOURCE: chunk_id
```

If no extractor applies, the local Ollama `llama3.2` model is called with `temperature=0`, `top_p=0.1`, and `num_predict=180`. The prompt requires answers to use only retrieved context, cite chunks, avoid guesses, avoid Wi-Fi/Wi-SUN conflation, and say that information was not found when evidence is missing. A validation pass checks that technical literals such as units, hex values, and symbols in the answer appear in retrieved context.

## 6. Evaluation Results

The gold set contains 50 questions: 10 factual, 10 numerical, 10 negation/absence, 10 comparison, and 10 debugging. The latest saved evaluation uses `k=5`.

| Metric | Value | Count | Caveat |
|---|---:|---:|---|
| Legacy Hit@5 | 1.000 | 50/50 | Continuity metric; unlabeled entries still count as hits |
| Source-labeled Hit@5 | 1.000 | 14/14 labeled | Focused subset requiring `datasheet_hier_chunk_0000` |
| Source-labeled MRR@5 | 0.964 | 14 labeled | Rank-sensitive source metric |
| Answerable@Context | 0.560 | 28/50 | Checks reference key terms in context, not full answer correctness |

| Category | N | Hit@5 | Answerable@Context |
|---|---:|---:|---:|
| Numerical | 10 | 1.000 | 0.900 |
| Factual | 10 | 1.000 | 0.700 |
| Negation | 10 | 1.000 | 0.600 |
| Debugging | 10 | 1.000 | 0.400 |
| Comparison | 10 | 1.000 | 0.200 |

These metrics must be interpreted carefully. The legacy Hit@5 is kept for comparison with earlier runs, while the source-labeled metrics are computed only on the 14 entries that now have required source labels; the remaining 36 entries are excluded from source-labeled Hit@5/MRR until they are labeled. Answerable@Context now normalizes spaces and hyphens for key terms, fixing the voltage false negative where references contain `1.8V` and `3.8V` while the corpus writes `1.8-V` and `3.8-V`; it still checks key-term presence rather than full answer correctness. Some reference answers are also wrong for CC2652R7: the gold set says 256 KB SRAM, but the indexed datasheet says 144 KB; it also contains an 85 deg C temperature expectation while current corpus evidence supports -40 to +105 deg C.

Manual inspection of 12 latest answers found 6 correct, 2 partially correct, 3 incorrect, and 1 unsupported/hallucinated. Correct answers include flash size, SRAM size, voltage range, package, UART count, and Wi-Fi absence. Failures include maximum RF output power (`+0 dBm` instead of `+20 dBm`), standard-mode TX power, RF API questions outside the corpus, and generic hard-fault debugging answers.

## 7. Ablation Study

Two ablation scripts were run for retrieval. Both completed after model access was available locally or via the approved environment.

| Experiment | Retrieval/generation change | Hit@5 | Answerable@Context | Interpretation |
|---|---|---:|---:|---|
| Full pipeline | Hybrid dense+BM25, rerank, anchor injection, extractor-first generation | 1.000 | 0.560 | Current headline run; source-labeled Hit@5=1.000 and MRR@5=0.964 on 14 labels |
| Dense only | FAISS dense retrieval only | 1.000 | Not measured | Inconclusive legacy run; should be rerun with source-labeled metrics |
| No rerank | Hybrid retrieval without cross-encoder reranking | 1.000 | Not measured | Inconclusive legacy run; should be rerun with source-labeled metrics |

The ablation table satisfies the requirement to compare retrieval variants, but it is not yet a strong scientific result. A better next evaluation would extend `must_cite_chunk_ids` beyond the focused subset and compute source-hit/MRR changes for dense-only, BM25-only, hybrid, and reranked retrieval.

## 8. Failure Analysis and Future Work

The main failures are data and evaluation limitations rather than only model mistakes. RF API questions about `RF_open`, `RF_close`, `RFCCpePatchFxp`, `RF_EventLastCmdDone`, and CPE patch order are expected to fail because the RF Driver API Reference is absent. The system often refuses these safely, but the gold set expects facts outside the indexed corpus. Comparison questions also underperform because competitor device facts are absent.

There are also system-level errors. The TX-power extractor/retrieval path selects a nearby current table instead of the maximum-output-power specification. Some debugging answers retrieve generic TRM exception text that is not specific to RF initialization. Unsupported connectivity questions now use the datasheet feature/protocol list for Wi-Fi, LTE/cellular, USB, Ethernet, and Bluetooth Classic absence answers, but broader absence coverage still depends on explicit corpus evidence.

Next improvements are, in priority order: extend source labels beyond the initial datasheet-anchor subset and rerun retrieval ablations with source-labeled metrics; add the RF Driver API Reference; add competitor datasheets or rewrite comparison questions to facts in the corpus; improve TX-power anchoring and extractor ranking; and strengthen strict-format validation for LLM fallback answers.
