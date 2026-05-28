# RAG Failure Case Study: When the Answer Exists in the Corpus

This note explains a failure mode from this project where the answer is explicitly present in the indexed data, but the RAG system still fails. This is different from the RF API failures, where the required RF Driver API Reference is missing from the corpus.

The important lesson is:

> Having the answer somewhere in the corpus is not enough. A RAG system must retrieve the right evidence, rank it above misleading evidence, parse it correctly, and generate the answer in the format expected by the evaluator.

## Concrete Failure From This Project

Evaluation question:

```text
What is the RF transmit power in standard mode (without PA) for CC2652R7?
```

Gold answer:

```text
+5 dBm in standard mode
```

System answer:

```text
The RF transmit power in standard mode (without PA) for CC2652R7 is not directly stated.
However, the document does mention that CMD_SET_TX20_POWER sets the transmit power of the
20 dBm PA, and the value to write to the bias control field of the PA is specified as 6-7 bits.
```

Retrieved sources:

```text
trm_hier_chunk_0584
trm_hier_chunk_2119
trm_hier_chunk_0572
trm_hier_chunk_0573
trm_hier_chunk_0568
```

The failure is real because the answer does appear in the indexed corpus, but the system retrieved nearby RF-power material from the TRM instead of the datasheet evidence.

## Where the Correct Answer Appears

The datasheet chunk `datasheet_hier_chunk_0001_sub0` contains the answer directly:

```text
The CC2652R7 supports +5 dBm TX at 9.7 mA in the 2.4-GHz band.
```

The datasheet chunk `datasheet_hier_chunk_0030` also supports the same answer through Table 7-1:

```text
Table 7-1. Typical TX Current and Output Power
TX Power Setting (SmartRF Studio) 5
Typical Output Power [dBm] 4.8
Typical Current Consumption [mA] 10
```

So the system had enough information in the corpus to answer approximately `+5 dBm`.

## Why It Failed Anyway

The question uses the phrase:

```text
standard mode (without PA)
```

That exact phrase does not appear in the datasheet evidence. The datasheet expresses the answer as:

```text
+5 dBm TX at 9.7 mA
```

and as a table row where the power setting is `5` and the typical measured output is `4.8 dBm`.

The retriever therefore had to connect several ideas:

- "standard mode" means the normal non-20-dBm transmit path.
- "without PA" means do not use the high-power PA command path.
- `+5 dBm TX` and `4.8 dBm typical output power` are the datasheet evidence for that mode.

Instead, retrieval was attracted to TRM chunks containing words like:

```text
transmit power
20 dBm PA
CMD_SET_TX20_POWER
power mode
RF Core
```

The most misleading retrieved chunk was `trm_hier_chunk_2119`, which describes:

```text
CMD_SET_TX20_POWER: Set Transmit Power of the 20 dBm PA
```

That chunk is semantically close to the query because it contains "transmit power" and "PA", but it answers a different question. The user asked for the standard non-PA transmit power, while the retrieved TRM chunk describes the special 20-dBm PA command.

## Why This Can Beat a Strong RAG System

Strictly speaking, a perfect system with perfect retrieval, perfect table parsing, and perfect domain normalization would answer this question correctly. So this is not impossible in a mathematical sense.

However, it is a failure that a strong generic RAG pipeline can still make. The reason is that standard RAG does not truly understand the hardware design. It ranks chunks by textual or embedding similarity, then asks the model to answer from those chunks.

That creates several weaknesses.

First, retrieval similarity is not the same as answerability. A chunk about `CMD_SET_TX20_POWER` is very similar to a query about RF transmit power, but it is not the correct evidence for standard transmit power.

Second, negation is hard for retrieval. The phrase "without PA" should reduce the score of 20-dBm PA chunks, but many retrievers still treat "PA" as an important matching term. The wrong chunk can therefore rank higher because it contains the very concept the question is trying to exclude.

Third, the corpus contains multiple meanings of "power". In this project, "power" can mean RF output power, current consumption, power modes, power domains, standby power, PA power control, or TX power setting. A generic retriever can confuse these because they share the same vocabulary.

Fourth, table evidence is fragile after PDF extraction. The table row that maps TX power setting `5` to `4.8 dBm` is present, but it is flattened into text. The model must reconstruct the table relationship correctly. If the row structure is unclear, the evidence becomes less reliable than a normal sentence.

