"""Document parser exports and factory selector."""

import os

from app.services.parsers.base import BaseDocumentParser, ParsedDocument, ParsedSection
from app.services.parsers.docx import DOCXDocumentParser
from app.services.parsers.pdf import PDFDocumentParser
from app.services.parsers.pptx import PPTXDocumentParser
from app.services.parsers.txt import TXTDocumentParser

MIME_TO_PARSER: dict[str, type[BaseDocumentParser]] = {
    "application/pdf": PDFDocumentParser,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXDocumentParser,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": PPTXDocumentParser,
    "text/plain": TXTDocumentParser,
    "text/markdown": TXTDocumentParser,
}

EXT_TO_PARSER: dict[str, type[BaseDocumentParser]] = {
    ".pdf": PDFDocumentParser,
    ".docx": DOCXDocumentParser,
    ".pptx": PPTXDocumentParser,
    ".txt": TXTDocumentParser,
    ".md": TXTDocumentParser,
}


def get_parser(filename: str, mime_type: str | None = None) -> BaseDocumentParser | None:
    """Select the appropriate parser instance based on MIME type and file extension."""
    if mime_type and mime_type.lower() in MIME_TO_PARSER:
        return MIME_TO_PARSER[mime_type.lower()]()

    _, ext = os.path.splitext(filename.lower())
    if ext in EXT_TO_PARSER:
        return EXT_TO_PARSER[ext]()

    return None


__all__ = [
    "BaseDocumentParser",
    "ParsedDocument",
    "ParsedSection",
    "PDFDocumentParser",
    "DOCXDocumentParser",
    "PPTXDocumentParser",
    "TXTDocumentParser",
    "get_parser",
]
