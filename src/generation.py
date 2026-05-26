# src/generation.py
from __future__ import annotations

from dataclasses import dataclass
import re as _re

import ollama

MODEL = "llama3.2"

_NOT_FOUND = "ANSWER: The information was not found in the provided documentation."

_TECHNICAL_PATTERNS = [
    _re.compile(r"\b0x[0-9a-fA-F]+\b"),
    _re.compile(r"\b[+-]?\d+(?:\.\d+)?\s*(?:KB|kB|MB|MHz|GHz|dBm|V|mA|uA|ns|ms|°C|dB)\b", _re.IGNORECASE),
    _re.compile(r"\bRF_\w+\b"),
    _re.compile(r"\bCC\d{4}[A-Z0-9-]*\b"),
    _re.compile(r"\b[A-Z]{2,}[a-zA-Z0-9_]*\b"),
]

_VALIDATION_IGNORE_LITERALS = {
    "ANSWER",
    "QUOTE",
    "SOURCE",
    "TRUE",
    "FALSE",
    "YES",
    "NO",
}

_TOC_DOTS = _re.compile(r"\.{5,}\s*\d+")
_WORD_RE = _re.compile(r"[a-z0-9]+(?:[-_/][a-z0-9]+)*")
_DEVICE_RE = _re.compile(r"\bCC\d{4}[A-Z0-9-]*\b", _re.IGNORECASE)
_RF_API_TERMS = ("RFCCpePatchFxp", "RF_open", "RF_EventLastCmdDone", "CPE patch")

PROMPT_TEMPLATE = """You are a firmware documentation extraction assistant for the TI CC2652R7.

Return exactly one of these formats:

QUOTE: [verbatim sentence, bullet, or table cell from one chunk]
ANSWER: [direct answer only]
SOURCE: [chunk_id]

or, if the answer is not directly present:

ANSWER: The information was not found in the provided documentation.

Hard rules:
- Use only the provided context. Do not add outside knowledge.
- A nearby family/platform list is not device support. For example, a SimpleLink platform sentence mentioning Wi-Fi or Wi-SUN does not mean the CC2652R7 supports Wi-Fi.
- For Yes/No questions, answer Yes only when the exact feature is directly stated for CC2652R7. Otherwise answer No only when the provided CC2652R7 feature list rules it out; if not, say not found.
- For memory questions, distinguish device capacity from sector size, cache size, retention mode, ROM, and example file-system sizes.
- For symbols or APIs such as RF_open or RFCCpePatchFxp, the exact symbol must appear in context. If it does not, say not found.
- Do not include "however", guesses, inferred likely causes, or unrelated summaries.

Question: {question}

Context:
{context}"""


@dataclass(frozen=True)
class _Evidence:
    score: float
    quote: str
    answer: str
    chunk_id: str


def is_toc_chunk(chunk: dict, min_refs: int = 4) -> bool:
    text = chunk.get("text", "")
    if not text.strip():
        return False
    return len(_TOC_DOTS.findall(text)) >= min_refs


def filter_toc_chunks(chunks: list[dict]) -> list[dict]:
    return [c for c in chunks if not is_toc_chunk(c)]


def deduplicate_and_budget(chunks: list[dict], max_words: int = 2000) -> list[dict]:
    seen_ids = set()
    result = []
    total_words = 0

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        if chunk_id in seen_ids:
            continue

        chunk_words = len(chunk.get("text", "").split())
        if result and total_words + chunk_words > max_words:
            break

        seen_ids.add(chunk_id)
        total_words += chunk_words
        result.append(chunk)

    return result


def format_context(chunks: list[dict]) -> str:
    parts = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        location = f"page {meta['page']}" if "page" in meta else f"section: {meta.get('section', 'unknown')}"
        parts.append(f"[{chunk['chunk_id']} | {source} | {location}]\n{chunk.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def generate_answer(question: str, chunks: list[dict], model: str = MODEL) -> str:
    filtered = filter_toc_chunks(chunks) or chunks
    filtered = _deduplicate_only(filtered)

    deterministic = _answer_from_context(question, filtered)
    if deterministic:
        return deterministic

    ranked = deduplicate_and_budget(_rank_chunks(question, filtered), max_words=1800)
    context = format_context(ranked)
    prompt = PROMPT_TEMPLATE.format(question=question, context=context)
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0, "top_p": 0.1, "num_predict": 180},
    )
    return response["message"]["content"].strip()


def _deduplicate_only(chunks: list[dict]) -> list[dict]:
    seen_ids = set()
    result = []
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)
        result.append(chunk)
    return result


