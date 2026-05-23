import os
from pypdf import PdfReader
from bs4 import BeautifulSoup


def load_html(path: str, doc_id: str) -> list[dict]:
    """Load an HTML file, split by h2/h3 headings, return one doc per section."""
    filename = os.path.basename(path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    docs = []
    current_section = "Introduction"
    current_texts = []

    for tag in soup.find_all(["h2", "h3", "p", "pre", "li", "td"]):
        if tag.name in ("h2", "h3"):
            text = " ".join(current_texts).strip()
            if text:
                docs.append({
                    "doc_id": doc_id,
                    "text": text,
                    "metadata": {"source": filename, "section": current_section}
                })
            current_section = tag.get_text(strip=True)
            current_texts = []
        else:
            t = tag.get_text(separator=" ", strip=True)
            if t:
                current_texts.append(t)

    text = " ".join(current_texts).strip()
    if text:
        docs.append({
            "doc_id": doc_id,
            "text": text,
            "metadata": {"source": filename, "section": current_section}
        })

    return [d for d in docs if len(d["text"].strip()) > 20]


def chunk_fixed(docs: list[dict], chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """Split documents into fixed-size word-based chunks with overlap."""
    chunks = []
    for doc in docs:
        words = doc["text"].split()
        start = 0
        chunk_idx = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunk_id = f"{doc['doc_id']}_fixed_chunk_{chunk_idx:04d}"
            chunk_meta = dict(doc["metadata"])
            chunk_meta["chunk_strategy"] = "fixed"
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc["doc_id"],
                "text": chunk_text,
                "metadata": chunk_meta,
            })
            if end == len(words):
                break
            start += chunk_size - overlap
            chunk_idx += 1
    return chunks


def chunk_hierarchical(docs: list[dict], max_tokens: int = 600, target_tokens: int = 500) -> list[dict]:
    """
    Hierarchical section-aware chunker.
    If a doc fits within max_tokens words, keep it as one chunk.
    If it exceeds max_tokens words, sub-split into target_tokens-word chunks.
    Preserves section breadcrumb from metadata.
    """
    chunks = []
    for doc in docs:
        words = doc["text"].split()
        base_id = f"{doc['doc_id']}_hier"

        if len(words) <= max_tokens:
            chunk_id = f"{base_id}_chunk_{len(chunks):04d}"
            meta = dict(doc["metadata"])
            meta["chunk_strategy"] = "hierarchical"
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc["doc_id"],
                "text": doc["text"],
                "metadata": meta,
            })
        else:
            start = 0
            sub_idx = 0
            while start < len(words):
                end = min(start + target_tokens, len(words))
                chunk_text = " ".join(words[start:end])
                chunk_id = f"{base_id}_chunk_{len(chunks):04d}_sub{sub_idx}"
                meta = dict(doc["metadata"])
                meta["chunk_strategy"] = "hierarchical"
                meta["sub_chunk"] = sub_idx
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc["doc_id"],
                    "text": chunk_text,
                    "metadata": meta,
                })
                if end == len(words):
                    break
                start += target_tokens
                sub_idx += 1

    return chunks


def load_pdf(path: str, doc_id: str) -> list[dict]:
    """Load a PDF file and return one document per page."""
    reader = PdfReader(path)
    filename = os.path.basename(path)
    docs = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if not text:
            continue
        docs.append({
            "doc_id": doc_id,
            "text": text,
            "metadata": {
                "source": filename,
                "page": page_num,
            }
        })
    return docs