Fifth, the gold answer uses a normalized engineering interpretation. The datasheet says `+5 dBm TX` and the table says `4.8 dBm typical output power`. The gold answer rounds and interprets this as `+5 dBm in standard mode`. That is reasonable, but it requires the system to know that `4.8 dBm typical` supports a `+5 dBm` answer.

## Why This Is Not Just an LLM Mistake

The answer model did not simply hallucinate. It was given the wrong evidence. The retrieved chunks mostly discussed TRM power management and the 20-dBm PA command path.

Once the wrong chunks are supplied, the LLM has limited options:

- It can refuse because the answer is not in the retrieved context.
- It can produce a wrong answer using the PA command chunk.
- It can guess from outside knowledge, which is unsafe for a grounded RAG system.

The safest behavior is to refuse or say the answer is not directly stated. That is what happened. The problem is upstream: the correct datasheet chunks did not make it into the context for this question.

## What This Shows About RAG Evaluation

This case shows that `answer exists in corpus` is weaker than `answer was retrieved and made usable`.

A good evaluation should track at least four separate questions:

```text
1. Does the corpus contain the answer?
2. Did retrieval return the required source chunk in top-k?
3. Did the answer generator use the correct source chunk?
4. Did the final answer match the expected normalized form?
```

For this case:

```text
Corpus contains answer: yes
Correct source retrieved: no
Generator grounded in correct evidence: no
Final answer correct: no
```

This is why source-labeled evaluation is important. Without required source labels, a high Hit@5 score may hide the fact that the answer-bearing chunk was not actually retrieved.

## What Has To Be Done

The fix is not only "use a better LLM". The system needs stronger retrieval and extraction controls for high-risk specification questions.

Recommended improvements:

1. Add required source labels for every gold question.

   For this question, acceptable source chunks should include:

   ```text
   datasheet_hier_chunk_0001_sub0
   datasheet_hier_chunk_0030
   ```

2. Add a TX-power-specific retrieval route.

   Queries containing terms like `TX power`, `transmit power`, `output power`, `dBm`, or `RF transmit` should strongly prefer datasheet electrical specification chunks and TX performance tables before TRM command-reference chunks.

3. Penalize excluded concepts during retrieval or reranking.

   For this question, `without PA` should penalize chunks about:

   ```text
   20 dBm PA
   CMD_SET_TX20_POWER
   high-power PA
   PA bias control
   ```

4. Add table-aware extraction.

   The system should parse Table 7-1 as structured data:

   ```text
   TX Power Setting: 5
   Typical Output Power: 4.8 dBm
   Typical Current Consumption: 10 mA
   ```

   Then the answer generator can round or normalize this to `about +5 dBm`.

5. Separate RF output power from current and power-management terms.

   The index should distinguish:

   ```text
   RF output power
   TX current consumption
   standby power mode
   power domain
   PA command setting
   ```

   These are not interchangeable, even though they all contain the word "power".

6. Add answer validation for numeric specification questions.

   If the question asks for a value in `dBm`, the final answer should be supported by a retrieved quote or table cell that also contains a `dBm` value. A chunk about power domains or PA command fields should not pass validation.

7. Improve query rewriting.

   The query:

   ```text
   RF transmit power in standard mode without PA
   ```

   should be rewritten into search variants such as:

   ```text
   CC2652R7 supports +5 dBm TX
   CC2652R7 typical output power dBm
   CC2652R7 TX current and output power table
   CC2652R7 2.4 GHz TX at 9.7 mA
   ```

## Report-Ready Summary

Some failures occur even when the answer is explicitly present in the indexed corpus. In this project, the datasheet states that the CC2652R7 supports `+5 dBm TX at 9.7 mA`, and Table 7-1 lists a TX power setting of `5` with typical output power of `4.8 dBm`. However, the system failed the question about standard RF transmit power because retrieval selected TRM chunks about `CMD_SET_TX20_POWER` and the `20 dBm PA` path instead of the datasheet TX-power specification. This demonstrates that RAG accuracy depends not only on corpus coverage, but also on retrieval ranking, negation handling, table parsing, and domain-specific normalization. The required fix is to label source chunks, add TX-power-specific retrieval and table extraction, penalize excluded PA evidence, and validate numeric answers against retrieved `dBm` evidence.
