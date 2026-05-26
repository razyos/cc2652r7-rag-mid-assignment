# Report Evidence Notes

Session A evidence freeze for the CC2652R7 RAG mid-assignment.

Date: 2026-05-23
Original deadline: 2026-05-26 12:00 noon Asia/Jerusalem
Extension: one week from 2026-05-26. Treat the working deadline as 2026-06-02, exact time TBD; assume noon until clarified.
Critical path: `report.pdf` is complete; the extension should be used for controlled evaluation and answer-quality improvements.

Post-freeze update: Sessions B-D are complete and merged to `main`. Session D fixed the
Answerable@Context hyphen/spacing normalization false negative and was merged to `main`
at commit `48dbd30`. Session E was verified and merged at `ab8b70c`, and handoff docs
were refreshed at `aecde5e`; Session E improves unsupported connectivity answers without changing headline metrics. The latest
eval is Hit@5 = 1.000 and Answerable@Context = 0.560 (28/50). `report.pdf`
remains 2 pages.

## Assignment Requirements To Cover

The final report is limited to 4 pages and must include:

1. corpus description
2. system architecture
3. chunking strategy
4. embedding and vector index choice
5. retrieval method
6. prompt design
7. evaluation results
8. ablation table
9. failure analysis
10. what to improve next

Submission must include code, data manifest, `eval/gold_set.jsonl`, `README.md`, `requirements.txt`, and `report.pdf`.

## Corpus Summary

Corpus: TI CC2652R7 technical documentation, public TI documentation.

Indexed documents:

| Source file | Document role | Current processed chunks |
|---|---:|---:|
| `data/raw/cc2652r7.pdf` | CC2652R7 datasheet | 60 |
| `data/raw/swcu192.pdf` | CC13x2x7/CC26x2x7 Technical Reference Manual | 2237 |
| `data/raw/Users_Guide.html` | SimpleLink SDK User's Guide | 64 |
| Total | 3 documents | 2361 |

Source of truth for chunk counts: `data/processed/chunks.json` as of 2026-05-23 15:52. These counts were aligned across the handoff documents on 2026-05-26.

Other corpus evidence:

- `data/MANIFEST.md` describes about 1100 pages / about 2.5M tokens, PDF x2 plus HTML x1.
- `pdfinfo data/raw/cc2652r7.pdf`: 58 pages.
- `pdfinfo data/raw/swcu192.pdf`: 2193 pages.
- Key chunk: `datasheet_hier_chunk_0000`, the datasheet features list. It contains the highest-value device facts: 48-MHz Arm Cortex-M4F, 704KB flash, 144KB SRAM, Bluetooth 5.2 Low Energy, IEEE 802.15.4, Zigbee/Thread/Matter, 1.8-V to 3.8-V supply, 31 GPIOs, and other feature bullets.
- Critical corpus gap: the TI RF Driver API Reference is not indexed. Symbols such as `RF_open`, `RF_close`, `RFCCpePatchFxp`, `RF_EventLastCmdDone`, and CPE patch details are expected to be missing.
- Competitor-device corpus gap: CC2652R1, CC2652P, CC1352R, and CC2652RB datasheets are not indexed, so most comparison questions require facts outside the corpus.

## Chunking Strategies

Implemented in `src/utils.py`.

| Strategy | Parameters | Behavior | Report use |
|---|---:|---|---|
| Fixed baseline | 512 words, 64-word overlap | Splits every loaded document into overlapping word windows. Ignores page/section structure. | Mention as the required second chunking strategy / baseline. |
| Hierarchical chosen strategy | `max_tokens=600`, `target_tokens=500` words | Keeps PDF pages or HTML sections intact when <=600 words; otherwise sub-splits into 500-word chunks without overlap. Preserves source/page/section metadata. | This is the current indexed strategy. |

Important wording: code uses word counts, even though some planning notes say "tokens".

Chunking helped:

- The datasheet first-page feature list survives as `datasheet_hier_chunk_0000`, which anchors many spec answers: flash, SRAM, voltage, GPIO, UART/SPI/I2C, timers, protocol support, and package.
- HTML loading by h2/h3 keeps SDK-guide sections together instead of arbitrary line chunks.

Chunking/retrieval hurt:

