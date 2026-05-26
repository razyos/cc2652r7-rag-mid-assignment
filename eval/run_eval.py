# eval/run_eval.py
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag_system import load_rag_system
from src.generation import check_answerability


def compute_hit_at_k(retrieved_chunk_ids: list, must_cite: list, k: int = 5) -> float:
    """1.0 if any must_cite chunk_id appears in top-k retrieved, else 0.0."""
    if not must_cite:
        return 1.0
    top_k = retrieved_chunk_ids[:k]
    return 1.0 if any(cid in top_k for cid in must_cite) else 0.0


def compute_mrr(retrieved_chunk_ids: list, must_cite: list, k: int = 5) -> float:
    """Reciprocal rank of the first labeled source in top-k, or 0.0."""
    if not must_cite:
        return 0.0
    top_k = retrieved_chunk_ids[:k]
    for index, chunk_id in enumerate(top_k, start=1):
        if chunk_id in must_cite:
            return 1.0 / index
    return 0.0


def has_source_labels(entry: dict) -> bool:
    """True when a gold entry has at least one required source label."""
    return bool(entry.get("must_cite_chunk_ids"))


def summarize_source_metrics(results: list[dict]) -> dict:
    labeled = [r for r in results if r.get("source_labeled")]
    if not labeled:
        return {"labeled_count": 0, "source_hit_at_k": None, "source_mrr": None}
    return {
        "labeled_count": len(labeled),
        "source_hit_at_k": sum(r["source_hit_at_k"] for r in labeled) / len(labeled),
        "source_mrr": sum(r["source_mrr"] for r in labeled) / len(labeled),
    }


def run_eval(gold_path: str = "eval/gold_set.jsonl",
             index_dir: str = "data/processed",
             k: int = 5) -> dict:
    system = load_rag_system(index_dir=index_dir, k=k)

    with open(gold_path) as f:
        gold = [json.loads(line) for line in f if line.strip()]

    results = []
    hit_scores = []
    answerable_scores = []

    for i, entry in enumerate(gold):
        print(f"[{i+1}/{len(gold)}] {entry['question'][:60]}...")
        result = system.answer(entry["question"])

        retrieved_ids = [c["chunk_id"] for c in result["retrieved_chunks"]]
        must_cite = entry.get("must_cite_chunk_ids", [])
        hit = compute_hit_at_k(retrieved_ids, must_cite, k=k)
        hit_scores.append(hit)
        source_labeled = has_source_labels(entry)
        source_hit = compute_hit_at_k(retrieved_ids, must_cite, k=k) if source_labeled else None
        source_mrr = compute_mrr(retrieved_ids, must_cite, k=k) if source_labeled else None

        # Fix 3: Answerable@GenerationContext
        answerability = check_answerability(
            entry.get("reference_answer", ""),
            result["retrieved_chunks"]
        )
        answerable_scores.append(1.0 if answerability["answerable"] else 0.0)

        results.append({
            "question": entry["question"],
            "category": entry["category"],
            "reference_answer": entry.get("reference_answer", ""),
            "system_answer": result["answer"],
            "sources": result["sources"],
            "hit_at_k": hit,
            "source_labeled": source_labeled,
            "source_hit_at_k": source_hit,
            "source_mrr": source_mrr,
            "answerable": answerability["answerable"],
            "answerability_key_terms": answerability["key_terms"],
            "answerability_missing": answerability["missing_terms"],
        })

    hit_at_k = sum(hit_scores) / len(hit_scores) if hit_scores else 0.0
    answerable_at_k = sum(answerable_scores) / len(answerable_scores) if answerable_scores else 0.0
    source_summary = summarize_source_metrics(results)

    categories = {}
    for r in results:
        cat = r["category"]
        categories.setdefault(cat, {"hit": [], "answerable": []})
        categories[cat]["hit"].append(r["hit_at_k"])
        categories[cat]["answerable"].append(1.0 if r["answerable"] else 0.0)

    print(f"\n=== Evaluation Results (k={k}) ===")
    print(f"Overall Hit@{k}:              {hit_at_k:.3f} ({sum(hit_scores):.0f}/{len(hit_scores)})")
    print(f"Overall Answerable@Context:   {answerable_at_k:.3f} ({sum(answerable_scores):.0f}/{len(answerable_scores)})")
    if source_summary["labeled_count"]:
        print(
            f"Source-labeled Hit@{k}:       "
            f"{source_summary['source_hit_at_k']:.3f} "
            f"({source_summary['labeled_count']} labeled)"
        )
        print(f"Source-labeled MRR@{k}:       {source_summary['source_mrr']:.3f}")
    else:
        print(f"Source-labeled Hit@{k}:       not available (0 labeled)")
        print(f"Source-labeled MRR@{k}:       not available (0 labeled)")
    print()
    for cat, scores in sorted(categories.items()):
        h = sum(scores["hit"]) / len(scores["hit"])
        a = sum(scores["answerable"]) / len(scores["answerable"])
        print(f"  {cat:12s}  Hit@{k}={h:.3f}  Answerable={a:.3f}")

    with open("eval/eval_results.json", "w") as f:
        json.dump({
            "hit_at_k": hit_at_k,
            "answerable_at_k": answerable_at_k,
            "source_metrics": source_summary,
            "k": k,
            "results": results
        }, f, indent=2)
    print("\nFull results saved to eval/eval_results.json")

    return {
        "hit_at_k": hit_at_k,
        "answerable_at_k": answerable_at_k,
        "source_metrics": source_summary,
        "results": results,
    }


if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_eval(k=k)
