# CC2652R7 RAG System Design Notes

Internal engineering notes for explaining the system beyond the 4-page report.

Date: 2026-05-26
Current branch context: `feature/source-label-eval`
Primary goal: make the design understandable, defensible, and easy to improve without
treating the current implementation as the only possible RAG architecture.

## 1. Executive Summary

This project is a local, assignment-scoped RAG system for Texas Instruments CC2652R7
documentation. It is designed to answer firmware, hardware-specification, absence, and
debugging questions with citations from a small official corpus.

The current architecture is deliberately manual:

1. Load and chunk the corpus.
2. Build a dense FAISS index and a BM25 keyword index.
3. Retrieve with dense search and BM25.
4. Merge candidates.
5. Rerank with a cross-encoder and identifier boost.
6. Inject the datasheet feature-list anchor for spec/support questions.
7. Generate with deterministic extractors first, then local Llama fallback.
8. Validate answer grounding and evaluate the run.

This is a strong architecture for the assignment because it is transparent, local,
reproducible, and focused on embedded-documentation failure modes: exact symbols,
numeric specs, protocol names, and unsupported-feature questions.

It is not a full production RAG platform. Production systems usually add source-label
evaluation, observability, user feedback, metadata access control, update pipelines,
caching, monitoring, and sometimes managed vector databases, graph retrieval, late
interaction models, or agentic query planning. The current system has several
production-like choices, but its infrastructure is intentionally simple.

## 2. System Goal and Problem Shape

The system exists because general LLMs are weak on exact device documentation:

- They confuse nearby TI device variants.
- They often hallucinate support for common interfaces such as Wi-Fi, USB, Ethernet,
  or cellular.
- They miss exact firmware symbols unless those symbols are retrieved literally.
- They can select a nearby table cell instead of the relevant spec.
- They answer out-of-corpus RF Driver API questions even when the indexed corpus does
  not contain the API reference.

The system therefore prioritizes:

- Grounded answers over fluent answers.
- Exact citations over broad summaries.
- Refusal when evidence is missing.
- Local reproducibility over hosted-model quality.
- Narrow controlled improvements over risky corpus/index rewrites close to submission.

## 3. Corpus Design

Current indexed corpus:

| Source | Role | Processed chunks |
|---|---:|---:|
| `data/raw/cc2652r7.pdf` | CC2652R7 datasheet | 60 |
| `data/raw/swcu192.pdf` | CC13x2x7/CC26x2x7 TRM | 2237 |
| `data/raw/Users_Guide.html` | SimpleLink SDK User's Guide | 64 |
| Total | 3 documents | 2361 |

Why this corpus:

- It is official TI documentation.
- It is small enough to run locally.
- It covers device specs, TRM details, and SDK guide context.
- It is sufficient for many factual/numerical CC2652R7 questions.

Most important chunk:

- `datasheet_hier_chunk_0000`
- Contains first-page feature/protocol facts:
  - 48-MHz Arm Cortex-M4F
  - 704 KB flash
  - 144 KB SRAM
  - Bluetooth 5.2 Low Energy
  - IEEE 802.15.4 / Zigbee / Thread / Matter support
  - 1.8-V to 3.8-V supply
  - 31 GPIOs
  - serial interfaces and general device features

Known corpus gaps:

- TI RF Driver API Reference is not indexed.
- Competitor datasheets are not indexed.
- Some table-heavy datasheet facts are hard to retrieve/extract correctly.

Why not expand the corpus immediately:

- Corpus expansion changes chunk counts, indexes, metrics, and report claims.
- RF Driver API and competitor datasheets would improve some gold-set failures, but
  they are major scope changes.
- The branch policy keeps this kind of work in experimental branches such as
  `exp/rf-driver-api-corpus` or `exp/competitor-datasheets`.

Industry alignment:

- Using official source documents and preserving metadata is aligned with production
  RAG practice.
- Treating missing documents as a corpus coverage problem, not only a retrieval bug,
  is also industry-realistic.
- What is missing for production is document versioning, ingestion provenance,
  permissioning, change detection, and automated reindexing.

## 4. Loading and Chunking

Implemented in `src/utils.py`.

Document loading:

- PDFs are loaded page-by-page with `pypdf`.
- HTML is loaded with BeautifulSoup and grouped by `h2`/`h3` sections.
- Metadata stores source filename and page or section.

Implemented chunking strategies:

| Strategy | Behavior | Strength | Weakness |
|---|---|---|---|
| Fixed | 512 words with 64-word overlap | Simple baseline, reproducible | Ignores document structure |
| Hierarchical | Keep page/section if <= 600 words; otherwise split into 500-word chunks | Preserves natural document units | Still imperfect for tables |

Why hierarchical is used:

- Datasheet feature pages and SDK sections usually form coherent retrieval units.
- The first datasheet feature list remains a compact authoritative chunk.
- HTML headings produce more meaningful boundaries than arbitrary windows.

Alternatives:

- Smaller chunks: improve pinpoint retrieval but lose context and increase index size.
- Larger chunks: preserve tables/sections but can waste context budget.
- Semantic chunking: split by embedding similarity or sentence boundaries; useful when
  documents have poor structure, but can be less reproducible and harder to explain.
- Parent-child chunking: retrieve small child chunks, then expand to larger parent
  sections; often useful in production, but adds more metadata and code.
- Table-aware extraction: parse tables into structured rows; likely the best fix for
  TX-power/table errors, but outside the current narrow branch.

Design judgment:

- Hierarchical chunking is the right current compromise for an assignment RAG system.
- If this were production firmware documentation search, table-aware ingestion and
  parent-child retrieval would be the first chunking upgrades.

## 5. Embeddings and Dense Indexing

Current implementation:

- Embedding model: `BAAI/bge-large-en-v1.5`
- Index: FAISS `IndexFlatIP`
- Embeddings are normalized, so inner product behaves like cosine similarity.
- Index artifacts live under `data/processed`.

Why FAISS is used:

- It is a mature vector similarity library.
- It supports exact and approximate search variants.
- It is local, fast, simple, and does not require a database server.
- The corpus is small enough that exact `IndexFlatIP` is acceptable.
- It matches the assignment's local/reproducible constraints.

Why not Chroma for this project:

- The corpus is static and single-tenant.
- There is no need for persistent collection APIs, document update workflows, or rich
  metadata filtering in the current assignment.
- The project already keeps chunk metadata in JSON and combines FAISS with BM25.
- Switching to Chroma would add operational surface without addressing the biggest
  current weaknesses: unlabeled eval, missing RF API corpus, competitor corpus gaps,
  and TX-power extraction.

Better options depending on future requirements:

| Option | Best when | Tradeoff |
|---|---|---|
| FAISS | Local, small/medium static corpus, custom pipeline | No built-in document DB, metadata filtering, or service API |
| Chroma | Simple app-level vector DB, metadata filtering, quick prototyping | Less control than raw FAISS; still another dependency/service mode |
| Qdrant | Production vector DB, filters, payloads, hybrid and multi-stage search | More infrastructure than needed for this repo |
| Weaviate | Integrated vector + BM25 hybrid search, managed/cloud options | More platform behavior to learn and configure |
| Milvus | Large-scale vector platform, distributed deployment, BM25/sparse support | Operationally heavier |
| Elasticsearch/OpenSearch | Strong keyword search plus vector and hybrid retrieval | More infrastructure; vector quality depends on configuration |
| pgvector | App already uses Postgres, needs joins/transactions with vectors | Not as specialized as vector-native systems for large ANN workloads |

Advanced embedding/retrieval options:

- Dense-only embeddings are no longer enough for many technical RAG workloads.
- Sparse+dense embeddings can combine semantic matching with exact term matching.
- Multi-vector or late-interaction retrieval, such as ColBERT-style systems, can
  improve relevance by comparing token-level representations instead of one vector per
  chunk.
- BGE-M3-style models are relevant because they support dense, sparse, and multi-vector
  retrieval modes in one model family.

Design judgment:

- FAISS is not "the best vector database." It is the best fit for this assignment's
  static local corpus and transparent code.
- If the project became a product, the next index decision would depend on data size,
  update frequency, metadata/security needs, latency target, and deployment budget.
- For this repo, source-label evaluation should happen before replacing the vector
  backend. Without better eval, a backend migration would be mostly guesswork.