- Some table-heavy datasheet facts are fragmented or retrieved through nearby current tables. Example: "maximum RF output power" currently returns `+0 dBm` from `datasheet_hier_chunk_0012` instead of the expected `+20 dBm`.
- RF Driver API questions cannot be recovered by chunking because the relevant source document is absent.

## Architecture Summary

Current pipeline in `src/rag_system.py`, `src/retrieval.py`, and `src/generation.py`:

1. Dense retrieval with FAISS over normalized `BAAI/bge-large-en-v1.5` embeddings, candidate k=20.
2. BM25 retrieval with `BM25Okapi`, candidate k=20.
3. Hybrid merge by chunk id, using max score for duplicates, top 20.
4. Identifier detection for firmware symbols, hex addresses, register-like names, and all-caps identifiers.
5. Cross-encoder reranking with `cross-encoder/ms-marco-MiniLM-L-6-v2`, plus a +3.0 boost when identifier tokens appear exactly in a chunk.
6. Datasheet anchor injection for spec/support questions: prepend `datasheet_hier_chunk_0000` after reranking, before budgeting.
7. Deduplicate by `chunk_id` and enforce about a 2000-word context budget.
8. Generation: filter table-of-contents chunks, run deterministic extractors first, then fall back to local Ollama `llama3.2` with `temperature=0`, `top_p=0.1`, `num_predict=180`.

Answer interface:

- `RAGSystem.answer(question)` returns `answer`, `sources`, `retrieved_chunks`, `trace`, and `validation`.
- The assignment requires at least `answer`, `sources`, and `retrieved_chunks`; the extra trace fields are useful diagnostics.

Prompt/generation design:

- Required answer format: `QUOTE`, `ANSWER`, `SOURCE`, or a strict not-found answer.
- Prompt rules prohibit outside knowledge, unsupported symbols, Wi-Fi/Wi-SUN conflation, and guesses.
- Deterministic generation currently handles memory, protocols, unsupported connectivity, CPU, clock, voltage, package, temperature, RF core, BLE sensitivity, GPIO, ADC, serial interfaces, timers, TX power, and RF command chaining.
- Validation checks technical literals in answers against retrieved chunks.

## Current Evaluation Metrics

Source: `eval/eval_results.json` after Session E was merged to `main` on 2026-05-26.

| Metric | Value | Count | Notes |
|---|---:|---:|---|
| Gold-set size | 50 | 50 | 10 questions each across factual, numerical, negation, comparison, debugging. |
| k | 5 | - | Eval output uses `k=5`. |
| Hit@5 | 1.000 | 50/50 | Caveat: every gold entry currently has empty `must_cite_chunk_ids`, so this metric is vacuous. |
| Answerable@Context | 0.560 | 28/50 | Checks whether reference key technical terms appear in final retrieved context. This is not answer accuracy. |

Metric caveats to state honestly in the report:

- `eval/gold_set.jsonl` has 0/50 non-empty `must_cite_chunk_ids`. Therefore Hit@5=1.000 only proves the eval harness ran; it does not prove the retriever found a labeled relevant chunk.
- Answerable@Context now normalizes spaces and hyphens for key-term matching. This fixed the voltage case where the answer/reference contains `1.8V` and `3.8V`, while the corpus writes `1.8-V` and `3.8-V`.
- Answerable@Context can also be misleading when the gold answer is wrong or outside the indexed corpus.
- Known gold-set problems: SRAM reference says 256 KB but CC2652R7 datasheet chunk says 144 KB; temperature reference says +85 deg C but current project evidence says operating ambient is -40 to +105 deg C.

## Per-Category Results

Source: `eval/eval_results.json`.

| Category | N | Hit@5 | Answerable@Context | Count | Main note |
|---|---:|---:|---:|---:|---|
| numerical | 10 | 1.000 | 0.900 | 9/10 | Strongest category; one TX-power-standard-mode miss. |
| factual | 10 | 1.000 | 0.700 | 7/10 | Voltage normalization fixed; remaining misses include RF API corpus gap, max TX-power error, and gold issues. |
| negation | 10 | 1.000 | 0.600 | 6/10 | Unsupported connectivity answers are now grounded in `datasheet_hier_chunk_0000`; Answerable still misses LTE/USB/5V/RF_open terms. |
| debugging | 10 | 1.000 | 0.400 | 4/10 | RF Driver API gap dominates; some generic TRM answers are not question-specific. |
| comparison | 10 | 1.000 | 0.200 | 2/10 | Most require competitor-device facts not indexed. |

