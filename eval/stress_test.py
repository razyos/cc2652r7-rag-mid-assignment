"""
Stress test: adversarial questions to find retrieval and generation failures.
Tests: out-of-corpus, ambiguous, exact-symbol, negation, hallucination traps.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag_system import load_rag_system

STRESS_QUESTIONS = [
    # --- Out-of-corpus (should say "not found") ---
    {"q": "What is the CC2652R7 Wi-Fi channel configuration?",
     "category": "out_of_corpus", "expect": "not found"},
    {"q": "How do I configure the CC2652R7 for LTE-M?",
     "category": "out_of_corpus", "expect": "not found"},
    {"q": "What is the price of the CC2652R7 on Mouser?",
     "category": "out_of_corpus", "expect": "not found"},

    # --- Exact symbol queries (tests identifier boost) ---
    {"q": "What does RFCCpePatchFxp do?",
     "category": "exact_symbol", "expect": "patch RF core"},
    {"q": "What is the address of RFC_PWR_PWMCLKEN?",
     "category": "exact_symbol", "expect": "hex address or register"},
    {"q": "When should RF_open be called?",
     "category": "exact_symbol", "expect": "after patch"},

    # --- Negation traps (should not hallucinate) ---
    {"q": "Can I call RF_open without RFCCpePatchFxp?",
     "category": "negation_trap", "expect": "no / must call patch first"},
    {"q": "Does the CC2652R7 have 1MB of flash?",
     "category": "negation_trap", "expect": "no / 704KB"},

    # --- Hallucination traps (specific numbers LLM might invent) ---
    {"q": "What is the exact hex address of the RF core base register on CC2652R7?",
     "category": "hallucination_trap", "expect": "grounded or not found"},
    {"q": "What is the VDDR trim default value in decimal?",
     "category": "hallucination_trap", "expect": "grounded or not found"},

    # --- Ambiguous multi-section questions ---
    {"q": "How does the CC2652R7 handle RF and BLE simultaneously?",
     "category": "ambiguous", "expect": "multi-protocol or not found"},
    {"q": "What happens during CC2652R7 startup sequence?",
     "category": "ambiguous", "expect": "boot / power sequence"},
]

def run_stress_test():
    print("Loading RAG system...")
    system = load_rag_system()
    print(f"Running {len(STRESS_QUESTIONS)} stress questions...\n")

    results = []
    failures = []

    for i, item in enumerate(STRESS_QUESTIONS):
        q = item["q"]
        cat = item["category"]
        print(f"[{i+1}/{len(STRESS_QUESTIONS)}] [{cat}] {q[:70]}...")

        result = system.answer(q)
        answer = result["answer"]
        validation = result.get("validation", {})
        trace = result.get("trace", {})

        grounded = validation.get("grounded", True)
        ungrounded = validation.get("ungrounded_literals", [])
        pins = trace.get("identifier_pins", [])
        dedup_count = trace.get("deduplicated_count", "?")

        # Detect likely failure modes
        not_found_correctly = (
            cat == "out_of_corpus" and
            ("not found" in answer.lower() or "not in the" in answer.lower() or
             "not available" in answer.lower() or "not provided" in answer.lower() or
             "not mentioned" in answer.lower())
        )
        hallucination_flag = not grounded and len(ungrounded) > 0

        status = "PASS"
        notes = []

        if cat == "out_of_corpus" and not not_found_correctly:
            status = "FAIL"
            notes.append("answered out-of-corpus question without saying not found")
        if hallucination_flag:
            status = "WARN"
            notes.append(f"ungrounded literals: {ungrounded}")

        print(f"  Status: {status}")
        print(f"  Grounded: {grounded} | Ungrounded: {ungrounded}")
        print(f"  Identifier pins: {pins}")
        print(f"  Chunks after dedup: {dedup_count}")
        print(f"  Answer (first 200 chars): {answer[:200]}")
        if notes:
            print(f"  Notes: {notes}")
        print()

        entry = {
            "question": q,
            "category": cat,
            "expected": item["expect"],
            "answer": answer,
            "status": status,
            "grounded": grounded,
            "ungrounded_literals": ungrounded,
            "identifier_pins": pins,
            "deduplicated_count": dedup_count,
            "notes": notes,
        }
        results.append(entry)
        if status in ("FAIL", "WARN"):
            failures.append(entry)

    print("=" * 60)
    print(f"STRESS TEST COMPLETE: {len(STRESS_QUESTIONS)} questions")
    print(f"  PASS: {sum(1 for r in results if r['status'] == 'PASS')}")
    print(f"  WARN: {sum(1 for r in results if r['status'] == 'WARN')}")
    print(f"  FAIL: {sum(1 for r in results if r['status'] == 'FAIL')}")

    with open("eval/stress_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nFull results saved to eval/stress_test_results.json")

if __name__ == "__main__":
    run_stress_test()
