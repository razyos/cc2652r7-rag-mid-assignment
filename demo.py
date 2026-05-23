#!/usr/bin/env python3
"""
Live CC2652R7 RAG Demo
Shows: bare LLM failure → UART error capture → RAG correct answer

Demo 1 (no board): Flash memory size — bare LLM hallucinates, RAG cites datasheet
Demo 2 (with board): UART error from CC2652R7 → RAG diagnosis with TI TRM citation

Usage:
  python demo.py               # offline demo only
  python demo.py /dev/tty.usbmodem<PORT>   # + live board UART capture
"""
import sys
import ollama
from src.rag_system import load_rag_system

# Questions grounded in our indexed corpus (datasheet + TRM)
DEMO_QUESTION_OFFLINE = "How much flash memory does the CC2652R7 have, and what is its CPU clock speed?"
DEMO_QUESTION_BOARD_FALLBACK = "CC2652R7 RF core is not responding. What power domain must be enabled, and how?"

SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 30


def bare_llm_answer(question: str) -> str:
    """Query Llama 3.2 with no context (no RAG)."""
    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": question}]
    )
    return response["message"]["content"]


def capture_uart_error(port: str, timeout: int = SERIAL_TIMEOUT) -> str:
    """Listen on UART, return first error line."""
    import serial
    print(f"\nListening on {port} at {SERIAL_BAUD} baud (timeout {timeout}s)...")
    with serial.Serial(port, SERIAL_BAUD, timeout=timeout) as ser:
        while True:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if line:
                print(f"  UART: {line}")
            if "[ERROR]" in line or "failed" in line.lower():
                return line
    return ""


def run_demo_pair(label: str, question: str, system) -> None:
    """Show bare LLM vs RAG side-by-side for one question."""
    print(f"\n{'='*60}")
    print(f"DEMO {label}")
    print(f"Question: {question}")
    print("=" * 60)

    print("\n[Bare LLM — no documentation]")
    bare = bare_llm_answer(question)
    print(bare[:600])

    print("\n[RAG — with TI datasheet + TRM]")
    result = system.answer(question)
    print(result["answer"])

    print("\n[Sources retrieved]")
    for chunk in result["retrieved_chunks"][:3]:
        meta = chunk.get("metadata", {})
        loc = f"page {meta['page']}" if "page" in meta else meta.get("section", chunk["chunk_id"])
        print(f"  - {chunk['chunk_id']} | {loc}")

    val = result.get("validation", {})
    if not val.get("grounded", True):
        print(f"  WARNING: possible ungrounded literals: {val.get('ungrounded_literals', [])}")


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else None

    print("Loading RAG system...")
    system = load_rag_system()

    # Demo 1: Always runs — flash size / clock speed (corpus-grounded)
    run_demo_pair("1 (offline)", DEMO_QUESTION_OFFLINE, system)

    # Demo 2: Live board UART capture, or fallback RF power domain question
    if port:
        print(f"\n[Waiting for UART error from board on {port}...]")
        uart_error = capture_uart_error(port)
        question2 = f"{uart_error}. What is the cause and fix?" if uart_error else DEMO_QUESTION_BOARD_FALLBACK
        if uart_error:
            print(f"Captured: {uart_error}")
    else:
        question2 = DEMO_QUESTION_BOARD_FALLBACK

    run_demo_pair("2 (board / RF)", question2, system)

    print("\n" + "=" * 60)
    print("Demo complete.")


if __name__ == "__main__":
    main()