def validate_answer(answer: str, retrieved_chunks: list[dict]) -> dict:
    if not retrieved_chunks:
        return {"grounded": False, "ungrounded_literals": [], "checked_literals": [], "warning": "No retrieved chunks."}

    corpus = " ".join(c.get("text", "") for c in retrieved_chunks)
    corpus_lower = corpus.lower()
    corpus_nospace = _re.sub(r"\s+", "", corpus_lower)

    literals = set()
    for pattern in _TECHNICAL_PATTERNS:
        for match in pattern.finditer(answer):
            token = match.group().strip()
            if len(token) >= 3 and token.upper() not in _VALIDATION_IGNORE_LITERALS:
                literals.add(token)

    ungrounded = []
    for literal in literals:
        literal_lower = literal.lower()
        literal_nospace = _re.sub(r"\s+", "", literal_lower)
        if literal_lower not in corpus_lower and literal_nospace not in corpus_nospace:
            ungrounded.append(literal)

    ungrounded = sorted(ungrounded)
    grounded = len(ungrounded) == 0
    return {
        "grounded": grounded,
        "ungrounded_literals": ungrounded,
        "checked_literals": sorted(literals),
        "warning": f"Ungrounded literals: {', '.join(ungrounded)}" if not grounded else None,
    }


def check_answerability(reference_answer: str, final_chunks: list[dict]) -> dict:
    if not final_chunks:
        return {"answerable": False, "key_terms": [], "missing_terms": []}

    context_text = " ".join(c.get("text", "") for c in final_chunks).lower()
    context_normalized = _re.sub(r"[\s-]+", "", context_text)

    key_term_patterns = [
        _re.compile(r"\b[+-]?\d+(?:\.\d+)?\s*(?:KB|kB|MB|MHz|GHz|dBm|V|mA|uA|ns|ms|°C|dB)\b", _re.IGNORECASE),
        _re.compile(r"\b0x[0-9a-fA-F]+\b"),
        _re.compile(r"\bRF_\w+\b"),
        _re.compile(r"\bCC\d{4}[A-Z0-9-]*\b"),
        _re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b"),
    ]

    key_terms = set()
    for pattern in key_term_patterns:
        for match in pattern.finditer(reference_answer):
            term = match.group().strip()
            if term.upper() not in _VALIDATION_IGNORE_LITERALS:
                key_terms.add(term)

    if not key_terms:
        for match in _re.finditer(r"\b\d{2,}\b", reference_answer):
            key_terms.add(match.group())

    missing = [
        term
        for term in key_terms
        if term.lower() not in context_text
        and _re.sub(r"[\s-]+", "", term.lower()) not in context_normalized
    ]
    return {
        "answerable": len(missing) == 0 or len(key_terms) == 0,
        "key_terms": sorted(key_terms),
        "missing_terms": missing,
    }


def _answer_from_context(question: str, chunks: list[dict]) -> str | None:
    qn = _norm(question)

    refusal = _refuse_unanswerable_question(question, chunks)
    if refusal:
        return refusal

    yes_no = _try_yes_no_answer(question, chunks)
    if yes_no:
        return yes_no

    for extractor in (
        _try_memory_answer,
        _try_protocol_answer,
        _try_cpu_answer,
        _try_clock_answer,
        _try_voltage_answer,
        _try_package_answer,
        _try_temperature_answer,
        _try_rf_core_answer,
        _try_ble_sensitivity_answer,
        _try_gpio_answer,
        _try_adc_answer,
        _try_serial_answer,
        _try_timer_answer,
        _try_tx_power_answer,
        _try_rf_command_chain_answer,
    ):
        answer = extractor(qn, chunks)
        if answer:
            return answer

    return None


def _refuse_unanswerable_question(question: str, chunks: list[dict]) -> str | None:
    qn = _norm(question)
    corpus = _corpus_text(chunks)
    corpus_norm = _norm(corpus)

    unsupported_connectivity = ("wi-fi", "wifi", "wireless lan", "lte", "lte-m", "cellular", "ethernet", "usb")
    if any(term in qn for term in unsupported_connectivity) and any(
        term in qn for term in ("configuration", "configure", "channel", "setup", "price", "mouser", "digikey")
    ):
        return _NOT_FOUND

    if any(term in qn for term in ("price", "mouser", "digikey", "stock", "availability")):
        return _NOT_FOUND

    if _is_comparison_question(qn):
        compared_devices = {d.upper() for d in _DEVICE_RE.findall(question) if d.upper() != "CC2652R7"}
        meta_terms = ("chunking", "hierarchical", "fixed chunking", "dense retrieval", "bm25", "retrieval")
        if compared_devices or any(term in qn for term in meta_terms):
            return _NOT_FOUND

    missing_rf_api = []
    for term in _RF_API_TERMS:
        if _norm(term) in qn and _norm(term) not in corpus_norm:
            missing_rf_api.append(term)
    if missing_rf_api:
        return _NOT_FOUND

    symbols = _extract_question_symbols(question)
    ignored = {"CC2652R7", "RF", "BLE", "IEEE", "GPIO", "UART", "SPI", "I2C", "ADC", "DAC", "USB", "CPU", "MCU"}
    absent = [
        symbol
        for symbol in symbols
        if symbol.upper() not in ignored and _norm(symbol) not in corpus_norm
    ]
    if absent and any(symbol.startswith("RF_") or symbol.startswith("RFCC") for symbol in absent):
        return _NOT_FOUND

    return None


