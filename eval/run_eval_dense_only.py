"""Ablation: dense-only retrieval (no BM25, no reranker)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.build_index import load_faiss_index
from src.retrieval import retrieve_dense
from src.generation import generate_answer
from sentence_transformers import SentenceTransformer

INDEX_DIR = "data/processed"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 5

index, chunks = load_faiss_index(INDEX_DIR)
with open(os.path.join(INDEX_DIR, "model_name.txt")) as f:
    model_name = f.read().strip()
model = SentenceTransformer(model_name)

with open("eval/gold_set.jsonl") as f:
    gold = [json.loads(l) for l in f if l.strip()]

hit_scores = []
for i, entry in enumerate(gold):
    print(f"[{i+1}/{len(gold)}] {entry['question'][:60]}...")
    results = retrieve_dense(entry["question"], index, chunks, model, k=K)
    retrieved_ids = [r["chunk_id"] for r in results]
    must_cite = entry.get("must_cite_chunk_ids", [])
    hit = 1.0 if not must_cite else (1.0 if any(c in retrieved_ids[:K] for c in must_cite) else 0.0)
    hit_scores.append(hit)

print(f"\n=== Dense-Only Retrieval (k={K}) ===")
print(f"Overall Hit@{K}: {sum(hit_scores)/len(hit_scores):.3f} ({sum(hit_scores):.0f}/{len(hit_scores)})")
