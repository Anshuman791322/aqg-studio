"""API endpoints for document upload initiation, completion, processing, knowledge analysis, and chunk retrieval."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.knowledge_agent import KnowledgeAnalysisAgent
from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.core.errors import NotFoundException, ValidationException
from app.db.session import get_db
from app.knowledge.schemas import (
    ConceptSchema,
    KeyFactSchema,
    KnowledgeAnalysis,
    LearningObjectiveSchema,
    TopicSchema,
)
from app.models.entities import Concept, LearningObjective, Topic
from app.orchestration.runner import job_runner
from app.orchestration.schemas import JobStatusResponse
from app.repositories.chunk import chunk_repo
from app.repositories.document import document_repo
from app.repositories.job import job_repo
from app.retrieval.schemas import RetrievalRequest, RetrievalResponse
from app.retrieval.service import HybridRetrievalService
from app.schemas.common import SuccessResponse
from app.schemas.document import (
    DocumentChunkData,
    DocumentInitiateRequest,
    DocumentInitiateResponse,
    DocumentResponseData,
)
from app.services.document_processor import document_processor
from app.services.storage import delete_file_from_storage

settings = get_settings()
router = APIRouter()
knowledge_agent = KnowledgeAnalysisAgent()
retrieval_service = HybridRetrievalService()


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


@router.post("/{document_id}/process", response_model=SuccessResponse[JobStatusResponse])
async def process_document(
    document_id: uuid.UUID,
    file: UploadFile | None = File(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[JobStatusResponse]:
    """Enqueue an asynchronous PostgreSQL background job for document parsing, chunking, embeddings, and analysis."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    doc = await document_repo.get_by_id(db, id=document_id, user_id=current_user.user_id)
    if not doc:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    initial_state: dict[str, Any] = {
        "document_id": str(document_id),
        "user_id": str(current_user.user_id),
        "filename": doc.original_filename,
        "storage_path": doc.storage_path,
        "mime_type": doc.mime_type,
    }

    if file is not None:
        content_bytes = await file.read()
        if content_bytes:
            initial_state["raw_bytes"] = content_bytes
            initial_state["filename"] = file.filename or doc.original_filename
            initial_state["mime_type"] = file.content_type or doc.mime_type

    job = await job_runner.enqueue_job(
        db,
        user_id=current_user.user_id,
        resource_type="document",
        resource_id=document_id,
        job_type="document_processing",
        initial_state=initial_state,
    )

    data = JobStatusResponse(
        job_id=job.id,
        resource_type=job.resource_type,
        resource_id=job.resource_id,
        job_type=job.job_type,
        status=job.status,
        progress=float(job.progress),
        current_step=job.current_step,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        locked_at=job.locked_at,
        heartbeat_at=job.heartbeat_at,
        state=dict(job.state or {}),
    )
    return SuccessResponse(data=data)


