"""API endpoints for document upload initiation, completion, processing, and chunk retrieval."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.errors import NotFoundException, ValidationException
from app.db.session import get_db
from app.repositories.chunk import chunk_repo
from app.repositories.document import document_repo
from app.schemas.common import SuccessResponse
from app.schemas.document import (
    DocumentChunkData,
    DocumentInitiateRequest,
    DocumentInitiateResponse,
    DocumentResponseData,
)
from app.services.document_processor import document_processor

router = APIRouter()


@router.post("/initiate", response_model=SuccessResponse[DocumentInitiateResponse])
async def initiate_document_upload(
    payload: DocumentInitiateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[DocumentInitiateResponse]:
    """Initiate a document upload record and obtain target private storage path."""
    doc_id, storage_path = await document_processor.initiate_upload(
        db=db,
        user_id=current_user.user_id,
        original_filename=payload.original_filename,
        declared_mime_type=payload.declared_mime_type,
        size_bytes=payload.size_bytes,
    )

    data = DocumentInitiateResponse(
        document_id=doc_id,
        storage_path=storage_path,
        upload_bucket="source-documents",
    )
    return SuccessResponse(data=data)


@router.post("/{document_id}/complete", response_model=SuccessResponse[DocumentResponseData])
async def complete_document_upload(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[DocumentResponseData]:
    """Confirm direct client upload completion to private Storage."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    doc = await document_processor.complete_upload(
        db=db,
        user_id=current_user.user_id,
        document_id=document_id,
    )
    if not doc:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    return SuccessResponse(data=DocumentResponseData.model_validate(doc))


@router.post("/{document_id}/process", response_model=SuccessResponse[DocumentResponseData])
async def process_document(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[DocumentResponseData]:
    """Process document file bytes, extract text, and generate structured chunks."""
    content_bytes = await file.read()
    if not content_bytes:
        raise ValidationException(
            message="Uploaded file content is empty.",
            code="EMPTY_FILE",
        )

    filename = file.filename or "uploaded_document"
    mime_type = file.content_type

    doc = await document_processor.process_document_bytes(
        db=db,
        user_id=current_user.user_id,
        document_id=document_id,
        raw_bytes=content_bytes,
        filename=filename,
        mime_type=mime_type,
    )

    return SuccessResponse(data=DocumentResponseData.model_validate(doc))


@router.get("", response_model=SuccessResponse[list[DocumentResponseData]])
async def list_documents(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[list[DocumentResponseData]]:
    """List all documents owned by the authenticated user."""
    if db is None:
        return SuccessResponse(data=[])

    docs = await document_repo.list_all(
        db,
        user_id=current_user.user_id,
        limit=limit,
        offset=offset,
    )
    data = [DocumentResponseData.model_validate(doc) for doc in docs]
    return SuccessResponse(data=data)


@router.get("/{document_id}", response_model=SuccessResponse[DocumentResponseData])
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[DocumentResponseData]:
    """Retrieve metadata and processing status for a single document."""
    if db is None:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    doc = await document_repo.get_by_id(db, id=document_id, user_id=current_user.user_id)
    if not doc:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    return SuccessResponse(data=DocumentResponseData.model_validate(doc))


@router.delete("/{document_id}", response_model=SuccessResponse[dict[str, bool]])
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[dict[str, bool]]:
    """Delete a document and all associated chunks."""
    if db is None:
        return SuccessResponse(data={"deleted": True})

    deleted = await document_repo.delete(db, id=document_id, user_id=current_user.user_id)
    if not deleted:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    return SuccessResponse(data={"deleted": True})


@router.get("/{document_id}/chunks", response_model=SuccessResponse[list[DocumentChunkData]])
async def get_document_chunks(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[list[DocumentChunkData]]:
    """Retrieve all structured chunks for a document ordered by chunk_index."""
    if db is None:
        return SuccessResponse(data=[])

    # First verify document ownership
    doc = await document_repo.get_by_id(db, id=document_id, user_id=current_user.user_id)
    if not doc:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    chunks = await chunk_repo.list_by_document(
        db, document_id=document_id, user_id=current_user.user_id
    )
    data = [DocumentChunkData.model_validate(c) for c in chunks]
    return SuccessResponse(data=data)
