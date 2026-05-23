# src/retrieval.py
import re
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
import faiss
from rank_bm25 import BM25Okapi


# ---------------------------------------------------------------------------
# Task 9: Dense, BM25, and Hybrid Retrieval
# ---------------------------------------------------------------------------

def retrieve_dense(query: str, index: faiss.Index, chunks: list[dict],
                   model: SentenceTransformer, k: int = 20) -> list[dict]:
    """Dense retrieval using FAISS inner product search."""
    query_emb = model.encode([query], normalize_embeddings=True)
    query_emb = np.array(query_emb, dtype="float32")
    scores, indices = index.search(query_emb, k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        result = dict(chunks[idx])
        result["score"] = float(score)
        results.append(result)
    return results


def retrieve_bm25(query: str, bm25: BM25Okapi, chunks: list[dict], k: int = 20) -> list[dict]:
    """BM25 keyword retrieval."""
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    top_indices = np.argsort(scores)[::-1][:k]
    results = []
    for idx in top_indices:
        if scores[idx] == 0:
            continue
        result = dict(chunks[idx])
        result["score"] = float(scores[idx])
        results.append(result)
    return results


def hybrid_retrieve(query: str, index: faiss.Index, chunks: list[dict],
                    model: SentenceTransformer, bm25: BM25Okapi, k: int = 20) -> list[dict]:
    """Merge dense and BM25 results, deduplicate by chunk_id."""
    dense_results = retrieve_dense(query, index, chunks, model, k=k)
    bm25_results = retrieve_bm25(query, bm25, chunks, k=k)

    seen = {}
    for result in dense_results + bm25_results:
        cid = result["chunk_id"]
        if cid not in seen:
            seen[cid] = result
        else:
            seen[cid]["score"] = max(seen[cid]["score"], result["score"])

    merged = list(seen.values())
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:k]


# ---------------------------------------------------------------------------
# Task 10: Identifier-Aware Reranker
# ---------------------------------------------------------------------------

_cross_encoder = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def is_identifier_token(token: str) -> bool:
    """Returns True if token looks like a firmware symbol, register name, hex address, or error code."""
    if re.match(r'^0x[0-9a-fA-F]+$', token):
        return True
    if re.match(r'^[A-Z]{2,}[a-zA-Z0-9_]+$', token):
        return True
    if re.match(r'^[A-Z][A-Z0-9_]+[A-Z0-9]$', token):
        return True
    if '_' in token and token.replace('_', '').isupper() and len(token) > 3:
        return True
    return False


def rerank(query: str, candidates: list[dict], k: int = 5) -> list[dict]:
    """
    Identifier-aware reranking using weighted boost (not hard pin).
    Chunks containing exact identifier token matches receive a +3.0 score bonus
    before ranking. This keeps the cross-encoder as the primary signal while
    ensuring firmware symbols, register names, and hex addresses are not silently
    demoted.
    """
    if not candidates:
        return []

    IDENTIFIER_BOOST = 3.0

    query_tokens = query.split()
    identifier_tokens = [t for t in query_tokens if is_identifier_token(t)]

    ce = _get_cross_encoder()
    pairs = [(query, c["text"]) for c in candidates]
    ce_scores = ce.predict(pairs)

    scored = []
    for chunk, ce_score in zip(candidates, ce_scores):
        chunk_text_lower = chunk["text"].lower()
        has_identifier_match = any(
            token.lower() in chunk_text_lower
            for token in identifier_tokens
        )
        boost = IDENTIFIER_BOOST if has_identifier_match else 0.0
        result = dict(chunk)
        result["rerank_score"] = float(ce_score)
        result["identifier_boost"] = boost
        result["final_score"] = float(ce_score) + boost
        scored.append(result)

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored[:k]


# ---------------------------------------------------------------------------
# Task 11: Retriever Class
# ---------------------------------------------------------------------------

class Retriever:
    def __init__(self, index: faiss.Index, chunks: list[dict],
                 model: SentenceTransformer, bm25: BM25Okapi,
                 candidate_k: int = 20):
        self.index = index
        self.chunks = chunks
        self.model = model
        self.bm25 = bm25
        self.candidate_k = candidate_k

    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        """Full retrieval pipeline: hybrid fetch -> identifier-aware rerank -> top-k."""
        candidates = hybrid_retrieve(
            query, self.index, self.chunks, self.model, self.bm25,
            k=self.candidate_k
        )
        return rerank(query, candidates, k=k)