## Ablation Results Or Commands

Commands run during this evidence-freeze session:

```bash
python eval/run_eval_dense_only.py 5
python eval/run_eval_no_rerank.py 5
```

The first sandboxed attempt failed because `SentenceTransformer` tried to resolve `BAAI/bge-large-en-v1.5` from Hugging Face and DNS/network access was blocked. After network escalation, both ablation scripts completed.

| Experiment | Command | Reported metric | Result | Interpretation |
|---|---|---:|---:|---|
| Full current pipeline | `python eval/run_eval.py` / existing `eval/eval_results.json` | Hit@5 / Answerable@Context | 1.000 / 0.560 | Current headline numbers, but Hit@5 is vacuous because cite labels are empty. |
| Dense-only retrieval | `python eval/run_eval_dense_only.py 5` | Hit@5 | 1.000 | Inconclusive for the same empty-cite-label reason. |
| Hybrid without rerank | `python eval/run_eval_no_rerank.py 5` | Hit@5 | 1.000 | Inconclusive for the same empty-cite-label reason. |

How to present this in the 4-page report:

- Include the ablation table because the assignment requires ablations.
- Label the current ablation as retrieval-hit ablation, not answer-quality ablation.
- Add a caveat sentence: "Because the current gold set does not yet contain labeled required chunks, the ablation hit rates are not discriminative; the more informative current metric is Answerable@Context plus manual inspection."

If time remains after `report.pdf`, the smallest eval-quality improvement is to fill `must_cite_chunk_ids` for a focused subset or add a separate exact-source retrieval metric. Do not do this before the report unless the report is already safe.

Extension update: this is now the highest-value next improvement. The comparison `insurance-rag` repo used an anchor/MRR-style retrieval evaluation; borrow the concept, not the code.

## 10+ Answer Manual Inspection

Labels use the assignment categories: Correct, Partially correct, Incorrect, Unsupported/Hallucinated.

| # | Category | Question | Latest system answer gist | Label | Evidence / note |
|---:|---|---|---|---|---|
| 1 | numerical | What is the flash memory size? | 704 KB flash from `datasheet_hier_chunk_0000` | Correct | Direct feature-list quote. |
| 2 | numerical | What is the SRAM size? | 144 KB SRAM from `datasheet_hier_chunk_0000` | Correct | Gold says 256 KB, but corpus/project evidence says 144 KB for CC2652R7. |
| 3 | factual | Operating voltage range? | 1.8 V to 3.8 V from `datasheet_hier_chunk_0000` | Correct | Metric false negative due `1.8-V`/`3.8-V` hyphens in corpus. |
| 4 | factual | Package? | 7 mm x 7 mm 48-pin VQFN package (RGZ) | Correct | Direct quote from `datasheet_hier_chunk_0000`. |
| 5 | numerical | How many UART interfaces? | 2 UART interfaces | Correct | Direct quote: "Two UART, two SSI, I2C, I2S". |
| 6 | factual | Maximum RF output power? | Answers `+0 dBm` from transmit-current table | Incorrect | Expected gold/reference is `+20 dBm`; extractor/retrieval selected wrong table cell. |
| 7 | numerical | RF transmit power in standard mode without PA? | Says not directly stated, then adds unsupported detail about TX20 PA bias bits | Partially correct | "Not directly stated" is defensible; extra explanation is not in required cited format and does not answer `+5 dBm` reference. |
| 8 | negation | Does CC2652R7 support Wi-Fi? | No, support list does not include Wi-Fi | Correct | Current answer is a grounded absence answer from CC2652R7 support list. |
| 9 | negation | Is CC2652R7 compatible with 5V logic directly? | `ANSWER: No` | Partially correct | Correct direction, but no quote/source and no voltage range in answer. |
| 10 | negation/factual | Can `RF_open()` be called without CPE patch / what before `RF_open()`? | Not found | Incorrect | Safe refusal, but gold answer requires RF Driver API facts absent from corpus. Treat as corpus-coverage failure, not hallucination. |
| 11 | debugging | What causes a hard fault during RF driver initialization? | Generic hard-fault quote only | Unsupported/Hallucinated | Retrieved generic exception text, not RF-driver-specific cause. |
| 12 | debugging | Symptom of incorrect VDDR trim? | Quotes VDDR recharge detector status | Incorrect | The answer is about a status bit, not RF output/range symptom in reference. |

