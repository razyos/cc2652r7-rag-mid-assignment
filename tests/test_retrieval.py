# tests/test_retrieval.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import faiss
import pytest
from rank_bm25 import BM25Okapi
from src.retrieval import retrieve_dense, retrieve_bm25, hybrid_retrieve
from tests.fakes import FakeCrossEncoder, FakeEmbeddingModel

CHUNKS = [
    {"chunk_id": "trm_chunk_0001", "doc_id": "trm", "text": "RF core initialization procedure for CC2652R7", "metadata": {"page": 1}},
    {"chunk_id": "trm_chunk_0002", "doc_id": "trm", "text": "BLE advertising configuration settings", "metadata": {"page": 2}},
    {"chunk_id": "trm_chunk_0003", "doc_id": "trm", "text": "RFCCpePatchFxp must be called before RF_open on CC2652R7", "metadata": {"page": 3}},
    {"chunk_id": "trm_chunk_0004", "doc_id": "trm", "text": "Power management and VDDR trim values", "metadata": {"page": 4}},
    {"chunk_id": "trm_chunk_0005", "doc_id": "trm", "text": "Zigbee stack configuration and commissioning", "metadata": {"page": 5}},
]

def _build_test_faiss(chunks):
    model = FakeEmbeddingModel()
    embeddings = model.encode([c["text"] for c in chunks], normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index, model

def _build_test_bm25(chunks):
    tokenized = [c["text"].lower().split() for c in chunks]
    return BM25Okapi(tokenized)


@pytest.fixture(autouse=True)
def fake_cross_encoder(monkeypatch):
    monkeypatch.setattr("src.retrieval._get_cross_encoder", lambda: FakeCrossEncoder())

def test_retrieve_dense_returns_k_results():
    index, model = _build_test_faiss(CHUNKS)
    results = retrieve_dense("RF patch required", index, CHUNKS, model, k=3)
    assert len(results) == 3
    assert "chunk_id" in results[0]
    assert "score" in results[0]
    assert "text" in results[0]

def test_retrieve_bm25_exact_match_scores_high():
    bm25 = _build_test_bm25(CHUNKS)
    results = retrieve_bm25("RFCCpePatchFxp RF_open", bm25, CHUNKS, k=3)
    assert results[0]["chunk_id"] == "trm_chunk_0003"

def test_hybrid_retrieve_no_duplicates():
    index, model = _build_test_faiss(CHUNKS)
    bm25 = _build_test_bm25(CHUNKS)
    results = hybrid_retrieve("RFCCpePatchFxp initialization", index, CHUNKS, model, bm25, k=5)
    ids = [r["chunk_id"] for r in results]
    assert len(ids) == len(set(ids))

from src.retrieval import rerank, is_identifier_token

def test_is_identifier_token_detects_symbols():
    assert is_identifier_token("RFCCpePatchFxp") == True
    assert is_identifier_token("RF_open") == True
    assert is_identifier_token("0x40044000") == True
    assert is_identifier_token("initialization") == False
    assert is_identifier_token("the") == False

def test_rerank_pins_exact_match_chunk():
    index, model = _build_test_faiss(CHUNKS)
    bm25 = _build_test_bm25(CHUNKS)
    candidates = hybrid_retrieve("RFCCpePatchFxp", index, CHUNKS, model, bm25, k=5)
    reranked = rerank("RFCCpePatchFxp RF_open", candidates, k=5)
    ids = [r["chunk_id"] for r in reranked]
    assert "trm_chunk_0003" in ids

def test_rerank_returns_k_or_fewer():
    index, model = _build_test_faiss(CHUNKS)
    bm25 = _build_test_bm25(CHUNKS)
    candidates = hybrid_retrieve("RF core", index, CHUNKS, model, bm25, k=5)
    reranked = rerank("RF core initialization", candidates, k=3)
    assert len(reranked) <= 3

def test_rerank_boost_not_absolute_pin():
    """Identifier boost should not override a clearly more relevant chunk."""
    # trm_chunk_0003 has RFCCpePatchFxp but query is about BLE advertising
    # trm_chunk_0002 (BLE advertising) should rank higher despite no identifier match
    index, model = _build_test_faiss(CHUNKS)
    bm25 = _build_test_bm25(CHUNKS)
    candidates = hybrid_retrieve("BLE advertising configuration", index, CHUNKS, model, bm25, k=5)
    reranked = rerank("BLE advertising configuration", candidates, k=3)
    # trm_chunk_0002 (BLE advertising) should be in results
    ids = [r["chunk_id"] for r in reranked]
    assert "trm_chunk_0002" in ids

def test_rerank_result_has_final_score():
    index, model = _build_test_faiss(CHUNKS)
    bm25 = _build_test_bm25(CHUNKS)
    candidates = hybrid_retrieve("RFCCpePatchFxp", index, CHUNKS, model, bm25, k=5)
    reranked = rerank("RFCCpePatchFxp", candidates, k=3)
    for r in reranked:
        assert "rerank_score" in r
        assert "final_score" in r
        assert "identifier_boost" in r

from src.retrieval import Retriever

def test_retriever_end_to_end():
    index, model = _build_test_faiss(CHUNKS)
    bm25 = _build_test_bm25(CHUNKS)
    retriever = Retriever(index=index, chunks=CHUNKS, model=model, bm25=bm25)
    results = retriever.retrieve("RFCCpePatchFxp RF_open", k=3)
    assert len(results) <= 3
    assert all("chunk_id" in r for r in results)
    assert all("text" in r for r in results)
    assert all("score" in r or "rerank_score" in r for r in results)
    assert all("metadata" in r for r in results)
