"""Document ingestion, validation, parsing, and hierarchical chunking coordinator."""

import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.models.entities import Document
from app.repositories.chunk import chunk_repo
from app.repositories.document import document_repo
from app.services.chunker import default_chunker
from app.services.cleaner import calculate_sha256
from app.services.parsers import get_parser
from app.services.storage import build_document_storage_path, sanitize_filename

logger = get_logger("aqg.document_processor")
settings = get_settings()

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/markdown",
}


class DocumentProcessorService:
    """Service orchestrating document lifecycle from initiation to structured chunking."""

    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def validate_upload_parameters(
        self,
        filename: str,
        declared_mime_type: str,
        size_bytes: int,
    ) -> tuple[str, str]:
        """Validate filename extension, MIME type, and size constraints."""
        if not filename or not filename.strip():
            raise ValidationException(
                message="Filename cannot be empty.",
                code="INVALID_FILENAME",
            )

        sanitized_name = sanitize_filename(filename)
        _, ext = os.path.splitext(sanitized_name.lower())

        # Check for explicit legacy .doc format
        if ext == ".doc" or filename.lower().endswith(".doc"):
            raise ValidationException(
                message=(
                    "Legacy .doc format is not supported. "
                    "Please convert your file to .docx or .pdf before uploading."
                ),
                code="UNSUPPORTED_LEGACY_DOC",
            )

        if ext not in SUPPORTED_EXTENSIONS:
            raise ValidationException(
                message=(
                    f"Unsupported file format '{ext}'. Supported formats: "
                    "PDF (.pdf), DOCX (.docx), PPTX (.pptx), TXT (.txt)."
                ),
                code="UNSUPPORTED_FILE_EXTENSION",
            )

        # Validate maximum size limit (default 50MB)
        max_bytes = self.settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
        if size_bytes <= 0:
            raise ValidationException(
                message="File size must be greater than 0 bytes.",
                code="EMPTY_FILE",
            )
        if size_bytes > max_bytes:
            raise ValidationException(
                message=(
                    f"File size exceeds maximum allowed limit of "
                    f"{self.settings.MAX_DOCUMENT_SIZE_MB}MB."
                ),
                code="FILE_TOO_LARGE",
            )

        return sanitized_name, ext

    async def initiate_upload(
        self,
        db: AsyncSession | None,
        user_id: uuid.UUID,
        original_filename: str,
        declared_mime_type: str,
        size_bytes: int,
    ) -> tuple[uuid.UUID, str]:
        """Initiate document record and return required private storage path."""
        sanitized_name, _ = self.validate_upload_parameters(
            original_filename, declared_mime_type, size_bytes
        )
        doc_id = uuid.uuid4()
        storage_path = build_document_storage_path(user_id, doc_id, sanitized_name)

        if db is not None:
            doc_data = {
                "id": doc_id,
                "user_id": user_id,
                "original_filename": sanitized_name,
                "storage_path": storage_path,
                "mime_type": declared_mime_type,
                "size_bytes": size_bytes,
                "status": "pending",
                "checksum": None,
            }
            await document_repo.create(db, obj_in=doc_data, user_id=user_id)

        return doc_id, storage_path

    async def complete_upload(
        self,
        db: AsyncSession | None,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document | None:
        """Confirm direct upload completion and mark document queued for processing."""
        if db is None:
            return None

        doc = await document_repo.get_by_id(db, id=document_id, user_id=user_id)
        if not doc:
            raise NotFoundException(
                message=f"Document '{document_id}' not found.",
                code="DOCUMENT_NOT_FOUND",
            )

        updated = await document_repo.update(
            db,
            id=document_id,
            user_id=user_id,
            obj_in={"status": "queued"},
        )
        return updated

    async def process_document_bytes(
        self,
        db: AsyncSession | None,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        raw_bytes: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> Document:
        """Idempotently parse raw bytes, generate structured chunks, and persist results."""
        checksum = calculate_sha256(raw_bytes)
        parser = get_parser(filename, mime_type)

        if parser is None:
            error_data = {
                "status": "failed",
                "error_code": "UNSUPPORTED_PARSER",
                "error_message": f"No compatible parser found for file '{filename}'.",
            }
            if db is not None:
                await document_repo.update(
                    db, id=document_id, user_id=user_id, obj_in=error_data
                )
            raise ValidationException(
                message=f"No compatible parser found for file '{filename}'.",
                code="UNSUPPORTED_PARSER",
            )

        # Parse document
        parsed_doc = parser.parse(raw_bytes, filename)

        if parsed_doc.is_scanned:
            update_data = {
                "status": "needs_ocr",
                "error_code": parsed_doc.error_code or "NEEDS_OCR",
                "error_message": (
                    parsed_doc.error_message or "Scanned document requires OCR."
                ),
                "page_count": parsed_doc.page_count,
                "checksum": checksum,
            }
            if db is not None:
                doc = await document_repo.update(
                    db, id=document_id, user_id=user_id, obj_in=update_data
                )
                if doc:
                    return doc
            return Document(
                id=document_id,
                user_id=user_id,
                original_filename=filename,
                storage_path=f"{user_id}/{document_id}/{filename}",
                mime_type=mime_type or "application/pdf",
                size_bytes=len(raw_bytes),
                **update_data,
            )

        if parsed_doc.error_code or parsed_doc.is_encrypted:
            update_data = {
                "status": "failed",
                "error_code": parsed_doc.error_code or "PROCESSING_FAILED",
                "error_message": (
                    parsed_doc.error_message or "Failed to parse document content."
                ),
                "checksum": checksum,
            }
            if db is not None:
                doc = await document_repo.update(
                    db, id=document_id, user_id=user_id, obj_in=update_data
                )
                if doc:
                    return doc
            return Document(
                id=document_id,
                user_id=user_id,
                original_filename=filename,
                storage_path=f"{user_id}/{document_id}/{filename}",
                mime_type=mime_type or "application/octet-stream",
                size_bytes=len(raw_bytes),
                **update_data,
            )

        # Generate structured hierarchical chunks
        generated_chunks = default_chunker.chunk_document(parsed_doc)

        # Persist chunks and update document state idempotently
        if db is not None:
            # 1. Purge any previous chunks for this document (safe re-processing)
            await chunk_repo.delete_by_document(
                db, document_id=document_id, user_id=user_id
            )

            # 2. Batch insert newly generated chunks
            chunk_entities_data = [
                {
                    "id": uuid.uuid4(),
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "section": c.section,
                    "token_count": c.token_count,
                    "char_count": c.char_count,
                    "content_hash": c.content_hash,
                    "metadata_": c.metadata,
                }
                for c in generated_chunks
            ]
            if chunk_entities_data:
                await chunk_repo.create_batch(
                    db, chunks_in=chunk_entities_data, user_id=user_id
                )

            # 3. Update document status to ready
            doc_update = {
                "status": "ready",
                "page_count": parsed_doc.page_count,
                "word_count": parsed_doc.word_count,
                "language": parsed_doc.language,
                "checksum": checksum,
                "metadata_": {
                    "total_chunks": len(generated_chunks),
                    "parser_metadata": parsed_doc.metadata,
                },
                "error_code": None,
                "error_message": None,
            }
            updated_doc = await document_repo.update(
                db, id=document_id, user_id=user_id, obj_in=doc_update
            )
            if updated_doc:
                return updated_doc

        return Document(
            id=document_id,
            user_id=user_id,
            original_filename=filename,
            storage_path=f"{user_id}/{document_id}/{filename}",
            mime_type=mime_type or "application/octet-stream",
            size_bytes=len(raw_bytes),
            status="ready",
            page_count=parsed_doc.page_count,
            word_count=parsed_doc.word_count,
            language=parsed_doc.language,
            checksum=checksum,
        )


document_processor = DocumentProcessorService()
