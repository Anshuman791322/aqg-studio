# AQG Studio - 5-Minute Product Demonstration Guide

This guide provides a structured, step-by-step 5-minute demonstration script for showcasing the core features and educator workflow of AQG Studio.

---

## 1. Preparation & Demo Asset

Ensure your local development servers or live cloud deployment are active:
- Frontend: `http://localhost:3000` (or `https://aqg-studio.vercel.app`)
- Backend: `http://localhost:8000` (or `https://aqg-studio-backend.onrender.com`)

Prepare a sample educational document (such as a 2–5 page PDF chapter on Biology, Economics, or Computer Science).

---

## 2. Five-Minute Demonstration Sequence

```mermaid
journey
    title 5-Minute Educator Journey in AQG Studio
    section Step 1: Sign In
      Visit Landing Page: 5: Educator
      Sign in with Supabase Auth: 5: Educator
    section Step 2: Upload
      Drag-and-drop PDF: 5: Educator
      Verify upload and SHA-256 checksum: 5: AQG Studio
    section Step 3: Knowledge Analysis
      Extract text & chunk hierarchically: 5: AQG Studio
      Inspect topics, concepts & key terms: 5: Educator
    section Step 4: Configure Assessment
      Set question count (e.g. 10 items): 5: Educator
      Adjust MCQ, True/False & Short Answer sliders: 5: Educator
      Set Bloom cognitive distribution: 5: Educator
    section Step 5: Generation
      Click Generate Assessment: 5: Educator
      Observe orchestrated LangGraph progress: 5: AQG Studio
    section Step 6: Review Studio
      Inspect generated questions & distractor rationales: 5: Educator
      Inspect verbatim source chunk citations: 5: Educator
      Approve / Edit item: 5: Educator
    section Step 7: Export
      Select PDF with Answer Key: 5: Educator
      Download publication-ready test paper: 5: Educator
```

---

### Step 1: Sign In (0:00 - 0:45)
1. Open the landing page (`/`).
2. Highlight the feature overview: Grounded Question Generation, 10-Dimensional Quality Evaluation, and Publication-Ready Exports.
3. Click **"Get Started"** or **"Sign In"** (`/login`) to authenticate via Supabase Auth.
4. You will be redirected to the **Dashboard** (`/dashboard`).

### Step 2: Upload Educational Material (0:45 - 1:30)
1. Click **"Upload Document"** or navigate to `/documents/new`.
2. Drag and drop your sample PDF, DOCX, PPTX, or TXT file into the upload dropzone.
3. Observe real-time client-side format checks (magic bytes, size validation).
4. Click **"Process Document"** to upload directly to user-scoped Supabase Storage.

### Step 3: Ingestion & Knowledge Exploration (1:30 - 2:15)
1. Upon upload completion, navigate to the Document Details page (`/documents/[id]`).
2. Point out:
   - Extracted document metadata (page count, total word count, checksum).
   - **Extracted Knowledge Topics & Concepts**: Importance scores, learning objectives, and hierarchical concept tags mapped to chunk citations.
3. Click **"Create Assessment"** to begin test planning.

### Step 4: Assessment Configuration (2:15 - 3:00)
1. On the assessment configuration page:
   - Give the assessment a title (e.g., *"Midterm Exam: Cellular Biology"*).
   - Set **Total Questions** (e.g., 10 questions).
   - Adjust the **Question Type Distribution** (e.g., 50% MCQ Single-Select, 30% True/False, 20% Short Answer).
   - Adjust **Cognitive Level Distribution** (e.g., Bloom Remember, Understand, Apply).
   - Adjust **Difficulty Distribution** (Easy, Medium, Hard).
2. Point out the real-time exact Hamilton-Hare remainder distribution balance.
3. Click **"Start Generation"**.

### Step 5: Orchestrated Generation & Evaluation (3:00 - 3:45)
1. Watch the live LangGraph execution state progress:
   - `load_assessment` → `retrieve_and_generate_batches` → `evaluate_batches` → `deduplicate` → `finalize_assessment`.
2. The UI automatically displays real-time progress percentage and status notifications without page reloads.

### Step 6: Review Studio & Provenance Verification (3:45 - 4:30)
1. Once completed, navigate into the **Assessment Review Studio** (`/assessments/[id]`).
2. Highlight key provenance features:
   - **Quality Scorecard**: Highlighting groundedness, distractor quality, and cognitive alignment scores.
   - **Source Grounding**: Click on any question to view its exact source page numbers and verbatim excerpts from the source document.
   - **Distractor Rationales**: Clear pedagogical explanations for why each incorrect option is false.
   - **Educator Actions**: Edit question stem, toggle option validity, or mark as Approved.

### Step 7: Multi-Format Export (4:30 - 5:00)
1. Click **"Export Assessment"**.
2. Select **PDF Exam Paper & Answer Key**.
3. Toggle options:
   - *Include Answer Key* (checked)
   - *Include Pedagogical Rationales* (checked)
   - *Shuffle Options with Deterministic Seed* (checked)
4. Click **"Download Export"**.
5. Open the downloaded PDF and showcase the clean typography, structured layout, header branding, and two-pass page numbering (`Page X of Y`).
