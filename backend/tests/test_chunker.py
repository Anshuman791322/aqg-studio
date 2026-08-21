"""Unit tests for hierarchical semantic chunker (600-900 tokens, 10% overlap)."""

from app.services.chunker import HierarchicalChunker
from app.services.parsers.base import ParsedDocument, ParsedSection


def test_chunker_basic_sections() -> None:
    """Verify chunker processes sections and assigns deterministic chunk indices."""
    sections = [
        ParsedSection(
            title="Section 1: Foundations",
            content="This is the foundational theory of algorithms. " * 30,
            page_start=1,
            page_end=2,
            level=1,
        ),
        ParsedSection(
            title="Section 2: Data Structures",
            content="Binary search trees and hash tables store keyed values. " * 30,
            page_start=3,
            page_end=4,
            level=1,
        ),
    ]
    parsed_doc = ParsedDocument(sections=sections, page_count=4)

    chunker = HierarchicalChunker(
        target_tokens=200, min_tokens=100, max_tokens=400, overlap_tokens=30
    )
    chunks = chunker.chunk_document(parsed_doc)

    assert len(chunks) >= 2
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == idx
        assert chunk.content != ""
        assert chunk.token_count > 0
        assert len(chunk.content_hash) == 64
        assert chunk.page_start >= 1
        assert chunk.page_end <= 4


def test_chunker_empty_document_returns_empty_list() -> None:
    """Verify chunker returns empty list for empty document."""
    parsed_doc = ParsedDocument(sections=[], page_count=0)
    chunker = HierarchicalChunker()
    chunks = chunker.chunk_document(parsed_doc)
    assert chunks == []


def test_chunker_large_paragraph_splitting() -> None:
    """Verify oversized paragraphs exceeding max_tokens are split cleanly."""
    long_sentences = ". ".join(
        [
            f"Sentence number {i} provides detailed domain context for students"
            for i in range(100)
        ]
    )
    sections = [
        ParsedSection(
            title="Comprehensive Analysis",
            content=long_sentences,
            page_start=1,
            page_end=1,
            level=1,
        )
    ]
    parsed_doc = ParsedDocument(sections=sections, page_count=1)

    chunker = HierarchicalChunker(
        target_tokens=150, min_tokens=80, max_tokens=300, overlap_tokens=20
    )
    chunks = chunker.chunk_document(parsed_doc)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count > 0
        assert chunk.token_count <= 400
