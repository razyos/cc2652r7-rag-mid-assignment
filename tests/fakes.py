import re

import numpy as np


_FEATURES = (
    ("rf", "rf_open", "rfccpepatchfxp", "patch"),
    ("core", "initialization", "initialize"),
    ("ble", "advertising"),
    ("configuration", "settings"),
    ("power", "vddr", "trim"),
    ("zigbee", "commissioning"),
    ("cc2652r7",),
    ("procedure", "called", "before"),
)


class FakeEmbeddingModel:
    """Small deterministic encoder for unit tests that should not start torch."""

    def encode(self, texts, normalize_embeddings=True, **_kwargs):
        rows = []
        for text in texts:
            normalized = text.lower()
            tokens = set(re.findall(r"[a-z0-9_]+", normalized))
            row = []
            for terms in _FEATURES:
                score = sum(
                    1.0
                    for term in terms
                    if term in tokens or term in normalized
                )
                row.append(score)
            rows.append(row)

        embeddings = np.array(rows, dtype="float32")
        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / np.where(norms == 0, 1.0, norms)
        return embeddings


class FakeCrossEncoder:
    """Scores query/chunk pairs by token overlap for reranker tests."""

    def predict(self, pairs):
        scores = []
        for query, text in pairs:
            query_terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
            text_terms = set(re.findall(r"[a-z0-9_]+", text.lower()))
            scores.append(float(len(query_terms & text_terms)))
        return np.array(scores, dtype="float32")
