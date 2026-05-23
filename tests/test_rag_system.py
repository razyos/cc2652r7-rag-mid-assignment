# tests/test_rag_system.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from src.rag_system import RAGSystem

CHUNKS = [
    {"chunk_id": "trm_chunk_0001", "doc_id": "trm",
     "text": "RFCCpePatchFxp must be called before RF_open on CC2652R7.",
     "metadata": {"source": "swcu192.pdf", "page": 891}},
]

def _make_system():
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    emb = model.encode([c["text"] for c in CHUNKS], normalize_embeddings=True)
    emb = np.array(emb, dtype="float32")
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    tokenized = [c["text"].lower().split() for c in CHUNKS]
    bm25 = BM25Okapi(tokenized)
    return RAGSystem(index=index, chunks=CHUNKS, model=model, bm25=bm25)

def test_answer_returns_required_keys():
    system = _make_system()
    with patch("src.generation.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "Call RFCCpePatchFxp first."}}
        result = system.answer("Why does RF_open fail?")
    assert "answer" in result
    assert "sources" in result
    assert "retrieved_chunks" in result

def test_answer_sources_are_strings():
    system = _make_system()
    with patch("src.generation.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "answer text"}}
        result = system.answer("What is RF patching?")
    assert isinstance(result["sources"], list)
    assert all(isinstance(s, str) for s in result["sources"])

def test_answer_retrieved_chunks_have_metadata():
    system = _make_system()
    with patch("src.generation.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "answer"}}
        result = system.answer("RF core")
    for chunk in result["retrieved_chunks"]:
        assert "chunk_id" in chunk
        assert "text" in chunk
        assert "metadata" in chunk

def test_answer_includes_trace():
    system = _make_system()
    with patch("src.generation.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "answer"}}
        result = system.answer("RFCCpePatchFxp RF_open")
    assert "trace" in result
    assert "query" in result["trace"]
    assert "dense_candidates" in result["trace"]
    assert "bm25_candidates" in result["trace"]
    assert "hybrid_candidates" in result["trace"]
    assert "identifier_pins" in result["trace"]
    assert "reranked" in result["trace"]
    assert "final_chunks" in result["trace"]
    assert "token_estimate" in result["trace"]
    assert result["trace"]["query"] == "RFCCpePatchFxp RF_open"

def test_answer_includes_validation():
    system = _make_system()
    with patch("src.generation.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "Call RFCCpePatchFxp before RF_open."}}
        result = system.answer("Why does RF_open fail?")
    assert "validation" in result
    assert "grounded" in result["validation"]
    assert "ungrounded_literals" in result["validation"]
    assert "warning" in result["validation"]
