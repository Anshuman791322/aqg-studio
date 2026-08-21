"""Deterministic plain text and Markdown parser."""

import re

from app.services.cleaner import (
    dehyphenate_text,
    detect_language,
    normalize_whitespace,
)
from app.services.parsers.base import BaseDocumentParser, ParsedDocument, ParsedSection

SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "cp1252", "latin-1", "iso-8859-1"]


class TXTDocumentParser(BaseDocumentParser):
    """Parser extracting structured text and headings from plain text and Markdown documents."""

    def parse(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        raw_text: str | None = None

        # Attempt decoding across standard encodings
        for enc in SUPPORTED_ENCODINGS:
            try:
                raw_text = content_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if raw_text is None:
            return ParsedDocument(
                error_code="ENCODING_ERROR",
                error_message=(
                    "Failed to decode text file. "
                    "Ensure file is UTF-8, Latin-1, or standard ASCII."
                ),
            )

        cleaned_text = normalize_whitespace(dehyphenate_text(raw_text))
        if not cleaned_text:
            return ParsedDocument(
                page_count=0,
                error_code="EMPTY_DOCUMENT",
                error_message="The uploaded text file is empty.",
            )

        sections: list[ParsedSection] = []
        # Check for Markdown headings: e.g. # Heading, ## Subheading
        lines = cleaned_text.split("\n")
        current_title = "Introduction"
        current_lines: list[str] = []
        current_level = 1

        for line in lines:
            s_line = line.strip()
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", s_line)

            if heading_match:
                if current_lines:
                    sections.append(
                        ParsedSection(
                            title=current_title,
                            content="\n".join(current_lines).strip(),
                            page_start=1,
                            page_end=1,
                            level=current_level,
                        )
                    )
                    current_lines = []
                current_level = len(heading_match.group(1))
                current_title = heading_match.group(2).strip()
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(
                ParsedSection(
                    title=current_title,
                    content="\n".join(current_lines).strip(),
                    page_start=1,
                    page_end=1,
                    level=current_level,
                )
            )

        full_raw_text = "\n\n".join(f"{s.title}\n{s.content}" for s in sections)
        word_count = len(full_raw_text.split())
        language = detect_language(full_raw_text)
        estimated_pages = max(1, (word_count // 350) + 1)

        return ParsedDocument(
            sections=sections,
            page_count=estimated_pages,
            word_count=word_count,
            language=language,
            raw_text=full_raw_text,
            is_scanned=False,
            metadata={"parser": "plain-text"},
        )
