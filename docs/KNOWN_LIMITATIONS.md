# AQG Studio - Known Limitations & Operational Considerations

This document outlines the known technical limitations, system boundaries, and operational considerations of AQG Studio when running on zero-cost infrastructure.

---

## 1. Supported Document Formats & Parsing

- **Legacy `.doc` Files Unsupported**: Legacy binary Microsoft Word documents (pre-2007 OLE2 `.doc` format) are not supported. Users must convert files to modern `.docx`, `.pdf`, `.pptx`, or `.txt` before uploading.
- **Scanned PDF Optical Character Recognition (OCR) Deferred**: PDFs containing only rasterized images without an embedded text layer are flagged as `ocr_deferred` and rejected from question generation to avoid hallucination. OCR integration with Tesseract or Vision APIs is scheduled for post-v1 releases.
- **Password-Protected / Encrypted Files**: Encrypted or DRM-locked PDFs and archives cannot be parsed and will return `DOCUMENT_ENCRYPTED`.

---

## 2. Infrastructure & Free-Tier Operational Constraints

- **Render Free-Tier Cold Starts**: Render free web services spin down to sleep after 15 minutes of inactivity. The initial HTTP request after idle may experience a **30–50 second wake-up latency**. Subsequent requests will execute with standard sub-second latency.
- **Low Database Connection Limits**: Supabase free-tier PostgreSQL instances typically provide 15–60 direct database connections. When deploying multiple workers, ensure the **Transaction Pooler** (port `6543`) is configured to avoid connection pool exhaustion.
- **Free Model Gateway Rate Limits & Availability**: OpenRouter Free Tier and NVIDIA NIM models have variable availability, context windows, and upstream RPM/TPM rate limits. The built-in `FallbackLLMGateway` handles failover and exponential backoff, but heavy concurrent loads may experience throttling.
- **Hosting Tier SLA**: Free community hosting (Vercel Hobby, Render Free, Supabase Free) is intended for demonstration, academic research, and low-volume production usage, rather than high-availability mission-critical enterprise workloads.

---

## 3. Pedagogical Quality & Human-in-the-Loop Review

- **Human-in-the-Loop Verification**: While AQG Studio executes automated 10-dimensional evaluation (groundedness, correctness, distractor plausibility, Bloom alignment) and iterative refinement loops, **human educator review is strongly recommended before deploying generated questions into high-stakes examinations or certification tests**.
- **Specialized Mathematical Notation**: Complex mathematical formula proofs or handwritten diagrams in PDF files may require verification in the Review Studio to ensure notation fidelity.

---

## 4. Quota and Boundary Defaults

| Dimension | Default Free Limit | Config Key |
| :--- | :--- | :--- |
| **Max Document Size** | 50 MB | `MAX_DOCUMENT_SIZE_MB` |
| **Max Questions per Assessment** | 50 items | `MAX_QUESTIONS_PER_ASSESSMENT` |
| **Max Assessments per Day** | 10 assessments | `MAX_ASSESSMENTS_PER_DAY` |
| **Burst Rate Limit** | 120 requests/min | `BURST_RATE_LIMIT_PER_MINUTE` |
| **LLM Call Budget per Assessment** | 30 calls | `MAX_LLM_CALLS_PER_ASSESSMENT` |
