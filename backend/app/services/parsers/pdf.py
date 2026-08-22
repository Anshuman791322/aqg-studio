"""Deterministic PDF parser using PyMuPDF (fitz)."""

from collections import Counter

import fitz

from app.services.cleaner import (
    dehyphenate_text,
    detect_language,
    normalize_whitespace,
)
from app.services.parsers.base import BaseDocumentParser, ParsedDocument, ParsedSection


class PDFDocumentParser(BaseDocumentParser):
    """PyMuPDF-based parser extracting structured text, sections, and page metadata."""

    def parse(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        # Validate PDF signature / magic bytes
        if not content_bytes.startswith(b"%PDF-"):
            return ParsedDocument(
                error_code="INVALID_FILE_SIGNATURE",
                error_message="The uploaded file does not contain a valid PDF binary signature.",
            )

        try:
            doc = fitz.open(stream=content_bytes, filetype="pdf")
        except Exception as e:
            return ParsedDocument(
                error_code="CORRUPTED_FILE",
                error_message=f"Failed to open PDF document: {str(e)}",
            )

        if doc.is_encrypted or doc.needs_pass:
            doc.close()
            return ParsedDocument(
                is_encrypted=True,
                error_code="DOCUMENT_ENCRYPTED",
                error_message=(
                    "Password-protected or encrypted PDFs cannot be processed. "
                    "Please upload an unprotected file."
                ),
            )

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            return ParsedDocument(
                page_count=0,
                error_code="EMPTY_DOCUMENT",
                error_message="The uploaded PDF contains no pages.",
            )

        raw_page_texts: list[str] = []
        top_lines: list[str] = []
        bottom_lines: list[str] = []

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text") or ""
            raw_page_texts.append(text)

            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if lines:
                top_lines.append(lines[0])
                bottom_lines.append(lines[-1])

        # Detect repeated running headers and footers across pages
        repeated_headers: set[str] = set()
        repeated_footers: set[str] = set()

        if page_count >= 3:
            threshold = max(2, int(page_count * 0.4))
            for line, count in Counter(top_lines).items():
                if count >= threshold and len(line) >= 3:
                    repeated_headers.add(line)

            for line, count in Counter(bottom_lines).items():
                if count >= threshold and len(line) >= 3:
                    repeated_footers.add(line)

        sections: list[ParsedSection] = []
        total_extracted_chars = 0
        all_cleaned_pages: list[str] = []

        for page_num, raw_text in enumerate(raw_page_texts, start=1):
            lines = raw_text.split("\n")
            filtered_lines: list[str] = []

            for line in lines:
                s_line = line.strip()
                if not s_line:
                    filtered_lines.append("")
                    continue
                # Strip detected repeated header/footer
                if s_line in repeated_headers or s_line in repeated_footers:
                    continue
                filtered_lines.append(line)

            page_content = "\n".join(filtered_lines)
            page_cleaned = normalize_whitespace(dehyphenate_text(page_content))
            total_extracted_chars += len(page_cleaned)
            all_cleaned_pages.append(page_cleaned)

            if page_cleaned:
                sections.append(
                    ParsedSection(
                        title=f"Page {page_num}",
                        content=page_cleaned,
                        page_start=page_num,
                        page_end=page_num,
                        level=1,
                    )
                )

        doc.close()

        # Scanned PDF detection heuristic: text density < 60 chars/page
        avg_chars_per_page = total_extracted_chars / page_count if page_count > 0 else 0
        if avg_chars_per_page < 60:
            return ParsedDocument(
                sections=[],
                page_count=page_count,
                word_count=0,
                language="en",
                raw_text="",
                is_scanned=True,
                error_code="NEEDS_OCR",
                error_message=(
                    "The uploaded PDF contains insufficient extractable text (scanned document). "
                    "Please provide a text-searchable PDF."
                ),
            )

        full_raw_text = "\n\n".join(p for p in all_cleaned_pages if p)
        word_count = len(full_raw_text.split())
        language = detect_language(full_raw_text)

        return ParsedDocument(
            sections=sections,
            page_count=page_count,
            word_count=word_count,
            language=language,
            raw_text=full_raw_text,
            is_scanned=False,
            metadata={
                "parser": "PyMuPDF",
                "repeated_headers_removed": list(repeated_headers),
                "repeated_footers_removed": list(repeated_footers),
            },
        )