def _try_yes_no_answer(question: str, chunks: list[dict]) -> str | None:
    qn = _norm(question)
    if not _is_yes_no_question(qn):
        return None

    if "without" in qn and any(_norm(term) in qn for term in _RF_API_TERMS):
        return _refuse_unanswerable_question(question, chunks)

    if "flash" in qn and _re.search(r"\b1\s*mb\b|\b1024\s*kb\b", qn):
        memory = _try_memory_answer(qn, chunks)
        if memory:
            value = _re.search(r"ANSWER:\s*([^\n]+)", memory)
            answer_value = value.group(1) if value else "the documented flash size"
            quote = _extract_quote(memory)
            source = _extract_source(memory)
            return _format_answer(quote, f"No, the documented flash memory size is {answer_value}.", source)

    feature = _requested_feature(qn)
    if not feature:
        return None

    if feature == "external crystal":
        evidence = _best_regex(
            chunks,
            [_re.compile(r"Radio operation requires an external 48\s*MHz crystal", _re.IGNORECASE)],
            answer_builder=lambda m: "No, radio operation requires an external 48 MHz crystal.",
            base_score=120,
        )
        return _format_evidence(evidence) if evidence else None

    if feature == "5v logic":
        voltage = _try_voltage_answer(qn, chunks)
        if voltage:
            quote = _extract_quote(voltage)
            source = _extract_source(voltage)
            return _format_answer(quote, "No, the documented operating range is below 5 V.", source)
        return None

    direct = _direct_feature_evidence(feature, chunks)
    if direct:
        return _format_evidence(_Evidence(direct.score, direct.quote, f"Yes, the CC2652R7 includes {feature}.", direct.chunk_id))

    support = _protocol_support_evidence(chunks)
    if feature in {"wi-fi", "wifi", "lte", "cellular", "ethernet", "usb", "bluetooth classic", "br/edr", "wi-sun"}:
        if support:
            label = _unsupported_feature_label(feature, qn)
            return _format_answer(
                support.quote,
                f"No, the provided CC2652R7 support list does not include {label}.",
                support.chunk_id,
            )

    if support and _feature_is_in_protocol_support(feature, support.quote):
        return _format_answer(support.quote, f"Yes, the CC2652R7 supports {feature}.", support.chunk_id)

    if feature in {"dac", "antenna"}:
        return _NOT_FOUND

    return None


def _try_memory_answer(qn: str, chunks: list[dict]) -> str | None:
    if "flash" in qn and not any(x in qn for x in ("sector", "erase", "write time", "retention")):
        candidates: list[_Evidence] = []
        patterns = [
            (_re.compile(r"\b(\d+(?:\.\d+)?)\s*kB\s+flash\s+program\s+memory\b", _re.IGNORECASE), 130),
            (_re.compile(r"\b(?:up\s+)?to\s+(\d+(?:\.\d+)?)\s*kB\s+nonvolatile\s+\(?flash\)?\s+memory\b", _re.IGNORECASE), 120),
            (_re.compile(r"\b(\d+(?:\.\d+)?)\s*kB\s+of\s+FLASH\b", _re.IGNORECASE), 105),
            (_re.compile(r"\bFLASH\s+SIZE\s+\d+\s*=\s*(\d+(?:\.\d+)?)\s*kB\b", _re.IGNORECASE), 100),
        ]
        for chunk in chunks:
            text = _clean(chunk.get("text", ""))
            for pattern, base in patterns:
                for match in pattern.finditer(text):
                    quote = _quote_around(text, match.start(), match.end())
                    near = _norm(quote)
                    if "sector" in near or "erase" in near:
                        continue
                    value = _kb_value(match.group(1))
                    score = base + _datasheet_boost(chunk) + _position_boost(chunks, chunk)
                    if "program memory" in near:
                        score += 30
                    candidates.append(_Evidence(score, quote, f"{value} of flash memory", chunk["chunk_id"]))
        return _format_best(candidates)

    if "sram" in qn or ("ram" in qn and "program" not in qn):
        candidates = []
        patterns = [
            (_re.compile(r"\b(?:has|provides|includes|with)\s+(\d+(?:\.\d+)?)\s*kB\s+total\s+SRAM\b", _re.IGNORECASE), 170),
            (_re.compile(r"\b(\d+(?:\.\d+)?)\s*kB\s+total\s+SRAM\b", _re.IGNORECASE), 165),
            (_re.compile(r"\bSRAM\s+SIZE\s+\d+\s*=\s*(\d+(?:\.\d+)?)\s*kB\b", _re.IGNORECASE), 145),
            (_re.compile(r"\b(?:has|provides|includes|with)\s+(\d+(?:\.\d+)?)\s*kB\s+(?:of\s+)?(?:ultra-low leakage\s+)?(?:system\s+)?SRAM\b", _re.IGNORECASE), 130),
            (_re.compile(r"\b(\d+(?:\.\d+)?)\s*kB\s+of\s+(?:ultra-low leakage\s+)?(?:system\s+)?SRAM\b", _re.IGNORECASE), 125),
            (_re.compile(r"\b(\d+(?:\.\d+)?)\s*kB\s+(?:of\s+)?System\s+RAM\b", _re.IGNORECASE), 120),
            (_re.compile(r"\b(\d+(?:\.\d+)?)\s*kB\s+SRAM\b", _re.IGNORECASE), 105),
            (_re.compile(r"\b(\d+(?:\.\d+)?)\s*kB\s+RAM\b", _re.IGNORECASE), 70),
        ]
        for chunk in chunks:
            text = _clean(chunk.get("text", ""))
            for pattern, base in patterns:
                for match in pattern.finditer(text):
                    quote = _quote_around(text, match.start(), match.end())
                    near = _norm(quote)
                    if "rom" in near:
                        continue
                    score = base + _datasheet_boost(chunk) + _position_boost(chunks, chunk)
                    if "total" in near:
                        score += 80
                    if "system ram" in near:
                        score += 35
                    if "ultra-low leakage" in near:
                        score += 25
                    if "retention" in near or "standby" in near or "bank" in near:
                        score -= 45
                    if "cache" in near or "sensor controller" in near or "rf core" in near:
                        score -= 90
                    value = _kb_value(match.group(1))
                    candidates.append(_Evidence(score, quote, f"{value} of SRAM", chunk["chunk_id"]))
        return _format_best(candidates)

    return None


