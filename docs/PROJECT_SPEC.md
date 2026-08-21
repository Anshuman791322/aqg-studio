# AQG Studio - Comprehensive Product Specification

## 1. Product Mission & Vision
**AQG Studio** (Automated Question Generation Studio) is an AI-orchestrated platform designed to convert raw instructional materials into pedagogically rigorous, source-grounded, and quality-evaluated assessments. 

Traditional AI question generators suffer from hallucinations, vague distractors, uncalibrated cognitive depths, and missing source attribution. AQG Studio resolves these shortcomings through a structured multi-agent pipeline governed by Bloom’s Revised Taxonomy, deterministic vector chunk grounding, automated self-critique, and an intuitive Human-in-the-Loop (HITL) review studio.

---

## 2. Intended Users & Target Personas
1. **Higher Education Faculty & School Educators**: Generate quiz banks, mid-term examinations, and formative check-ins aligned directly with lecture slides and textbook chapters.
2. **Corporate L&D & Compliance Officers**: Generate compliance and onboarding verification assessments from SOPs, policy documents, and training decks.
3. **Test Prep Authors & Instructional Designers**: Rapidly draft high-volume item pools with varied difficulty and cognitive depth, complete with distractor rationales and rubric standards.
4. **Self-Directed Learners**: Upload study notes and textbooks to generate practice flashcards and diagnostic assessments.

---

## 3. Supported Input Formats & Validation Rules

| Format | Extension | Support Status | Extraction Engine |
| :--- | :--- | :--- | :--- |
| **Portable Document Format** | `.pdf` | **Supported (Native Text)** | `pypdf` / `pymupdf` with structural page tagging |
| **Microsoft Word** | `.docx` | **Supported** | `python-docx` (paragraphs, headings, tables) |
| **Microsoft PowerPoint** | `.pptx` | **Supported** | `python-pptx` (slide hierarchy, notes, shape text) |
| **Plain Text & Markdown** | `.txt`, `.md` | **Supported** | Native UTF-8 parsing with header segmentation |
| **Legacy Microsoft Word** | `.doc` | **Explicitly Rejected** | Returns 400 Bad Request with actionable user instructions: *"Legacy binary .doc files are not supported in AQG Studio MVP. Please open your document in Microsoft Word, LibreOffice, or Google Docs and save it as modern .docx format before uploading."* |
| **Scanned Image-Only PDF** | `.pdf` | **Deferred OCR** | Scanned/image-only PDFs (detected via text-density threshold < 20 printable characters per page across 80%+ of pages) are detected during parsing and flagged with status `OCR_DEFERRED`: *"This PDF appears to be a scanned image without a native text layer. OCR processing is scheduled for a future release. Please upload a searchable PDF or convert it using an external OCR tool."* |

---

## 4. Assessment Dimensions & Categorization

### 4.1 Question Types
1. **Multiple Choice Questions (MCQ - Single Select)**: 1 stem question, exactly 1 correct answer, 3 plausible, non-trivial distractors, and an explanation for why the key is correct and why each distractor is incorrect.
2. **Multiple Choice Questions (MCQ - Multi-Select / Multiple Response)**: 1 stem question, 2 or more correct options, 2 or more plausible distractors.
3. **True / False**: 1 factual or conceptual assertion, correct binary truth value, reference citation, and explanatory context.
4. **Short Answer (Objective / Fill-in-the-blank)**: Concise question requiring a 1-to-3 sentence answer or specific key terminology, accompanied by acceptable alternative synonyms.
5. **Descriptive / Long Answer**: Open-ended analytical question accompanied by a structured grading rubric (Key Concepts Required, Partial Credit Rules, Exemplary Answer).

### 4.2 Difficulty Levels
- **Easy**: Tests direct recall, basic definitions, explicit facts directly stated in single sentences.
- **Medium**: Tests comprehension, comparison between two concepts, application of a rule, or inference across adjacent paragraphs.
- **Hard**: Tests multi-concept synthesis, critical analysis, edge-case evaluation, or problem-solving requiring conceptual integration.

