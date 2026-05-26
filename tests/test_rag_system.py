# tests/test_rag_system.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch
import pytest
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from src.rag_system import RAGSystem
from tests.fakes import FakeCrossEncoder, FakeEmbeddingModel

CHUNKS = [
    {"chunk_id": "trm_chunk_0001", "doc_id": "trm",
     "text": "RFCCpePatchFxp must be called before RF_open on CC2652R7.",
     "metadata": {"source": "swcu192.pdf", "page": 891}},
]

def _make_system():
    model = FakeEmbeddingModel()
    emb = model.encode([c["text"] for c in CHUNKS], normalize_embeddings=True)
    emb = np.array(emb, dtype="float32")
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    tokenized = [c["text"].lower().split() for c in CHUNKS]
    bm25 = BM25Okapi(tokenized)
    return RAGSystem(index=index, chunks=CHUNKS, model=model, bm25=bm25)


@pytest.fixture(autouse=True)
def fake_cross_encoder(monkeypatch):
    monkeypatch.setattr("src.retrieval._get_cross_encoder", lambda: FakeCrossEncoder())

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


@pytest.mark.parametrize(
    "question",
    [
        "Does the CC2652R7 support Wi-Fi?",
        "Does the CC2652R7 support USB?",
        "Does the CC2652R7 support LTE or cellular connectivity?",
        "Does the CC2652R7 have an Ethernet interface?",
        "Does the CC2652R7 support Bluetooth Classic (BR/EDR)?",
    ],
)
def test_answer_injects_datasheet_anchor_for_unsupported_connectivity_questions(question):
    anchor = {
        "chunk_id": "datasheet_hier_chunk_0000",
        "doc_id": "datasheet",
        "text": (
            "Wireless protocol support Thread, Zigbee, Matter. "
            "Bluetooth 5.2 Low Energy. SimpleLink TI 15.4-stack. "
            "6LoWPAN. Proprietary systems."
        ),
        "metadata": {"source": "cc2652r7.pdf", "page": 1},
    }
    application_chunk = {
        "chunk_id": "datasheet_hier_chunk_0001_sub0",
        "doc_id": "datasheet",
        "text": "Communication equipment includes wireless LAN or Wi-Fi access points.",
        "metadata": {"source": "cc2652r7.pdf", "page": 2},
    }
    hybrid_chunk = dict(application_chunk)
    hybrid_chunk["score"] = 0.7
    reranked_chunk = dict(application_chunk)
    reranked_chunk["rerank_score"] = 0.6
    system = RAGSystem(index=None, chunks=[anchor, application_chunk], model=None, bm25=None)

    with patch("src.rag_system.retrieve_dense", return_value=[]), \
         patch("src.rag_system.retrieve_bm25", return_value=[]), \
         patch("src.rag_system.hybrid_retrieve", return_value=[hybrid_chunk]), \
         patch("src.rag_system.rerank", return_value=[reranked_chunk]), \
         patch("src.rag_system.generate_answer", return_value="ANSWER: No") as mock_generate, \
         patch(
             "src.rag_system.validate_answer",
             return_value={"grounded": True, "ungrounded_literals": [], "warning": None},
         ):
        system.answer(question)

    final_chunks = mock_generate.call_args.args[1]
    assert final_chunks[0]["chunk_id"] == "datasheet_hier_chunk_0000"