## 6. BM25 and Hybrid Retrieval

Current implementation:

- `rank_bm25.BM25Okapi` builds a lexical index over chunk text.
- Dense retrieval returns semantic candidates.
- BM25 returns exact-token candidates.
- `hybrid_retrieve()` merges both lists by `chunk_id` and keeps the max score.

Why BM25 is necessary:

- Firmware questions contain exact symbols: `RF_open`, `RFCCpePatchFxp`,
  `RF_EventLastCmdDone`.
- Dense embeddings may blur symbol identity.
- Numeric and unit strings often need lexical matching.
- BM25 is transparent and useful as a fallback when semantic retrieval misses exact
  terminology.

Current weakness:

- The merge uses max score across dense and BM25 scores even though these scores are
  not calibrated to the same scale.
- This is acceptable for a small assignment pipeline because a cross-encoder reranks
  the merged candidates afterward.
- For a production system, reciprocal rank fusion (RRF) or learned fusion would be
  more principled.

Industry alignment:

- Hybrid retrieval is common in modern RAG systems because vector search and keyword
  search fail differently.
- Managed systems such as Weaviate, Qdrant, and Milvus expose hybrid retrieval patterns
  directly.

Alternatives:

- Dense-only: simpler but worse for symbols, IDs, and exact specs.
- BM25-only: strong for exact terms but weak for paraphrase.
- Sparse neural retrieval: SPLADE-like or BGE-M3 sparse representations can improve
  lexical-semantic matching.
- RRF fusion: often a better first production choice than score maxing.
- Query routing: choose dense, lexical, hybrid, or graph retrieval based on query type.

Design judgment:

- The current dense+BM25 hybrid path is directionally correct.
- The biggest improvement is not a new backend; it is better labeled evaluation so
  fusion changes can be measured.

## 7. Identifier-Aware Reranking

Current implementation:

