# tests/test_generation.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch
from src.generation import (
    check_answerability,
    format_context,
    generate_answer,
    deduplicate_and_budget,
    validate_answer,
)

SAMPLE_CHUNKS = [
    {"chunk_id": "trm_chunk_0003", "text": "RFCCpePatchFxp must be called before RF_open.",
     "metadata": {"source": "swcu192.pdf", "page": 891}, "rerank_score": 0.9},
    {"chunk_id": "sdk_chunk_0042", "text": "Use RF_open() after applying the CPE patch.",
     "metadata": {"source": "Users_Guide.html", "section": "RF Driver"}, "rerank_score": 0.7},
]

DATASHEET_FEATURE_CHUNK = {
    "chunk_id": "datasheet_hier_chunk_0000",
    "text": (
        "Wireless protocol support Thread, Zigbee, Matter. "
        "Bluetooth 5.2 Low Energy. SimpleLink TI 15.4-stack. "
        "6LoWPAN. Proprietary systems. MCU peripherals include "
        "Two UART, two SSI, I2C, I2S, 31 GPIOs."
    ),
    "metadata": {"source": "cc2652r7.pdf", "page": 1},
}

def test_format_context_includes_chunk_id_and_source():
    context = format_context(SAMPLE_CHUNKS)
    assert "trm_chunk_0003" in context
    assert "swcu192.pdf" in context
    assert "RFCCpePatchFxp" in context

def test_generate_answer_calls_ollama():
    with patch("src.generation.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "Call RFCCpePatchFxp first."}}
        answer = generate_answer("Why does RF_open fail?", SAMPLE_CHUNKS)
        assert answer == "Call RFCCpePatchFxp first."
        mock_chat.assert_called_once()

def test_generate_answer_prompt_contains_question_and_context():
    with patch("src.generation.ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "some answer"}}
        generate_answer("Why does RF_open fail?", SAMPLE_CHUNKS)
        call_args = mock_chat.call_args
        # Handle both positional and keyword args
        if call_args.kwargs.get("messages"):
            messages = call_args.kwargs["messages"]
        else:
            messages = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("messages", [])
        prompt = messages[-1]["content"]
        assert "Why does RF_open fail?" in prompt
        assert "RFCCpePatchFxp" in prompt


def test_deduplicate_removes_duplicate_chunk_ids():
    chunks = [
        {"chunk_id": "a", "text": "hello world", "metadata": {"source": "f.pdf", "page": 1}},
        {"chunk_id": "a", "text": "hello world", "metadata": {"source": "f.pdf", "page": 1}},
        {"chunk_id": "b", "text": "other text", "metadata": {"source": "f.pdf", "page": 2}},
    ]
    result = deduplicate_and_budget(chunks, max_words=1000)
    assert len(result) == 2
    assert result[0]["chunk_id"] == "a"
    assert result[1]["chunk_id"] == "b"


def test_budget_enforced():
    chunks = [
        {"chunk_id": "a", "text": " ".join(["word"] * 1000), "metadata": {"source": "f.pdf", "page": 1}},
        {"chunk_id": "b", "text": " ".join(["word"] * 1000), "metadata": {"source": "f.pdf", "page": 2}},
        {"chunk_id": "c", "text": " ".join(["word"] * 1000), "metadata": {"source": "f.pdf", "page": 3}},
    ]
    result = deduplicate_and_budget(chunks, max_words=1500)
    assert len(result) == 1


RETRIEVED_CHUNKS_FOR_VALIDATION = [
    {"chunk_id": "trm_001", "text": "RFCCpePatchFxp must be called before RF_open. The CC2652R7 supports +20 dBm output power.", "metadata": {}},
]

def test_validate_answer_grounded():
    answer = "Call RFCCpePatchFxp before RF_open to initialize the RF core."
    result = validate_answer(answer, RETRIEVED_CHUNKS_FOR_VALIDATION)
    assert result["grounded"] == True
    assert result["ungrounded_literals"] == []
    assert result["warning"] is None

def test_validate_answer_ungrounded_hex():
    answer = "Set register at 0x40044000 to enable RF core."
    result = validate_answer(answer, RETRIEVED_CHUNKS_FOR_VALIDATION)
    assert result["grounded"] == False
    assert "0x40044000" in result["ungrounded_literals"]
    assert result["warning"] is not None

def test_validate_answer_no_chunks():
    result = validate_answer("some answer", [])
    assert result["grounded"] == False
    assert result["warning"] is not None

def test_validate_answer_returns_required_keys():
    result = validate_answer("answer", RETRIEVED_CHUNKS_FOR_VALIDATION)
    assert "grounded" in result
    assert "ungrounded_literals" in result
    assert "checked_literals" in result
    assert "warning" in result


def test_check_answerability_matches_voltage_terms_with_hyphenated_units():
    chunks = [
        {
            "chunk_id": "datasheet_hier_chunk_0000",
            "text": "1.8-V to 3.8-V single supply voltage",
            "metadata": {},
        }
    ]

    result = check_answerability("1.8V to 3.8V", chunks)

    assert result["answerable"] is True
    assert result["missing_terms"] == []


def test_check_answerability_matches_voltage_terms_with_spaces_and_hyphens():
    chunks = [
        {
            "chunk_id": "datasheet_hier_chunk_0000",
            "text": "Recommended operating range: 1.8-V minimum, 3.8-V maximum.",
            "metadata": {},
        }
    ]

    result = check_answerability("1.8 V minimum and 3.8 V maximum", chunks)

    assert result["answerable"] is True
    assert result["missing_terms"] == []


def test_generate_answer_names_lte_or_cellular_as_combined_unsupported_feature():
    answer = generate_answer(
        "Does the CC2652R7 support LTE or cellular connectivity?",
        [DATASHEET_FEATURE_CHUNK],
    )

    assert "ANSWER: No" in answer
    assert "LTE or cellular connectivity" in answer
    assert "SOURCE: datasheet_hier_chunk_0000" in answer