### 4.3 Bloom’s Revised Taxonomy Levels
All generated questions must explicitly declare and conform to one of the 6 cognitive domains:
1. **Remember**: Recall facts, terminology, formulas, and baseline concepts (e.g., *Define, List, State, Identify*).
2. **Understand**: Explain ideas, interpret concepts, summarize principles (e.g., *Classify, Describe, Discuss, Explain*).
3. **Apply**: Use information in concrete situations, solve practical scenarios (e.g., *Calculate, Demonstrate, Implement, Solve*).
4. **Analyze**: Break material into constituent parts, distinguish cause/effect, compare/contrast (e.g., *Analyze, Compare, Contrast, Differentiate*).
5. **Evaluate**: Justify a decision, critique an argument, assess validity against criteria (e.g., *Appraise, Critique, Defend, Judge, Validate*).
6. **Create**: Synthesize components into a new whole, design a proposed solution (e.g., *Construct, Design, Formulate, Propose*).

---

## 5. Pedagogical Quality Criteria & Evaluation Metrics
Every question generated by AQG Studio undergoes automated grading across 5 distinct dimensions:
1. **Factual Groundedness (Hallucination Defense)**: Is the question factually supported *only* by the provided source document chunks? Score: 1–5.
2. **Stem Clarity & Unambiguity**: Is the question stem unambiguous, free of grammatical flaws, and clearly structured? Score: 1–5.
3. **Distractor Plausibility & Quality**: For MCQs, are distractors common misconceptions, grammatically parallel to the correct answer, and definitively incorrect? No lazy distractors ("All of the above", "None of the above"). Score: 1–5.
4. **Cognitive & Bloom Alignment**: Does the question legitimately target the intended Bloom level and difficulty tier? Score: 1–5.
5. **Fairness & Bias Neutrality**: Is the question free of regional, cultural, or linguistic bias not present in the source text? Score: 1–5.

Questions scoring below an aggregate threshold (e.g., < 4.0 / 5.0 or < 3.5 in Groundedness) are automatically routed back to the Generation Agent with feedback annotations for iterative refinement (up to 2 retry attempts).

---

## 6. Source Traceability & Citation Granularity
Every question retains an immutable provenance trace:
- **`chunk_id`**: UUID of the specific text chunk(s) stored in pgvector.
- **`page_number`**: Page index (1-based) for PDFs and DOCX documents.
- **`slide_number`**: Slide index (1-based) for PPTX decks.
- **`verbatim_excerpt`**: The exact 1–3 sentence text excerpt from the document that verifies the question's premise and answer key.
- **`character_offsets`**: Start and end character offsets within the raw chunk.

---

## 7. Human-in-the-Loop (HITL) Review Workflow
Generated questions are placed in a `DRAFT` or `PENDING_REVIEW` state. Users have full control to:
- Review the question stem, options, correct answer, explanation, and cited source chunk side-by-side.
- Edit stems, tweak distractors, adjust points, and modify Bloom classifications.
- Request targeted AI single-item regeneration (e.g., *"Make distractors more challenging"* or *"Rephrase stem for 10th-grade reading level"*).
- Approve (`APPROVED`), Reject (`REJECTED`), or Flag (`FLAGGED`) individual questions.
- Publish final assessment bundles to LMS export formats.

---

## 8. MVP Operational Limits & Budgets (Free Tier Enforced)

| Parameter | MVP Constraint | Rationale / Enforcement |
| :--- | :--- | :--- |
| **Max File Upload Size** | **50 MB** | Enforces reasonable processing time on serverless backend |
| **Max Pages per Document** | **100 pages** | Prevents memory exhaustion during PDF tree parsing |
| **Max Slides per Deck** | **50 slides** | Prevents rate limits on PPTX slide analysis |
| **Max Questions per Job** | **50 questions** | Balances LLM rate limits and token budgets |
| **Default Chunk Size** | **512 tokens (~1800 chars)** | Optimal granularity for pgvector RAG retrieval |
| **Chunk Overlap** | **64 tokens (~220 chars)** | Preserves contextual continuity across split boundaries |
| **Max Refinement Retries** | **2 attempts per item** | Prevents runaway LLM spend and loop execution |
| **LLM Call Timeout** | **60 seconds per agent call** | FastAPI async timeout guard |
| **Export Formats (MVP)** | JSON, CSV, PDF, DOCX, Moodle XML, GIFT, QTI 2.1 | Industry-standard LMS compatibility |
