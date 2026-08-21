# Phase 4 Handoff: Document Processing Agent & Ingestion

## Summary of Implementation
Phase 4 implements the deterministic **Document Processing Agent** and upload lifecycle for AQG Studio:
1. **Upload Lifecycle**:
   - `POST /api/v1/documents/initiate`: Validates MIME types, extensions (`.pdf`, `.docx`, `.pptx`, `.txt`, `.md`), rejection of legacy `.doc` with conversion guidance, and 50MB file size limits. Generates a document ID and deterministic private Storage path `<user_id>/<document_id>/<sanitized_filename>`.
   - Direct frontend upload to the private `source-documents` bucket under Supabase Storage RLS.
   - `POST /api/v1/documents/{document_id}/complete`: Confirms upload and marks document `queued`.
   - `POST /api/v1/documents/{document_id}/process`: Deterministic ingestion endpoint parsing content bytes, extracting structured sections, running the hierarchical chunker, and persisting chunks and metadata.
2. **Deterministic Format Parsers**:
   - **PDF Parser (`PDFDocumentParser`)**: Uses PyMuPDF (`fitz`), detects password-encrypted files (`DOCUMENT_ENCRYPTED`), removes repeated running headers and footers across pages, and flags scanned/empty PDFs lacking extractable text with status `needs_ocr` (`NEEDS_OCR`).
   - **DOCX Parser (`DOCXDocumentParser`)**: Uses `python-docx`, extracts heading hierarchies and structured tables, guards against zip bombs, and rejects legacy `.doc` binary files.
   - **PPTX Parser (`PPTXDocumentParser`)**: Uses `python-pptx`, maps slide numbers to page boundaries, and extracts titles, text frames, tables, and speaker notes.
   - **TXT / Markdown Parser (`TXTDocumentParser`)**: Decodes standard encodings (UTF-8, Latin-1, CP1252) and detects Markdown heading structures.
3. **Linguistic Cleaning & Language Detection**:
   - Normalizes whitespace and control characters.
   - Conservative dehyphenation merging words split across line breaks.
   - Deterministic stopword-frequency language detector (English, Spanish, French, German, Italian, Portuguese, Hindi).
   - Accurate token counting via `tiktoken` (`cl100k_base`) with character-ratio fallback.
4. **Hierarchical Chunker (`HierarchicalChunker`)**:
   - Enforces target token boundaries (600–900 tokens, max 1,200).
   - Preserves semantic heading and paragraph structures.
   - Applies ~10% overlap (~75 tokens) between adjacent chunks.
   - Computes deterministic SHA-256 `content_hash` and tracks `page_start`, `page_end`, and `section`.
   - Guarantees idempotent replacement of chunks upon re-processing.
5. **Document Retrieval & Lifecycle Endpoints**:
   - `GET /api/v1/documents`: User-scoped document list.
   - `GET /api/v1/documents/{document_id}`: Document metadata and processing status.
   - `GET /api/v1/documents/{document_id}/chunks`: Ordered structured chunk list.
   - `DELETE /api/v1/documents/{document_id}`: Cascading deletion of document and chunks.

## Test Verification
- **Unit & Integration Tests**: 77 backend tests passing (`pytest`).
- **Static Analysis & Types**: Ruff (`0` errors), mypy (`0` errors across 46 files).
- **Frontend Verification**: ESLint (`0` warnings/errors), TypeScript strict typecheck (`0` errors), Jest, and Next.js 15 production build passing across 9 routes.