- The cross-encoder is `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Candidate pairs are scored as `(query, chunk_text)`.
- Identifier-looking tokens receive an exact-match boost of `+3.0`.

Why reranking exists:

- First-stage retrieval should be broad and cheap.
- Reranking can use a stronger query-document relevance model over a smaller candidate
  set.
- The candidate set includes both dense and BM25 results, so reranking arbitrates
  between semantic and lexical evidence.

Why identifier boost exists:

- In embedded documentation, `RF_open` and `RF_close` are not interchangeable.
- Cross-encoders trained on web search may not fully respect firmware-symbol identity.
- Exact symbol presence is strong evidence for technical questions.

Alternatives:

- Larger cross-encoder reranker: better quality, slower.
- Domain-tuned reranker: best if labeled firmware relevance data exists.
- Hard pinning identifier chunks: higher recall for symbols, but can over-rank irrelevant
  symbol mentions.
- Late interaction retrieval: more expensive indexing but often stronger ranking.
- LLM reranking: flexible but slower and less reproducible locally.

Industry alignment:

- Two-stage retrieval with reranking is a common production pattern.
- Exact-match boosting is a pragmatic domain adaptation for code, firmware, legal, and
  medical corpora where exact terms matter.

## 8. Datasheet Anchor Injection

Current implementation:

- Stage 5b in `src/rag_system.py`.
- For spec/support questions, prepend `datasheet_hier_chunk_0000` after reranking.
- Recent Session E work added unsupported connectivity terms such as Wi-Fi, USB,
  LTE/cellular, Ethernet, Bluetooth Classic, BR/EDR, and Wi-SUN.

Why this exists:

- The datasheet feature list is the authoritative source for many device capabilities.
- Cross-encoder reranking can demote broad feature-list chunks when a query names a
  specific interface.
- Prepending after rerank ensures the feature list survives context budgeting.

Why after reranking:

- Injecting before rerank can cause a broad anchor to compete poorly against specific
  peripheral sections.
- Injecting after rerank makes it a controlled domain rule rather than a model-scored
  candidate.

Alternatives:

- Metadata-aware retrieval: tag feature-list chunks as high-priority device overview
  facts.
- Query classifier/router: detect "device spec", "unsupported feature", "RF API", or
  "debugging" and choose context strategy.
- Parent-child expansion: retrieve a specific child, then include its parent overview.
- Structured facts table: extract device capabilities into a small curated data source.

Industry alignment:

- This is a hand-built version of domain-aware retrieval policy.
- In production, this might become a router, metadata prior, or structured knowledge
  base lookup.

Design judgment:

- The anchor injection is justified because the corpus has one unusually important
  feature-list chunk.
- It should stay narrow. If many anchors are added, it becomes an implicit rules engine
  and should be refactored into an explicit query policy layer.

## 9. Context Budgeting and Deduplication

Current implementation:

- Deduplicate by `chunk_id`.
- Keep chunks until about a 2000-word budget is reached.
- Generation reranks/deduplicates again with a smaller budget before LLM fallback.

Why it exists:

- Local Llama 3.2 has limited useful context and can degrade with irrelevant text.
- Duplicate chunks waste context.
- Technical answers often need only one or two exact snippets.

Alternatives:

- Tokenizer-accurate budgeting instead of word count.
- Dynamic budget by query type.
- Context compression/summarization.
- Parent-child context expansion.
- Citation-aware context packing.

Design judgment:

- Word-count budgeting is acceptable for this assignment.
- If the project grows, switch to tokenizer-aware budgeting and add explicit source
  diversity constraints.

## 10. Generation Design

Current implementation:

- `generate_answer()` filters table-of-contents chunks.
- Deterministic extractors run before the LLM.
- If no extractor applies, local Ollama `llama3.2` is called.
- Prompt output must be either:

```text
QUOTE: ...
ANSWER: ...
SOURCE: chunk_id
```

or:

```text
ANSWER: The information was not found in the provided documentation.
```

Why extractor-first:

- Many questions ask for exact specs: flash, SRAM, voltage, GPIO count, package, protocol
  support, serial interfaces, timers.
- Regex/rule extraction is more reliable than a small local LLM for these facts.
- It reduces hallucinations and makes behavior testable.
- It allows precise refusal for unsupported features.

Why still use an LLM fallback:

- Some questions are not covered by deterministic extractors.
- Debugging and explanation questions may need synthesis from retrieved context.
- The assignment expects a RAG system, not only a lookup table.

Prompt design:

- Use only retrieved context.
- Do not add outside knowledge.
- Do not conflate Wi-Fi and Wi-SUN.
- Answer yes only when exact support is stated.
- For symbols/API questions, require exact symbol evidence.
- Avoid "however", guesses, and unrelated summaries.

Validation:

- `validate_answer()` extracts technical literals from the answer and checks whether
  they appear in retrieved chunks.
- This catches some ungrounded numbers, units, symbols, and device identifiers.
- It is not a full factuality checker.

Alternatives:

- Pure LLM generation: simpler, but worse for exact specs and unsupported features.
- Tool/function calling: make extractors explicit callable tools.
- Structured output schema: parse JSON with quote, answer, source, confidence.
- Constrained decoding: enforce output format more strictly.
- Larger hosted LLM: better reasoning, but violates current local-only project constraint.
- Fine-tuned local model: possible but unjustified for this small corpus.

Industry alignment:

- Extractor-first generation is a common engineering pattern for high-risk facts.
- Strict citation/refusal instructions are aligned with grounded RAG practice.
- Production systems would add stronger output parsing, retry logic, and observability.

## 11. Evaluation Design

Current evaluation:

- 50 gold questions across factual, numerical, negation, comparison, and debugging.
- `Hit@5` is computed from `must_cite_chunk_ids`.
- `Answerable@Context` checks whether key technical terms from the reference answer
  appear in final retrieved context.
- `feature/source-label-eval` adds a focused 14-question source-labeled subset and
  reports source-labeled Hit@5/MRR separately from legacy Hit@5.

Current metrics:

| Metric | Value | Caveat |
|---|---:|---|
| Legacy Hit@5 | 1.000 | Kept for continuity; unlabeled entries still count as hits |
| Source-labeled Hit@5 | 1.000 | Computed over 14 labeled datasheet-anchor entries |
| Source-labeled MRR@5 | 0.964 | Rank-sensitive source metric over the same 14 entries |
| Answerable@Context | 0.560 | Checks context term presence, not answer correctness |

Why this is not enough:

- Incomplete source labels still make legacy Hit@5 non-discriminative for 36 unlabeled rows.
- Answerable@Context can pass when the answer is wrong but key terms are present.
- Answerable@Context can fail when the reference answer is wrong or the source formats
  terms differently.
- It does not measure citation correctness, faithfulness, or answer usefulness.

Best next improvement:

- Expand source labels beyond the first datasheet-anchor subset.
- Rerun dense-only, BM25-only, hybrid, and reranked retrieval with source-labeled metrics.
- Keep MRR so rank quality matters.
- Keep Answerable@Context for continuity, but stop treating it as answer accuracy.

Production-style evaluation would include:

- Retrieval: Hit@k, Recall@k, MRR, nDCG on labeled relevant chunks.
- Context quality: context precision and context recall.
- Generation: exact-match for structured facts, factual correctness, citation accuracy,
  faithfulness/groundedness, refusal correctness.
- Regression tests: fixed questions for known failures.
- Human review: small set of manually labeled answers.

Industry alignment:

- The current evaluation harness is useful but incomplete.
- RAG evaluation tools commonly separate retrieval quality, context quality, and answer
  faithfulness. This project should move in that direction with `feature/source-label-eval`.

## 12. Industry Alignment: What Is Standard and What Is Not

There is no single universal industry standard RAG architecture. The common pattern is:

1. Ingest trusted documents with metadata.
2. Chunk them with a reproducible strategy.
3. Index dense embeddings, lexical representations, or both.
4. Retrieve a broad candidate set.
5. Rerank or fuse results.
6. Pack context with citations.
7. Generate using a grounded prompt or structured tool path.
8. Evaluate retrieval and generation separately.
9. Monitor failures and improve with feedback.

This project matches several production-like patterns:

- Official corpus with metadata.
- Hybrid dense + lexical retrieval.
- Cross-encoder reranking.
- Domain-specific identifier handling.
- Deterministic extractors for exact facts.
- Strict citation/refusal prompt.
- Validation for technical literals.
- Branch policy for risky corpus changes.

This project is not production-grade in these areas:

- Source-label retrieval evaluation exists for a focused subset, but it is not complete.
- No continuous evaluation in CI.
- No retrieval observability dashboard.
- No user feedback loop.
- No access control, multi-tenancy, or document versioning.
- No incremental indexing.
- No tokenizer-accurate context budget.
- No structured table extraction.
- No managed serving layer.

Conclusion:

- The design is appropriate and defensible for the assignment.
- It is closer to a transparent research/education RAG pipeline than a deployed product.
- The next serious step is better evaluation, not a fashionable vector database switch.

## 13. Alternatives and When They Would Be Better

### LangChain or LlamaIndex

Would help if:

- The goal were quick integration with many loaders, vector stores, and agent tools.
- The project needed a standard orchestration layer.

Why not now:

- The current manual code is easier to explain in the report.
- Frameworks can hide retrieval behavior.
- Assignment grading benefits from transparent implementation.

### Chroma

Would help if:

- We needed a lightweight vector DB with collection management.
- Metadata filtering or persistent app-level retrieval APIs became important.

Why not now:

- No multi-tenant filtering is needed.
- FAISS already solves local dense search.
- BM25 is already implemented separately.

### Qdrant, Weaviate, or Milvus

Would help if:

- The corpus were dynamic or much larger.
- We needed service deployment, filtering, payload metadata, hybrid search APIs, or
  sparse/dense/multi-vector retrieval in the database layer.

Why not now:

- More infrastructure would not fix the current evaluation weakness.
- Operational complexity is not justified for 2361 chunks.

### Elasticsearch or OpenSearch

Would help if:

- Keyword search, analyzers, filters, logs, and operational search tooling were primary.
- Dense vector search needed to live alongside strong lexical search.

Why not now:

- Heavy for a local assignment.
- The current BM25 + FAISS path is simpler and transparent.

### pgvector

Would help if:

- The app already used Postgres.
- Vector search needed joins, transactions, backups, or relational metadata.

Why not now:

- This project has no database application layer.
- JSON chunk metadata is enough.

### ColBERT or Other Late-Interaction Retrieval

Would help if:

- Ranking quality became the main bottleneck.
- The corpus had many similar chunks where single-vector embeddings lose token-level
  detail.

Why not now:

- More index complexity.
- Higher storage and compute cost.
- Needs better eval labels before migration is justified.

### BGE-M3-Style Dense + Sparse + Multi-Vector Retrieval

Would help if:

- We wanted one model family to support dense, sparse, and multi-vector retrieval.
- We wanted a more modern retrieval stack than separate BGE dense embeddings plus BM25.

Why not now:

- Requires index changes and eval work.
- Current assignment is already close to submission-safe.

### GraphRAG

Would help if:

- Questions required connecting facts across many documents/entities.
- The corpus had rich relationships and high-level synthesis tasks.

Why not now:

- Most CC2652R7 questions are single-hop exact fact or absence questions.
- Graph extraction would be overkill before source-label eval and missing-corpus work.

### Hosted LLMs and Hosted Embeddings

Would help if:

- The goal were maximum answer quality rather than local reproducibility.
- Latency/cost/privacy constraints allowed external APIs.

Why not now:

- The project constraint is local inference only.
- Hosted APIs would change the assignment story.

## 14. Current Known Weaknesses

1. Legacy Hit@5 is not meaningful for unlabeled rows; source-labeled metrics currently cover 14/50 entries.
2. RF Driver API questions are out of corpus.
3. Competitor comparison questions are mostly out of corpus.
4. TX-power extraction selects the wrong table evidence in at least one case.
5. Some gold answers appear inconsistent with the indexed CC2652R7 datasheet.
6. Full test suite can stall on model-heavy paths.
7. The LLM fallback can still produce generic or weak debugging answers.
8. Context budgeting is word-based, not tokenizer-based.
9. Score fusion is simple max-score merging, not calibrated fusion.
10. Table parsing is not structured.

## 15. Recommended Improvement Roadmap

Priority 1: source-label evaluation.

- Branch: `feature/source-label-eval`.
- First subset is implemented with 14 `datasheet_hier_chunk_0000` labels.
- Next step is expanding labels and rerunning ablations with source-labeled Hit@k/MRR.
- Keep report claims explicit about labeled subset size.

Priority 2: TX-power extractor.

- Branch: `feature/tx-power-extractor`.
- Fix maximum RF output power and standard-mode TX-power behavior.
- Prefer table-aware evidence if it can be done narrowly.

Priority 3: RF Driver API corpus expansion.

- Branch: `exp/rf-driver-api-corpus`.
- Add exact RF Driver API source only with user approval.
- Rebuild indexes, rerun eval, update report and PDF.

Priority 4: broader retrieval modernization.

- Only after source-label eval exists.
- Compare current FAISS+BM25 against at least one modern alternative:
  - RRF fusion
  - BGE-M3 sparse+dense
  - Qdrant hybrid
  - Weaviate hybrid
  - pgvector if a relational app layer appears
  - ColBERT-style reranking/retrieval for hard cases

## 16. Design Principles to Preserve

- Do not optimize metrics that are not meaningful.
- Do not call a corpus gap a generation bug.
- Prefer exact evidence for technical claims.
- Prefer refusal over unsupported guesses.
- Keep main submission-safe.
- Add tests before changing answer behavior.
- Keep broad architecture changes on focused branches.
- Update report artifacts whenever metrics or claims change.

## 17. External References Consulted

These are not required reading for running the project. They explain the broader design
space and why the current choices are reasonable for this assignment but not the only
valid choices for modern RAG.

- FAISS project: https://github.com/facebookresearch/faiss
- FAISS paper: https://arxiv.org/abs/2401.08281
- Chroma docs: https://docs.trychroma.com/docs/overview/introduction
- Qdrant hybrid queries: https://qdrant.tech/documentation/concepts/hybrid-queries/
- Weaviate hybrid search: https://docs.weaviate.io/weaviate/search/hybrid
- Milvus full-text/BM25 search: https://milvus.io/docs/full-text-search.md
- pgvector project: https://github.com/pgvector/pgvector
- ColBERTv2 paper: https://arxiv.org/abs/2112.01488
- BGE-M3 / M3-Embedding paper: https://arxiv.org/abs/2402.03216
- Microsoft GraphRAG docs: https://microsoft.github.io/graphrag/
- Ragas evaluation metrics: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