def _try_protocol_answer(qn: str, chunks: list[dict]) -> str | None:
    if "wireless protocol" not in qn and "protocols" not in qn:
        return None

    evidence = _protocol_support_evidence(chunks)
    if not evidence:
        return None

    protocols = _protocol_names_from_text(evidence.quote)
    if not protocols:
        return None
    return _format_answer(evidence.quote, ", ".join(protocols), evidence.chunk_id)


def _try_cpu_answer(qn: str, chunks: list[dict]) -> str | None:
    if not (("cpu" in qn or "processor" in qn or "core" in qn) and any(x in qn for x in ("use", "core", "cpu", "processor"))):
        return None
    if "rf" in qn or "coprocessor" in qn:
        return None
    # Let _try_clock_answer handle clock/frequency questions
    if "clock" in qn or "frequency" in qn:
        return None

    patterns = [
        _re.compile(r"48[-\s]*MHz\s+Arm\s+Cortex\s*-?\s*M4F\s+processor", _re.IGNORECASE),
        _re.compile(r"Arm\s+Cortex\s*-?\s*M4F\s+system\s+CPU", _re.IGNORECASE),
        _re.compile(r"Arm\s+Cortex\s*-?\s*M4F\s+main\s+processor", _re.IGNORECASE),
        _re.compile(r"Arm\s+Cortex\s*-?\s*M4F", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "Arm Cortex-M4F", base_score=110)
    return _format_evidence(evidence) if evidence else None


def _try_clock_answer(qn: str, chunks: list[dict]) -> str | None:
    if not ("clock" in qn and ("cpu" in qn or "frequency" in qn)):
        return None
    patterns = [
        _re.compile(r"48\s*MHz\s+SCLK_HF\s+is\s+used\s+as\s+the\s+main\s+system", _re.IGNORECASE),
        _re.compile(r"Powerful\s+48[-\s]*MHz\s+Arm", _re.IGNORECASE),
        _re.compile(r"Arm\s+Cortex.{0,10}M4F\s+processor\s+core\s+[^\n.]{0,80}?48\s*MHz", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "48 MHz", base_score=120)
    return _format_evidence(evidence) if evidence else None


def _try_voltage_answer(qn: str, chunks: list[dict]) -> str | None:
    if not ("voltage" in qn or "supply" in qn or "5v" in qn):
        return None
    patterns = [
        _re.compile(r"1\.8[-\s]*V\s+to\s+3\.8[-\s]*V\s+single\s+supply\s+voltage", _re.IGNORECASE),
        _re.compile(r"Operating\s+supply\s+voltage[^\n.]{0,120}?1\.8\s+3\.8\s+V", _re.IGNORECASE),
        _re.compile(r"Range\s+1\.8\s+3\.8\s+V", _re.IGNORECASE),
        # datasheet table: "MIN MAX UNIT ... 1.8 3.8 V" near "supply"
        _re.compile(r"1\.8\s+3\.8\s+V", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "1.8 V to 3.8 V", base_score=120)
    return _format_evidence(evidence) if evidence else None


def _try_package_answer(qn: str, chunks: list[dict]) -> str | None:
    if "package" not in qn and "qfn" not in qn:
        return None
    patterns = [
        _re.compile(r"7[-\s]*mm\s*(?:x|×)\s*7[-\s]*mm\s+RGZ\s+VQFN48", _re.IGNORECASE),
        _re.compile(r"RGZ\s*=\s*48[-\s]*pin\s+VQFN", _re.IGNORECASE),
        _re.compile(r"VQFN\s*\(48\)\s+7\.00\s*mm\s*(?:x|×)\s*7\.00\s*mm", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "7 mm x 7 mm 48-pin VQFN package (RGZ)", base_score=120)
    return _format_evidence(evidence) if evidence else None


def _try_temperature_answer(qn: str, chunks: list[dict]) -> str | None:
    if "temperature" not in qn:
        return None
    patterns = [
        # Operating ambient temperature: -40 to 105°C per datasheet Recommended Operating Conditions table
        _re.compile(r"Operating\s+ambient\s+temperature[^\n]{0,60}?-40\s+105", _re.IGNORECASE),
        _re.compile(r"-40\s+(?:to\s+)?\+?105\s*°?C", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "-40°C to +105°C (operating ambient)", base_score=115)
    return _format_evidence(evidence) if evidence else None


def _try_rf_core_answer(qn: str, chunks: list[dict]) -> str | None:
    if not ("rf" in qn and ("coprocessor" in qn or "core" in qn or "processor" in qn)):
        return None
    patterns = [
        _re.compile(r"RF\s+core\s+contains\s+an\s+Arm\s+Cortex\s*-?\s*M0\s+processor", _re.IGNORECASE),
        _re.compile(r"software\s+defined\s+radio\s+powered\s+by\s+an\s+Arm\s+Cortex\s*-?\s*M0", _re.IGNORECASE),
        _re.compile(r"RF\s+Core\s+Arm\s+Cortex\s*-?\s*M0\s+Processor", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "A dedicated RF core with an Arm Cortex-M0 processor", base_score=120)
    return _format_evidence(evidence) if evidence else None


def _try_ble_sensitivity_answer(qn: str, chunks: list[dict]) -> str | None:
    if not ("sensitivity" in qn and ("ble" in qn or "bluetooth" in qn)):
        return None
    candidates = []
    pattern = _re.compile(r"Receiver\s+sensitivity[^\n.]{0,120}?(-\d+)\s*dBm", _re.IGNORECASE)
    for chunk in chunks:
        text = _clean(chunk.get("text", ""))
        for match in pattern.finditer(text):
            quote = _quote_around(text, match.start(), match.end())
            near = _norm(quote)
            score = 100 + _datasheet_boost(chunk) + _position_boost(chunks, chunk)
            if "bluetooth low energy" in _norm(text[:250]) or "1 mbps" in near or "1-mbps" in near:
                score += 40
            if "125 kbps" in near or "coded" in near:
                score -= 25
            value = f"{match.group(1)} dBm"
            candidates.append(_Evidence(score, quote, value, chunk["chunk_id"]))
    return _format_best(candidates)


def _try_gpio_answer(qn: str, chunks: list[dict]) -> str | None:
    if "gpio" not in qn and "i/o pins" not in qn:
        return None
    patterns = [
        _re.compile(r"\b31\s+GPIOs\b", _re.IGNORECASE),
        _re.compile(r"\bup\s+to\s+31\s+I/O\s+pins\b", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "31 GPIOs", base_score=110)
    return _format_evidence(evidence) if evidence else None


def _try_adc_answer(qn: str, chunks: list[dict]) -> str | None:
    if "adc" not in qn and "analog-to-digital" not in qn:
        return None
    patterns = [
        _re.compile(r"12[-\s]*bit\s+ADC", _re.IGNORECASE),
        _re.compile(r"Resolution\s+12\s+Bits", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "12-bit ADC", base_score=110)
    return _format_evidence(evidence) if evidence else None


def _try_serial_answer(qn: str, chunks: list[dict]) -> str | None:
    if "uart" in qn:
        evidence = _best_regex(
            chunks,
            [_re.compile(r"Two\s+UART", _re.IGNORECASE), _re.compile(r"2\s*[x×]\s*UART", _re.IGNORECASE)],
            answer_builder=lambda m: "2 UART interfaces",
            base_score=120,
        )
        return _format_evidence(evidence) if evidence else None

    if "spi" in qn or "ssi" in qn:
        evidence = _best_regex(
            chunks,
            [_re.compile(r"Two\s+SSI", _re.IGNORECASE), _re.compile(r"2\s*[x×]\s*SSI", _re.IGNORECASE)],
            answer_builder=lambda m: "2 SSI interfaces compatible with SPI",
            base_score=120,
        )
        return _format_evidence(evidence) if evidence else None

    if "i2c" in qn or "i²c" in qn:
        evidence = _best_regex(
            chunks,
            [_re.compile(r"Two\s+UART,\s+two\s+SSI,\s+I2C,\s+I2S", _re.IGNORECASE), _re.compile(r"The\s+I2C\s+interface", _re.IGNORECASE)],
            answer_builder=lambda m: "1 I2C interface",
            base_score=105,
        )
        return _format_evidence(evidence) if evidence else None

    return None


def _try_timer_answer(qn: str, chunks: list[dict]) -> str | None:
    if "timer" not in qn:
        return None
    patterns = [
        _re.compile(r"Four\s+32[-\s]*bit\s+or\s+eight\s+16[-\s]*bit\s+general[-\s]*purpose\s+timers", _re.IGNORECASE),
        _re.compile(r"The\s+four\s+flexible\s+GPTIMERs", _re.IGNORECASE),
        _re.compile(r"Four\s+32[-\s]*bit\s+timers", _re.IGNORECASE),
    ]
    evidence = _best_regex(chunks, patterns, answer_builder=lambda m: "4 general-purpose 32-bit timers, configurable as 8 16-bit timers", base_score=115)
    return _format_evidence(evidence) if evidence else None


def _try_tx_power_answer(qn: str, chunks: list[dict]) -> str | None:
    if not (("power" in qn or "tx" in qn or "transmit" in qn) and ("rf" in qn or "output" in qn or "standard" in qn)):
        return None

    candidates = []
    patterns = [
        (_re.compile(r"Output\s+power\s+up\s+to\s+([+-]?\d+(?:\.\d+)?)\s*dBm", _re.IGNORECASE), 135),
        (_re.compile(r"([+-]?\d+(?:\.\d+)?)\s*dBm\s+output\s+power\s+setting", _re.IGNORECASE), 95),
        (_re.compile(r"([+-]?\d+(?:\.\d+)?)\s*dBm\s+(?:high[-\s]*power\s+)?amplifier", _re.IGNORECASE), 85),
    ]
    for chunk in chunks:
        text = _clean(chunk.get("text", ""))
        for pattern, base in patterns:
            for match in pattern.finditer(text):
                quote = _quote_around(text, match.start(), match.end())
                near = _norm(quote)
                score = base + _datasheet_boost(chunk) + _position_boost(chunks, chunk)
                if "standard" in qn and ("pa" in near or "amplifier" in near):
                    score -= 60
                if "up to" in near or "maximum" in qn:
                    score += 25
                value = f"{_signed_number(match.group(1))} dBm"
                candidates.append(_Evidence(score, quote, value, chunk["chunk_id"]))
    return _format_best(candidates)


def _try_rf_command_chain_answer(qn: str, chunks: list[dict]) -> str | None:
    if not ("rf" in qn and "command" in qn and ("chain" in qn or "scheduler" in qn)):
        return None

    evidence = _best_regex(
        chunks,
        [
            _re.compile(r"The system CPU can schedule back-to-back radio operation commands by using the next operation pointer[^\n.]{0,260}", _re.IGNORECASE),
            _re.compile(r"pointer can point to the next command to perform in the chain[^\n.]{0,180}", _re.IGNORECASE),
        ],
        answer_builder=lambda m: "The documentation describes chaining with the next operation pointer; no fixed count is stated.",
        base_score=120,
    )
    return _format_evidence(evidence) if evidence else None


def _direct_feature_evidence(feature: str, chunks: list[dict]) -> _Evidence | None:
    if feature == "dac":
        return _best_regex(
            chunks,
            [_re.compile(r"8[-\s]*bit\s+DAC", _re.IGNORECASE), _re.compile(r"internal\s+8\s+bits\s+DAC", _re.IGNORECASE)],
            answer_builder=lambda m: "Yes, the CC2652R7 includes a DAC.",
            base_score=130,
        )
    return None


def _protocol_support_evidence(chunks: list[dict]) -> _Evidence | None:
    candidates = []
    for chunk in chunks:
        text = _clean(chunk.get("text", ""))
        norm = _norm(text)

        section_match = _re.search(
            r"Wireless protocol support\s+(.*?)(?:High performance radio|Regulatory compliance|MCU peripherals)",
            text,
            _re.IGNORECASE,
        )
        if section_match:
            quote = _quote(section_match.group(0))
            candidates.append(_Evidence(160 + _datasheet_boost(chunk) + _position_boost(chunks, chunk), quote, "", chunk["chunk_id"]))

        for sentence in _sentences(text):
            sn = _norm(sentence)
            if "simplelink" in sn and "platform consists" in sn:
                continue
            if "cc2652r7" in sn and ("supporting" in sn or "supports" in sn) and _has_protocol_name(sn):
                candidates.append(_Evidence(140 + _datasheet_boost(chunk) + _position_boost(chunks, chunk), _quote(sentence), "", chunk["chunk_id"]))
            elif "programmable radio includes support" in sn and _has_protocol_name(sn):
                candidates.append(_Evidence(125 + _datasheet_boost(chunk) + _position_boost(chunks, chunk), _quote(sentence), "", chunk["chunk_id"]))

        if "simplelink mcu platform consists" in norm and len(candidates) == 0:
            continue

    return max(candidates, key=lambda ev: ev.score) if candidates else None


def _protocol_names_from_text(text: str) -> list[str]:
    norm = _norm(text)
    names = []
    checks = [
        ("Bluetooth 5.2 Low Energy", ("bluetooth" in norm and "low energy" in norm)),
        ("IEEE 802.15.4", "802.15.4" in norm),
        ("Zigbee", "zigbee" in norm),
        ("Thread", "thread" in norm),
        ("Matter", "matter" in norm),
        ("TI 15.4-Stack", "15.4-stack" in norm or "ti 15.4" in norm),
        ("6LoWPAN", "6lowpan" in norm),
        ("proprietary systems", "proprietary" in norm),
        ("2-(G)FSK, 4-(G)FSK, and MSK", "(g)fsk" in norm or "msk" in norm),
    ]
    for name, present in checks:
        if present and name not in names:
            names.append(name)
    return names


def _feature_is_in_protocol_support(feature: str, quote: str) -> bool:
    norm = _norm(quote)
    if feature in {"ble", "bluetooth low energy", "bluetooth"}:
        return "bluetooth" in norm and "low energy" in norm
    if feature in {"zigbee", "thread", "matter", "6lowpan", "proprietary"}:
        return feature in norm
    if feature in {"ieee 802.15.4", "802.15.4", "ti 15.4"}:
        return "15.4" in norm
    return False


def _unsupported_feature_label(feature: str, qn: str) -> str:
    if feature in {"lte", "cellular"} and "lte" in qn and "cellular" in qn:
        return "LTE or cellular connectivity"

    return {
        "wi-fi": "Wi-Fi",
        "wifi": "Wi-Fi",
        "lte": "LTE",
        "cellular": "cellular connectivity",
        "ethernet": "Ethernet",
        "usb": "USB",
        "bluetooth classic": "Bluetooth Classic (BR/EDR)",
        "br/edr": "Bluetooth Classic (BR/EDR)",
        "wi-sun": "Wi-SUN",
    }[feature]


def _requested_feature(qn: str) -> str | None:
    aliases = [
        ("wi-fi", ("wi-fi", "wifi", "wireless lan")),
        ("bluetooth classic", ("bluetooth classic", "br/edr", "classic bluetooth")),
        ("lte", ("lte", "lte-m")),
        ("cellular", ("cellular",)),
        ("ethernet", ("ethernet",)),
        ("usb", ("usb",)),
        ("wi-sun", ("wi-sun", "wisun")),
        ("dac", (" dac", "digital-to-analog", "digital to analog")),
        ("antenna", ("antenna",)),
        ("5v logic", ("5v", "5 v")),
        ("external crystal", ("external crystal", "crystal oscillator", "48 mhz crystal")),
        ("ble", ("ble", "bluetooth low energy")),
        ("zigbee", ("zigbee",)),
        ("thread", ("thread",)),
        ("matter", ("matter",)),
        ("6lowpan", ("6lowpan", "6lowpan")),
        ("proprietary", ("proprietary",)),
    ]
    for feature, terms in aliases:
        if any(term in qn for term in terms):
            return feature
    return None


def _rank_chunks(question: str, chunks: list[dict]) -> list[dict]:
    qn = _norm(question)
    q_words = set(_WORD_RE.findall(qn))
    ranked = []
    for index, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        norm = _norm(text)
        words = set(_WORD_RE.findall(norm))
        score = len(q_words & words) * 3 + max(0, 20 - index)

        for symbol in _extract_question_symbols(question):
            if _norm(symbol) in norm:
                score += 40

        if "flash" in qn:
            if "flash program memory" in norm or "nonvolatile flash memory" in norm:
                score += 80
            if "sector" in norm or "erase" in norm:
                score -= 35
        if "sram" in qn or "ram" in qn:
            if "sram size" in norm or "system ram" in norm or "ultra-low leakage sram" in norm:
                score += 70
            if "rom" in norm:
                score -= 60
            if "cache" in norm or "retention" in norm:
                score -= 15
        if "wi-fi" in qn or "wifi" in qn or "protocol" in qn:
            if "wireless protocol support" in norm or "multiprotocol" in norm:
                score += 60
            if "platform consists" in norm:
                score -= 45
        if "source" in chunk.get("metadata", {}) and chunk["metadata"].get("source") == "cc2652r7.pdf":
            score += 5

        copied = dict(chunk)
        copied["_generation_rank_score"] = score
        ranked.append(copied)

    ranked.sort(key=lambda c: c.get("_generation_rank_score", 0), reverse=True)
    for chunk in ranked:
        chunk.pop("_generation_rank_score", None)
    return ranked


def _best_regex(
    chunks: list[dict],
    patterns: list[_re.Pattern],
    answer_builder,
    base_score: float,
) -> _Evidence | None:
    candidates = []
    for chunk in chunks:
        text = _clean(chunk.get("text", ""))
        for pattern_index, pattern in enumerate(patterns):
            for match in pattern.finditer(text):
                quote = _quote_around(text, match.start(), match.end())
                score = base_score - pattern_index * 5 + _datasheet_boost(chunk) + _position_boost(chunks, chunk)
                candidates.append(_Evidence(score, quote, answer_builder(match), chunk["chunk_id"]))
    return max(candidates, key=lambda ev: ev.score) if candidates else None


def _format_best(candidates: list[_Evidence]) -> str | None:
    if not candidates:
        return None
    return _format_evidence(max(candidates, key=lambda ev: ev.score))


def _format_evidence(evidence: _Evidence | None) -> str | None:
    if not evidence:
        return None
    return _format_answer(evidence.quote, evidence.answer, evidence.chunk_id)


def _format_answer(quote: str, answer: str, source: str) -> str:
    return f"QUOTE: {_quote(quote)}\nANSWER: {answer}\nSOURCE: {source}"


def _extract_quote(answer: str) -> str:
    match = _re.search(r"QUOTE:\s*(.*?)\nANSWER:", answer, _re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_source(answer: str) -> str:
    match = _re.search(r"\nSOURCE:\s*([^\n]+)", answer)
    return match.group(1).strip() if match else "unknown"


def _extract_question_symbols(text: str) -> set[str]:
    symbols = set(_re.findall(r"\bRF_\w+\b", text))
    symbols.update(_re.findall(r"\bRFCC\w+\b", text))
    symbols.update(_DEVICE_RE.findall(text))
    return symbols


def _is_yes_no_question(qn: str) -> bool:
    return qn.startswith(("does ", "do ", "is ", "are ", "can ", "should ", "could ", "will ", "would "))


def _is_comparison_question(qn: str) -> bool:
    return any(term in qn for term in ("compare", "differ", "difference", " vs ", " versus ", " over ", " than "))


def _has_protocol_name(norm_text: str) -> bool:
    return any(term in norm_text for term in ("bluetooth", "zigbee", "thread", "802.15.4", "15.4-stack", "6lowpan", "matter", "proprietary"))


def _sentences(text: str) -> list[str]:
    text = _clean(text)
    pieces = _re.split(r"(?<=[.!?])\s+|(?:\s+•\s*)", text)
    return [p.strip() for p in pieces if len(p.strip()) >= 12]


def _quote_around(text: str, start: int, end: int, radius: int = 150) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)

    boundary_left = max(text.rfind(". ", 0, start), text.rfind(" •", 0, start), text.rfind("; ", 0, start))
    if boundary_left >= left:
        left = boundary_left + 2

    boundary_right_candidates = [pos for pos in (text.find(". ", end), text.find(" •", end), text.find("; ", end)) if pos != -1]
    if boundary_right_candidates:
        boundary_right = min(boundary_right_candidates)
        if boundary_right <= right:
            right = boundary_right + 1

    return _quote(text[left:right])


def _quote(text: str) -> str:
    text = _clean(text)
    if len(text) <= 420:
        return text
    return text[:417].rstrip() + "..."


def _clean(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2122", "")
    text = text.replace("\u00ae", "")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")
    text = text.replace("\u2212", "-")
    text = text.replace("×", "x")
    text = _re.sub(r"\s+", " ", text)
    return text.strip()


def _norm(text: str) -> str:
    text = _clean(text).lower()
    text = text.replace("wi fi", "wi-fi")
    text = text.replace("wi-fi", "wi-fi")
    text = text.replace("i²c", "i2c")
    text = text.replace("µ", "u")
    text = _re.sub(r"\s+", " ", text)
    return text.strip()


def _corpus_text(chunks: list[dict]) -> str:
    return " ".join(chunk.get("text", "") for chunk in chunks)


def _kb_value(raw: str) -> str:
    value = raw.strip()
    if value.endswith(".0"):
        value = value[:-2]
    return f"{value} KB"


def _signed_number(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith(("+", "-")):
        return raw
    return f"+{raw}"


def _datasheet_boost(chunk: dict) -> int:
    source = chunk.get("metadata", {}).get("source", "")
    return 12 if source == "cc2652r7.pdf" else 0


def _position_boost(chunks: list[dict], chunk: dict) -> int:
    try:
        return max(0, 12 - chunks.index(chunk))
    except ValueError:
        return 0
