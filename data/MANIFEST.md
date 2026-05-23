Corpus name: TI CC2652R7 Technical Documentation
Domain: Embedded systems / wireless microcontroller firmware
Source of documents: Texas Instruments (ti.com), public technical documentation
Number of documents: 3
Approximate number of pages / tokens: ~1100 pages / ~2.5M tokens
File types: PDF (2), HTML (1)
License / permission: TI public documentation, freely downloadable
Why this corpus is suitable for RAG: Contains precise hardware specifications,
  register addresses, RF driver API signatures, and patch requirements that a
  baseline LLM consistently gets wrong or confuses with other CC26xx variants.
What kind of questions should the system answer:
  - Firmware debugging ("Why does RF_open() fail?")
  - Hardware specs ("What is the max TX power of CC2652R7?")
  - API usage ("How do I call RFCCpePatchFxp()?")
  - Register-level questions ("What is the address of RFC_PWR_PWMCLKEN?")
  - Comparison ("How does CC2652R7 differ from CC2652R1?")
