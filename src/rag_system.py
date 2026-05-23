# src/rag_system.py
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from src.retrieval import (
    Retriever,
    retrieve_dense,
    retrieve_bm25,
    hybrid_retrieve,
    rerank,
    is_identifier_token,
)
from src.generation import generate_answer, deduplicate_and_budget, validate_answer


class RAGSystem:
    def __init__(self, index: faiss.Index, chunks: list[dict],
                 model: SentenceTransformer, bm25: BM25Okapi,
                 k: int = 5, ollama_model: str = "llama3.2"):
        self.retriever = Retriever(index=index, chunks=chunks, model=model, bm25=bm25)
        self.k = k
        self.ollama_model = ollama_model

    def answer(self, question: str) -> dict:
        """
        Main interface: retrieve relevant chunks, generate grounded answer.
        Returns {"answer": str, "sources": list[str], "retrieved_chunks": list[dict],
                 "trace": dict}
        The trace captures every pipeline stage for diagnostic attribution.
        """
        candidate_k = self.retriever.candidate_k

        # Stage 1: Dense retrieval
        dense_results = retrieve_dense(
            question, self.retriever.index, self.retriever.chunks,
            self.retriever.model, k=candidate_k
        )
        dense_candidates = [
            {"chunk_id": c["chunk_id"], "score": c["score"]} for c in dense_results
        ]

        # Stage 2: BM25 retrieval
        bm25_results = retrieve_bm25(
            question, self.retriever.bm25, self.retriever.chunks, k=candidate_k
        )
        bm25_candidates = [
            {"chunk_id": c["chunk_id"], "score": c["score"]} for c in bm25_results
        ]

        # Stage 3: Hybrid merge (deduplicate, max-score fusion)
        hybrid_results = hybrid_retrieve(
            question, self.retriever.index, self.retriever.chunks,
            self.retriever.model, self.retriever.bm25, k=candidate_k
        )
        hybrid_candidates = [
            {"chunk_id": c["chunk_id"], "score": c["score"]} for c in hybrid_results
        ]

        # Stage 4: Identify pinned chunks (identifier-aware pre-filter)
        query_tokens = question.split()
        identifier_tokens = [t for t in query_tokens if is_identifier_token(t)]
        identifier_pins = [
            c["chunk_id"] for c in hybrid_results
            if any(tok.lower() in c["text"].lower() for tok in identifier_tokens)
        ]

        # Stage 5: Rerank
        reranked_results = rerank(question, hybrid_results, k=self.k)

        # Stage 5b: Inject datasheet anchor chunks for spec questions.
        # The cross-encoder demotes the features-list chunk (chunk_0000) for specific
        # peripheral queries, but it is the authoritative source for counts/voltage/GPIO.
        _SPEC_TERMS = ("uart", "spi", "ssi", "i2c", "voltage", "supply", "gpio", "i/o",
                       "clock", "frequency", "timer", "package", "temperature",
                       "flash", "sram", "ram", "wireless protocol", "protocols")
        qn_lower = question.lower()
        if any(term in qn_lower for term in _SPEC_TERMS):
            anchor_ids = {"datasheet_hier_chunk_0000"}
            already = {r["chunk_id"] for r in reranked_results}
            anchors = [c for c in self.retriever.chunks
                       if c["chunk_id"] in anchor_ids and c["chunk_id"] not in already]
            # Prepend anchor so it is always within the token budget
            reranked_results = anchors + reranked_results
        reranked = [
            {"chunk_id": c["chunk_id"], "rerank_score": c.get("rerank_score", 0.0)}
            for c in reranked_results
        ]

        # Stage 6: Deduplicate and enforce token budget
        deduplicated_results = deduplicate_and_budget(reranked_results)
        deduplicated_count = len(deduplicated_results)

        # Stage 7: Final chunks sent to generator
        retrieved = deduplicated_results
        final_chunks = [
            {
                "chunk_id": c["chunk_id"],
                "source": c.get("metadata", {}).get("source", ""),
                "location": (
                    c.get("metadata", {}).get("page")
                    or c.get("metadata", {}).get("section", "")
                ),
            }
            for c in retrieved
        ]

        # Token estimate: rough word count of all chunk texts joined
        context_text = " ".join(c.get("text", "") for c in retrieved)
        token_estimate = len(context_text.split())

        answer_text = generate_answer(question, retrieved, model=self.ollama_model)
        sources = [c["chunk_id"] for c in retrieved]
        validation = validate_answer(answer_text, retrieved)

        trace = {
            "query": question,
            "dense_candidates": dense_candidates,
            "bm25_candidates": bm25_candidates,
            "hybrid_candidates": hybrid_candidates,
            "identifier_pins": identifier_pins,
            "reranked": reranked,
            "final_chunks": final_chunks,
            "token_estimate": token_estimate,
            "deduplicated_count": deduplicated_count,
            "validation_warning": validation["warning"],
        }

        return {
            "answer": answer_text,
            "sources": sources,
            "retrieved_chunks": retrieved,
            "trace": trace,
            "validation": validation,
        }


def load_rag_system(index_dir: str = "data/processed",
                    embed_model: str = "BAAI/bge-large-en-v1.5",
                    k: int = 5) -> "RAGSystem":
    """Load indexes from disk and return a ready RAGSystem."""
    try:
        from src.build_index import load_faiss_index, load_bm25_index
    except ModuleNotFoundError:
        from build_index import load_faiss_index, load_bm25_index
    index, chunks = load_faiss_index(index_dir)
    bm25, _ = load_bm25_index(index_dir)
    model = SentenceTransformer(embed_model)
    return RAGSystem(index=index, chunks=chunks, model=model, bm25=bm25, k=k)
