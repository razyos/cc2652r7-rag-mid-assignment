# CC2652R7 RAG Pipeline

A complete Retrieval-Augmented Generation (RAG) pipeline over TI CC2652R7 documentation for firmware debugging.

## Setup

```bash
pip install -r requirements.txt
```

## Build Index

```bash
python src/build_index.py
```

## Run Evaluation

```bash
python eval/run_eval.py
```

## Live Demo (with CC2652R7 board)

```bash
python demo.py /dev/tty.usbmodem<PORT>
```

## System Interface

```python
from src.rag_system import load_rag_system

system = load_rag_system()
result = system.answer("Why does RF_open fail on CC2652R7?")
print(result["answer"])
print(result["sources"])
```

## Project Structure

```
mid_ass/
├── data/
│   ├── raw/              # TI PDFs and HTML documentation
│   ├── processed/        # Built FAISS and BM25 indexes
│   └── MANIFEST.md       # Corpus description
├── src/
│   ├── build_index.py    # Builds FAISS + BM25 indexes from corpus
│   ├── rag_system.py     # Main answer() interface
│   ├── retrieval.py      # Hybrid retriever + identifier-aware reranker
│   ├── generation.py     # Ollama generation with citation prompt
│   └── utils.py          # PDF/HTML loaders, chunkers
├── eval/
│   ├── gold_set.jsonl    # 50 Q&A evaluation pairs
│   └── run_eval.py       # Evaluation runner (Hit@k metric)
├── demo.py               # Live CC2652R7 demo with UART capture
├── report.md             # Editable final report source
├── report.pdf            # Final assignment report
├── requirements.txt
└── README.md
```
