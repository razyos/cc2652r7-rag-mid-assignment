# src/build_index.py
import json
import os
import pickle
import sys

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi


def build_faiss_index(chunks: list[dict], model_name: str = "BAAI/bge-large-en-v1.5",
                       save_path: str = None, model=None) -> tuple:
    """Embed chunks and build a FAISS inner-product index."""
    if model is None:
        model = SentenceTransformer(model_name)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    embeddings = np.array(embeddings, dtype="float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    if save_path:
        os.makedirs(save_path, exist_ok=True)
        faiss.write_index(index, os.path.join(save_path, "faiss.index"))
        with open(os.path.join(save_path, "chunks.json"), "w") as f:
            json.dump(chunks, f)
        with open(os.path.join(save_path, "model_name.txt"), "w") as f:
            f.write(model_name)

    return index, chunks


def load_faiss_index(index_path: str) -> tuple:
    """Load a saved FAISS index and chunks."""
    index = faiss.read_index(os.path.join(index_path, "faiss.index"))
    with open(os.path.join(index_path, "chunks.json")) as f:
        chunks = json.load(f)
    return index, chunks


def build_bm25_index(chunks: list[dict], save_path: str = None) -> tuple:
    """Build BM25 index over chunk texts."""
    tokenized = [c["text"].lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized)

    if save_path:
        os.makedirs(save_path, exist_ok=True)
        with open(os.path.join(save_path, "bm25.pkl"), "wb") as f:
            pickle.dump(bm25, f)
        with open(os.path.join(save_path, "bm25_chunks.json"), "w") as f:
            json.dump(chunks, f)

    return bm25, chunks


def load_bm25_index(index_path: str) -> tuple:
    """Load a saved BM25 index and chunks."""
    with open(os.path.join(index_path, "bm25.pkl"), "rb") as f:
        bm25 = pickle.load(f)
    with open(os.path.join(index_path, "bm25_chunks.json")) as f:
        chunks = json.load(f)
    return bm25, chunks


# ── Orchestrator ──────────────────────────────────────────────────────────────

try:
    from src.utils import load_pdf, load_html, chunk_fixed, chunk_hierarchical
except ModuleNotFoundError:
    # When run directly as a script (python src/build_index.py), sys.path does
    # not include the package root, so fall back to a sibling-module import.
    from utils import load_pdf, load_html, chunk_fixed, chunk_hierarchical

INDEX_DIR = "data/processed"
EMBED_MODEL = "BAAI/bge-large-en-v1.5"


def build_all_indexes(strategy: str = "hierarchical") -> None:
    """
    Full pipeline: load all corpus docs → chunk → build FAISS + BM25 indexes.
    strategy: "fixed" or "hierarchical"
    """
    print("Loading documents...")
    docs = []
    docs += load_pdf("data/raw/cc2652r7.pdf", doc_id="datasheet")
    docs += load_pdf("data/raw/swcu192.pdf", doc_id="trm")
    docs += load_html("data/raw/Users_Guide.html", doc_id="sdk_guide")
    print(f"Loaded {len(docs)} document pages/sections")

    print(f"Chunking with strategy: {strategy}...")
    if strategy == "fixed":
        chunks = chunk_fixed(docs, chunk_size=512, overlap=64)
    else:
        chunks = chunk_hierarchical(docs, max_tokens=600, target_tokens=500)
    print(f"Created {len(chunks)} chunks")

    with open(os.path.join(INDEX_DIR, "chunks.json"), "w") as f:
        json.dump(chunks, f, indent=2)

    print("Building FAISS index...")
    build_faiss_index(chunks, model_name=EMBED_MODEL, save_path=INDEX_DIR)

    print("Building BM25 index...")
    build_bm25_index(chunks, save_path=INDEX_DIR)

    print(f"Done. Indexes saved to {INDEX_DIR}/")


if __name__ == "__main__":
    strategy = sys.argv[1] if len(sys.argv) > 1 else "hierarchical"
    os.makedirs(INDEX_DIR, exist_ok=True)
    build_all_indexes(strategy=strategy)