@router.get("/{document_id}/status", response_model=SuccessResponse[JobStatusResponse])
async def get_document_status(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[JobStatusResponse]:
    """Retrieve background processing status, progress percentage, and current step for a document."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    doc = await document_repo.get_by_id(db, id=document_id, user_id=current_user.user_id)
    if not doc:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    # Find active or most recent job
    job = await job_repo.get_active_job(
        db,
        resource_type="document",
        resource_id=document_id,
        user_id=current_user.user_id,
    )
    if not job:
        history = await job_repo.list_by_resource(
            db, resource_id=document_id, user_id=current_user.user_id
        )
        job = history[0] if history else None

    if not job:
        # Generate synthetic status reflecting document table state
        data = JobStatusResponse(
            job_id=uuid.uuid4(),
            resource_type="document",
            resource_id=document_id,
            job_type="document_processing",
            status="completed" if doc.status == "ready" else doc.status,
            progress=100.0 if doc.status == "ready" else 0.0,
            current_step="finalize_document" if doc.status == "ready" else None,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        return SuccessResponse(data=data)

    data = JobStatusResponse(
        job_id=job.id,
        resource_type=job.resource_type,
        resource_id=job.resource_id,
        job_type=job.job_type,
        status=job.status,
        progress=float(job.progress),
        current_step=job.current_step,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        locked_at=job.locked_at,
        heartbeat_at=job.heartbeat_at,
        state=dict(job.state or {}),
    )
    return SuccessResponse(data=data)



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
    """Delete a document, purge associated chunks, and remove remote storage objects."""
    if db is None:
        return SuccessResponse(data={"deleted": True})

    doc = await document_repo.get_by_id(db, id=document_id, user_id=current_user.user_id)
    if not doc:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    # Clean up remote Supabase Storage object
    if doc.storage_path:
        await delete_file_from_storage(
            bucket=settings.SUPABASE_STORAGE_BUCKET_DOCUMENTS,
            path=doc.storage_path,
        )

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


@router.post("/{document_id}/analyze", response_model=SuccessResponse[KnowledgeAnalysis])
async def analyze_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[KnowledgeAnalysis]:
    """Execute knowledge retrieval and pedagogical analysis across document chunks."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    try:
        analysis = await knowledge_agent.analyze_document(
            session=db,
            document_id=document_id,
            user_id=current_user.user_id,
        )
        return SuccessResponse(data=analysis)
    except ValueError as val_err:
        raise NotFoundException(
            message=str(val_err),
            code="DOCUMENT_NOT_FOUND",
        ) from val_err


@router.get("/{document_id}/analysis", response_model=SuccessResponse[KnowledgeAnalysis])
async def get_document_analysis(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[KnowledgeAnalysis]:
    """Retrieve existing persisted knowledge analysis model for a document."""
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

    # Fetch topics with concepts
    topic_stmt = (
        select(Topic)
        .where(Topic.document_id == document_id, Topic.user_id == current_user.user_id)
        .order_by(Topic.importance_score.desc(), Topic.created_at.asc())
    )

    topic_res = await db.execute(topic_stmt)
    topics = list(topic_res.scalars().all())

    # Fetch concepts
    concept_stmt = (
        select(Concept)
        .where(Concept.document_id == document_id, Concept.user_id == current_user.user_id)
    )
    concept_res = await db.execute(concept_stmt)
    concepts = list(concept_res.scalars().all())
    concepts_by_topic: dict[uuid.UUID, list[Concept]] = {}
    for c in concepts:
        concepts_by_topic.setdefault(c.topic_id, []).append(c)

    # Fetch objectives
    obj_stmt = (
        select(LearningObjective)
        .where(
            LearningObjective.document_id == document_id,
            LearningObjective.user_id == current_user.user_id,
        )
        .order_by(LearningObjective.created_at.asc())
    )
    obj_res = await db.execute(obj_stmt)
    objectives = list(obj_res.scalars().all())

    # Reconstruct KnowledgeAnalysis
    topic_schemas: list[TopicSchema] = []
    total_concepts = 0

    for t in topics:
        c_list: list[ConceptSchema] = []
        for c in concepts_by_topic.get(t.id, []):
            c_meta = dict(c.metadata_ or {})
            c_source_ids = [uuid.UUID(sid) for sid in c_meta.get("source_chunk_ids", [])]
            c_list.append(
                ConceptSchema(
                    name=c.name,
                    definition=c.definition or "",
                    importance_score=float(c_meta.get("importance_score", 1.0)),
                    difficulty=c.difficulty if c.difficulty in ("easy", "medium", "hard") else "medium",  # type: ignore[arg-type]
                    source_chunk_ids=c_source_ids or [t.id],
                )
            )
        total_concepts += len(c_list)

        t_meta = dict(t.metadata_ or {})
        t_source_ids = [uuid.UUID(sid) for sid in t_meta.get("source_chunk_ids", [])]

        topic_schemas.append(
            TopicSchema(
                name=t.name,
                description=t.description,
                importance_score=float(t.importance_score),
                order_index=int(t_meta.get("order_index", 0)),
                concepts=c_list,
                source_chunk_ids=t_source_ids or [t.id],
            )
        )

    obj_schemas: list[LearningObjectiveSchema] = []
    for o in objectives:
        o_meta = dict(o.metadata_ or {})
        o_source_ids = [uuid.UUID(sid) for sid in o_meta.get("source_chunk_ids", [])]
        obj_schemas.append(
            LearningObjectiveSchema(
                bloom_level=o.bloom_level,  # type: ignore[arg-type]
                description=o.description,
                topic_name=None,
                source_chunk_ids=o_source_ids or [o.id],
            )
        )

    doc_meta = dict(doc.metadata_ or {}).get("knowledge_analysis", {})

    key_fact_schemas: list[KeyFactSchema] = []
    for f in doc_meta.get("key_facts", []):
        f_source_ids = [uuid.UUID(sid) for sid in f.get("source_chunk_ids", [])]
        key_fact_schemas.append(
            KeyFactSchema(
                fact=f.get("fact", ""),
                importance_score=float(f.get("importance_score", 1.0)),
                source_chunk_ids=f_source_ids or [document_id],
            )
        )

    analysis = KnowledgeAnalysis(
        document_id=document_id,
        analysis_version=doc_meta.get("analysis_version", "1.0.0"),
        summary=doc_meta.get("summary", ""),
        estimated_difficulty="medium",
        topics=topic_schemas,
        learning_objectives=obj_schemas,
        key_facts=key_fact_schemas,
        total_topics=len(topic_schemas),
        total_concepts=total_concepts,
        total_objectives=len(obj_schemas),
        provider_metadata=doc_meta.get("provider_metadata", {}),
    )
    return SuccessResponse(data=analysis)



@router.post("/{document_id}/retrieve", response_model=SuccessResponse[RetrievalResponse])
async def retrieve_document_chunks(
    document_id: uuid.UUID,
    payload: RetrievalRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[RetrievalResponse]:
    """Execute scoped vector/hybrid chunk retrieval over document chunks."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    # Verify document ownership first
    doc = await document_repo.get_by_id(db, id=document_id, user_id=current_user.user_id)
    if not doc:
        raise NotFoundException(
            message=f"Document '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
        )

    retrieved = await retrieval_service.retrieve(
        session=db,
        user_id=current_user.user_id,
        document_id=document_id,
        query=payload.query,
        top_k=payload.top_k,
        section_filter=payload.section_filter,
        alpha=payload.alpha,
    )

    data = RetrievalResponse(
        document_id=document_id,
        query=payload.query,
        total_retrieved=len(retrieved),
        chunks=retrieved,
    )
    return SuccessResponse(data=data)
