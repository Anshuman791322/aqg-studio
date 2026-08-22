"""Output & Report Agent for deterministic pedagogical metrics and assessment exports."""

import uuid

from app.exports.service import export_service
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundException
from app.core.logging import get_logger
from app.models.entities import Evaluation, Topic
from app.reporting.calculator import calculate_assessment_report
from app.reporting.schemas import (
    AssessmentReportResponse,
    ExportCreateRequest,
    ExportResponse,
)
from app.repositories.assessment import assessment_repo
from app.repositories.blueprint import blueprint_repo
from app.repositories.document import document_repo
from app.repositories.evaluation import evaluation_repo
from app.repositories.export import export_repo
from app.repositories.question import question_repo
from app.repositories.topic import topic_repo

logger = get_logger("app.agents.output_report_agent")


class OutputReportAgent:
    """Agent responsible for assessment analytics, pedagogical quality reports, and exports."""

    async def generate_assessment_report(
        self,
        session: AsyncSession,
        *,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AssessmentReportResponse:
        """Fetch all related entities and calculate deterministic pedagogical report."""
        assessment = await assessment_repo.get_by_id(session, id=assessment_id, user_id=user_id)
        if not assessment:
            raise NotFoundException(
                message=f"Assessment '{assessment_id}' not found.",
                code="ASSESSMENT_NOT_FOUND",
            )

        document = await document_repo.get_by_id(session, id=assessment.document_id, user_id=user_id)
        questions = list(await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id))
        blueprints = list(await blueprint_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id))

        # Retrieve evaluations
        evaluations: list[Evaluation] = []
        for q in questions:
            q_evals = await evaluation_repo.list_by_question(session, question_id=q.id, user_id=user_id)
            evaluations.extend(q_evals)

        # Retrieve document topics
        topics: list[Topic] = []
        if document:
            topics = list(await topic_repo.list_by_document(session, document_id=document.id, user_id=user_id))

        # Retrieve exports
        exports = list(await export_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id))

        report = calculate_assessment_report(
            assessment=assessment,
            document=document,
            questions=questions,
            blueprints=blueprints,
            evaluations=evaluations,
            topics=topics,
            exports=exports,
        )

        logger.info(
            f"Generated assessment report for '{assessment.name}' ({assessment_id}): "
            f"{report.metrics.total_accepted} approved items, overall quality {report.metrics.average_overall_quality}"
        )
        return report

    async def create_export(
        self,
        session: AsyncSession,
        *,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID,
        request: ExportCreateRequest,
    ) -> ExportResponse:
        """Dispatch export generation and persist package."""
        return await export_service.create_assessment_export(
            session,
            assessment_id=assessment_id,
            user_id=user_id,
            request=request,
        )

    async def list_exports(
        self,
        session: AsyncSession,
        *,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ExportResponse]:
        """List all generated export records for an assessment."""
        records = await export_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
        return [
            ExportResponse(
                id=r.id,
                assessment_id=r.assessment_id,
                user_id=r.user_id,
                format=r.format,
                storage_path=r.storage_path,
                configuration=dict(r.configuration or {}),
                status=r.status,
                file_size_bytes=r.file_size_bytes,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ]


output_report_agent = OutputReportAgent()
