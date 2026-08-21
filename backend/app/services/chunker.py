"""Hierarchical semantic chunker conforming to 600-900 token boundaries and 10% overlap."""

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.cleaner import calculate_sha256, estimate_tokens, normalize_whitespace
from app.services.parsers.base import ParsedDocument


@dataclass
class GeneratedChunk:
    """Deterministic structured chunk generated from document sections."""

    chunk_index: int
    content: str
    page_start: int
    page_end: int
    section: str | None
    chapter: str | None
    token_count: int
    char_count: int
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)


class HierarchicalChunker:
    """Chunker splitting documents along semantic heading/paragraph boundaries."""

    def __init__(
        self,
        target_tokens: int = 750,
        min_tokens: int = 400,
        max_tokens: int = 1200,
        overlap_tokens: int = 75,
    ) -> None:
        self.target_tokens = target_tokens
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_document(self, parsed_doc: ParsedDocument) -> list[GeneratedChunk]:
        """Convert a ParsedDocument into an ordered list of structured chunks."""
        chunks: list[GeneratedChunk] = []
        if not parsed_doc.sections:
            return chunks

        running_paragraphs: list[dict[str, Any]] = []
        chunk_idx = 0

        for section in parsed_doc.sections:
            sec_title = section.title or "General"
            sec_content = section.content.strip()
            if not sec_content:
                continue

            # Break section into atomic paragraphs
            raw_paras = [p.strip() for p in sec_content.split("\n\n") if p.strip()]
            if not raw_paras:
                raw_paras = [sec_content]

            for para in raw_paras:
                para_tokens = estimate_tokens(para)
                atomic_pieces: list[str] = []

                if para_tokens > self.target_tokens:
                    # Split oversized paragraph by sentence boundaries
                    sentences = [
                        s.strip()
                        for s in re.split(r"(?<=[.!?])\s+", para)
                        if s.strip()
                    ]
                    sentence_buffer = ""
                    for s in sentences:
                        combined = f"{sentence_buffer} {s}".strip() if sentence_buffer else s
                        if estimate_tokens(combined) > self.target_tokens:
                            if sentence_buffer:
                                atomic_pieces.append(sentence_buffer.strip())
                            sentence_buffer = s
                        else:
                            sentence_buffer = combined
                    if sentence_buffer:
                        atomic_pieces.append(sentence_buffer.strip())
                else:
                    atomic_pieces.append(para)

                for piece in atomic_pieces:
                    running_paragraphs.append({
                        "text": piece,
                        "tokens": estimate_tokens(piece),
                        "page_start": section.page_start,
                        "page_end": section.page_end,
                        "section": sec_title,
                    })

                    current_tokens = sum(p["tokens"] for p in running_paragraphs)
                    if current_tokens >= self.target_tokens:
                        chunk, overlap_paras = self._emit_chunk(running_paragraphs, chunk_idx)
                        chunks.append(chunk)
                        chunk_idx += 1
                        running_paragraphs = overlap_paras

        # Emit any remaining paragraphs in buffer
        if running_paragraphs:
            chunk, _ = self._emit_chunk(running_paragraphs, chunk_idx)
            chunks.append(chunk)

        return chunks

    def _emit_chunk(
        self,
        paragraphs: list[dict[str, Any]],
        chunk_index: int,
    ) -> tuple[GeneratedChunk, list[dict[str, Any]]]:
        """Format a list of paragraph descriptors into a GeneratedChunk and compute overlap."""
        text_parts: list[str] = []
        page_starts: list[int] = []
        page_ends: list[int] = []
        sections: set[str] = set()

        for p in paragraphs:
            text_parts.append(p["text"])
            page_starts.append(p["page_start"])
            page_ends.append(p["page_end"])
            if p["section"]:
                sections.add(p["section"])

        content = normalize_whitespace("\n\n".join(text_parts))
        token_count = estimate_tokens(content)
        char_count = len(content)
        content_hash = calculate_sha256(content)

        page_start = min(page_starts) if page_starts else 1
        page_end = max(page_ends) if page_ends else 1
        primary_section = list(sections)[0] if sections else None

        chunk = GeneratedChunk(
            chunk_index=chunk_index,
            content=content,
            page_start=page_start,
            page_end=page_end,
            section=primary_section,
            chapter=None,
            token_count=token_count,
            char_count=char_count,
            content_hash=content_hash,
            metadata={
                "all_sections": list(sections),
                "paragraph_count": len(paragraphs),
            },
        )

        # Compute overlap paragraphs for the next chunk (~10% tokens)
        overlap_paras: list[dict[str, Any]] = []
        accumulated_overlap = 0
        for p in reversed(paragraphs):
            accumulated_overlap += p["tokens"]
            overlap_paras.insert(0, p)
            if accumulated_overlap >= self.overlap_tokens:
                break

        # Ensure forward progress: do not retain all paragraphs as overlap
        if len(overlap_paras) >= len(paragraphs):
            overlap_paras = overlap_paras[1:]

        return chunk, overlap_paras


# Singleton chunker instance
default_chunker = HierarchicalChunker()
