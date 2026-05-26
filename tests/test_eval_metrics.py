import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.run_eval import (
    compute_hit_at_k,
    compute_mrr,
    has_source_labels,
    summarize_source_metrics,
)


def test_compute_hit_at_k_requires_matching_labeled_source():
    retrieved = ["a", "b", "c"]
    assert compute_hit_at_k(retrieved, ["b"], k=2) == 1.0
    assert compute_hit_at_k(retrieved, ["c"], k=2) == 0.0


def test_compute_mrr_uses_first_matching_rank():
    retrieved = ["wrong", "target", "also_target"]
    assert compute_mrr(retrieved, ["target", "also_target"], k=5) == 0.5


def test_compute_mrr_returns_zero_without_label_or_match():
    assert compute_mrr(["a", "b"], [], k=5) == 0.0
    assert compute_mrr(["a", "b"], ["z"], k=5) == 0.0


def test_has_source_labels_detects_non_empty_labels():
    assert has_source_labels({"must_cite_chunk_ids": ["datasheet_hier_chunk_0000"]}) is True
    assert has_source_labels({"must_cite_chunk_ids": []}) is False
    assert has_source_labels({}) is False


def test_summarize_source_metrics_counts_only_labeled_entries():
    rows = [
        {"source_labeled": True, "source_hit_at_k": 1.0, "source_mrr": 1.0},
        {"source_labeled": True, "source_hit_at_k": 0.0, "source_mrr": 0.0},
        {"source_labeled": False, "source_hit_at_k": None, "source_mrr": None},
    ]

    summary = summarize_source_metrics(rows)

    assert summary["labeled_count"] == 2
    assert summary["source_hit_at_k"] == 0.5
    assert summary["source_mrr"] == 0.5
