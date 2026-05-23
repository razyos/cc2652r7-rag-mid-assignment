import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import load_pdf

def test_load_pdf_returns_list_of_docs():
    docs = load_pdf("data/raw/cc2652r7.pdf", doc_id="datasheet")
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert "doc_id" in docs[0]
    assert "text" in docs[0]
    assert "metadata" in docs[0]
    assert docs[0]["doc_id"] == "datasheet"
    assert docs[0]["metadata"]["source"] == "cc2652r7.pdf"
    assert isinstance(docs[0]["metadata"]["page"], int)
    assert len(docs[0]["text"]) > 0


# Task 3: HTML Loader
from src.utils import load_html

def test_load_html_returns_list_of_docs():
    docs = load_html("data/raw/Users_Guide.html", doc_id="sdk_guide")
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert docs[0]["doc_id"] == "sdk_guide"
    assert docs[0]["metadata"]["source"] == "Users_Guide.html"
    assert "section" in docs[0]["metadata"]
    assert len(docs[0]["text"]) > 0

def test_load_html_sections_are_non_empty():
    docs = load_html("data/raw/Users_Guide.html", doc_id="sdk_guide")
    for doc in docs:
        assert len(doc["text"].strip()) > 20


# Task 4: Fixed-Size Chunker
from src.utils import chunk_fixed

def test_chunk_fixed_produces_chunks():
    docs = [{"doc_id": "test", "text": "word " * 200, "metadata": {"source": "test.pdf", "page": 1}}]
    chunks = chunk_fixed(docs, chunk_size=50, overlap=10)
    assert len(chunks) > 1
    assert "chunk_id" in chunks[0]
    assert "doc_id" in chunks[0]
    assert "text" in chunks[0]
    assert "metadata" in chunks[0]
    assert chunks[0]["doc_id"] == "test"

def test_chunk_fixed_chunk_id_is_unique():
    docs = [{"doc_id": "test", "text": "word " * 300, "metadata": {"source": "test.pdf", "page": 1}}]
    chunks = chunk_fixed(docs, chunk_size=50, overlap=10)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))

def test_chunk_fixed_overlap_creates_shared_content():
    words = [f"word{i}" for i in range(100)]
    text = " ".join(words)
    docs = [{"doc_id": "test", "text": text, "metadata": {"source": "test.pdf", "page": 1}}]
    chunks = chunk_fixed(docs, chunk_size=20, overlap=5)
    chunk0_words = chunks[0]["text"].split()
    chunk1_words = chunks[1]["text"].split()
    assert chunk0_words[-5:] == chunk1_words[:5]


# Task 5: Hierarchical Section-Aware Chunker
from src.utils import chunk_hierarchical

def test_chunk_hierarchical_short_doc_is_single_chunk():
    docs = [{"doc_id": "test", "text": "short text here", "metadata": {"source": "test.pdf", "page": 1, "section": "Intro"}}]
    chunks = chunk_hierarchical(docs, max_tokens=600, target_tokens=500)
    assert len(chunks) == 1
    assert chunks[0]["text"] == "short text here"

def test_chunk_hierarchical_long_doc_is_split():
    long_text = "word " * 700
    docs = [{"doc_id": "test", "text": long_text, "metadata": {"source": "test.pdf", "page": 1, "section": "RF Core"}}]
    chunks = chunk_hierarchical(docs, max_tokens=600, target_tokens=500)
    assert len(chunks) > 1

def test_chunk_hierarchical_breadcrumb_in_metadata():
    docs = [{"doc_id": "trm", "text": "word " * 100, "metadata": {"source": "swcu192.pdf", "page": 5, "section": "RF Core > Patching"}}]
    chunks = chunk_hierarchical(docs, max_tokens=600, target_tokens=500)
    assert "section" in chunks[0]["metadata"]
    assert chunks[0]["metadata"]["section"] == "RF Core > Patching"

def test_chunk_hierarchical_ids_are_unique():
    long_text = "word " * 800
    docs = [{"doc_id": "test", "text": long_text, "metadata": {"source": "test.pdf", "page": 1, "section": "A"}}]
    chunks = chunk_hierarchical(docs, max_tokens=600, target_tokens=500)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