Manual-inspection takeaway:

- Deterministic extractors make basic device-spec answers strong.
- The system is generally conservative for absent RF API facts, but those questions are still failures against the gold set.
- The biggest answer-quality failures are table-cell selection for TX power, generic TRM debugging answers, and unsupported/uncited fallback text.

## Failure Analysis Examples

Use these in the report.

1. Corpus gap: RF Driver API

- Questions: `RF_open()`, `RFCCpePatchFxp()`, `RF_EventLastCmdDone`, `RF_close()`, CPE patch order.
- Cause: the RF Driver API Reference PDF is not in `data/raw/` and not indexed.
- Symptom: current answers often say "not found". This is grounded behavior, but the gold set expects facts outside the indexed corpus.
- Improvement: add the RF Driver API Reference after the report is safe, rebuild indexes, rerun eval.

2. Corpus gap: competitor device comparisons

- Questions comparing CC2652R7 to CC2652R1, CC2652P, CC1352R, and CC2652RB.
- Cause: only CC2652R7/TRM/SDK guide documents are indexed.
- Symptom: comparison category Answerable@Context is 0.200.
- Improvement: either add competitor datasheets or rewrite comparison questions to compare facts present in the corpus.

3. Metric gap: empty retrieval labels

- `eval/gold_set.jsonl` has 50 entries and 0 non-empty `must_cite_chunk_ids`.
- Cause: retrieval metric treats entries without required chunk ids as automatic hit.
- Symptom: full, dense-only, and no-rerank all report Hit@5=1.000.
- Improvement: label required chunk ids for at least the core gold questions.

4. Metric bug: hyphen/unit normalization

- Status: fixed in Session D and merged to `main` at commit `48dbd30`.
- Example: voltage answer is correct, and Answerable@Context now matches reference `1.8V`/`3.8V` against context `1.8-V`/`3.8-V`.

5. Gold-set mistakes

- SRAM: gold says 256 KB; current indexed datasheet says 144 KB for CC2652R7.
- Temperature: gold says +85 deg C; project evidence says operating ambient is up to +105 deg C.
- These should be discussed as evaluation limitations, not system bugs.

6. Extractor/retrieval error: max RF output power

- Question: "What is the maximum RF output power of the CC2652R7?"
- Current answer: `+0 dBm`.
- Expected: `+20 dBm`.
- Cause: selected a transmit-current table cell instead of the maximum-output-power feature/spec.
- Improvement: add "rf output power", "tx power", and "transmit power" to anchor injection terms and/or strengthen TX-power extractor ranking. Do this only after report safety.

7. Fallback answer quality

- Example: standard-mode TX power answer includes an uncited explanation and "However", which the prompt says to avoid.
- Example: hard-fault debugging answer quotes generic exception text.
- Improvement: add refusal/extractor logic for unsupported debugging questions or enforce strict format validation on LLM fallback.

## Future Improvement Priorities

Report-first priority order:

1. Keep `main` frozen as the stable submission branch unless a branch passes verification.
2. Continue `feature/source-label-eval`; fill `must_cite_chunk_ids` for a defensible subset or add anchor-style matching so Hit@5 becomes meaningful, preferably with MRR.
3. Next small answer-quality branch: `feature/tx-power-extractor`.
4. Run a final submission audit after any merge.
5. Larger branches: `exp/rf-driver-api-corpus` and `exp/competitor-datasheets`; rebuild indexes and rerun eval before considering merge.

Do not merge RF Driver API corpus expansion, competitor corpus expansion, gold-set rewrites, or broad refactors into `main` before a full eval/report/PDF audit passes.

## Report Recommendation

`report.md` and `report.pdf` are complete and submission-safe. Session E refreshed both
after the unsupported-connectivity branch change, and `pdfinfo report.pdf` still reports
2 pages. The next session should focus on source-label evaluation, not risky corpus work.
