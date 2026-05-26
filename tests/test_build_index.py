import tempfile

from src.build_index import (
    build_bm25_index,
    build_faiss_index,
    load_bm25_index,
    load_faiss_index,
)
from tests.fakes import FakeEmbeddingModel

SAMPLE_CHUNKS = [
    {"chunk_id": "a_chunk_0001", "doc_id": "a", "text": "RF core initialization procedure", "metadata": {}},
    {"chunk_id": "a_chunk_0002", "doc_id": "a", "text": "BLE advertising configuration", "metadata": {}},
    {"chunk_id": "a_chunk_0003", "doc_id": "a", "text": "RFCCpePatchFxp must be called before RF_open", "metadata": {}},
]

def test_build_faiss_index_returns_index_and_chunks():
    index, chunks = build_faiss_index(
        SAMPLE_CHUNKS,
        model_name="fake-embedding-model",
        model=FakeEmbeddingModel(),
    )
    assert index.ntotal == 3
    assert len(chunks) == 3

def test_faiss_index_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        build_faiss_index(
            SAMPLE_CHUNKS,
            model_name="fake-embedding-model",
            model=FakeEmbeddingModel(),
            save_path=tmpdir,
        )
        loaded_index, loaded_chunks = load_faiss_index(tmpdir)
        assert loaded_index.ntotal == 3
        assert loaded_chunks[0]["chunk_id"] == SAMPLE_CHUNKS[0]["chunk_id"]

def test_build_bm25_returns_bm25_object():
    bm25, chunks = build_bm25_index(SAMPLE_CHUNKS)
    scores = bm25.get_scores("RFCCpePatchFxp".split())
    assert len(scores) == 3
    assert scores[2] == max(scores)

def test_bm25_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        build_bm25_index(SAMPLE_CHUNKS, save_path=tmpdir)
        loaded_bm25, loaded_chunks = load_bm25_index(tmpdir)
        scores = loaded_bm25.get_scores("RFCCpePatchFxp".split())
        assert scores[2] == max(scores)
