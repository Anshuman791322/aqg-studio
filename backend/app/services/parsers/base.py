"""Base abstract parser models and interfaces for document extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedSection:
    """Structured section extracted from a document."""

    title: str | None = None
    content: str = ""
    page_start: int = 1
    page_end: int = 1
    level: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Complete structured document extraction result."""

    sections: list[ParsedSection] = field(default_factory=list)
    page_count: int = 1
    word_count: int = 0
    language: str = "en"
    raw_text: str = ""
    is_scanned: bool = False
    is_encrypted: bool = False
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseDocumentParser(ABC):
    """Abstract base class for all document format parsers."""

    @abstractmethod
    def parse(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        """Parse raw document bytes into a structured ParsedDocument."""
        pass
