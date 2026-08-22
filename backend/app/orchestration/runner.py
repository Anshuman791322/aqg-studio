import asyncio
import contextlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.models.entities import Job
from app.orchestration.assessment_flow import assessment_workflow
from app.orchestration.document_flow import document_workflow
from app.repositories.job import job_repo

logger = get_logger("aqg.orchestration.runner")


class PostgresJobRunner:
    """PostgreSQL transactional background job runner operating inside the FastAPI process."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        poll_interval_seconds: float = 1.0,
        worker_concurrency: int = 1,
    ) -> None:
        self._session_factory = session_factory
        self.poll_interval = poll_interval_seconds
        self.concurrency = worker_concurrency
        self._running = False
        self._worker_task: asyncio.Task[None] | None = None

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession] | None:
        """Return configured or global session factory."""
        if self._session_factory is not None:
            return self._session_factory
        return get_session_factory()

    async def start(self) -> None:
        """Start the background worker and recover any stale running jobs."""
        if self._running:
            return

        self._running = True
        logger.info("Starting PostgresJobRunner worker loop")

        # 1. Recover stale running jobs on startup
        if self.session_factory is not None:
            try:
                async with self.session_factory() as session:
                    await self.recover_stale_running_jobs(session)
            except Exception as exc:
                logger.warning(f"Startup crash recovery encountered error: {exc}")

        # 2. Spawn worker loop task
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        """Gracefully stop the background worker task."""
        if not self._running:
            return

        logger.info("Stopping PostgresJobRunner worker loop")
        self._running = False

        if self._worker_task is not None:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None

    async def recover_stale_running_jobs(self, session: AsyncSession) -> int:
        """Detect stale running jobs from previous process crashes and return them to queued state."""
        stmt = (
            update(Job)
            .where(Job.status == "running")
            .values(
                status="queued",
                locked_at=None,
                heartbeat_at=None,
                updated_at=datetime.now(UTC),
            )
        )
        res = await session.execute(stmt)
        await session.commit()
        count = int(res.rowcount) if hasattr(res, "rowcount") else 0
        if count > 0:
            logger.info(f"Recovered {count} stale running job(s) back to 'queued' state.")
        return count

    async def claim_next_job(self, session: AsyncSession) -> Job | None:
        """Atomically claim the next queued job using PostgreSQL SELECT FOR UPDATE SKIP LOCKED."""
        # Use with_for_update(skip_locked=True) for safe transactional locking
        stmt = (
            select(Job)
            .where(Job.status == "queued")
            .order_by(Job.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        res = await session.execute(stmt)
        job = res.scalar_one_or_none()

        if job is not None:
            job.status = "running"
            job.locked_at = datetime.now(UTC)
            job.heartbeat_at = datetime.now(UTC)
            job.attempts += 1
            await session.commit()
            logger.info(
                f"Claimed job {job.id} (type: {job.job_type}, resource: {job.resource_id})",
                extra={"job_id": str(job.id)},
            )

        return job

    async def _worker_loop(self) -> None:
        """Continuous polling and execution loop."""
        while self._running:
            try:
                if self.session_factory is not None:
                    async with self.session_factory() as session:
                        job = await self.claim_next_job(session)
                        if job is not None:
                            await self.process_job(job.id)
                            continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in background job worker polling loop: {exc}")

            await asyncio.sleep(self.poll_interval)

    async def process_job(self, job_id: uuid.UUID) -> None:
        """Execute the appropriate LangGraph workflow for a claimed job with step checkpointing and heartbeat."""
        if self.session_factory is None:
            return

        async with self.session_factory() as session:
            job = await session.get(Job, job_id)
            if not job or job.status != "running":
                return

            logger.info(
                f"Executing job {job.id} with LangGraph workflow",
                extra={"job_id": str(job.id), "job_type": job.job_type},
            )

            # Heartbeat background task
            heartbeat_stop = asyncio.Event()

            async def _heartbeat_loop() -> None:
                while not heartbeat_stop.is_set():
                    try:
                        await asyncio.sleep(3.0)
                        if self.session_factory is not None:
                            async with self.session_factory() as hb_session:
                                await hb_session.execute(
                                    update(Job)
                                    .where(Job.id == job_id, Job.status == "running")
                                    .values(heartbeat_at=datetime.now(UTC))
                                )
                                await hb_session.commit()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.warning(f"Heartbeat update failed: {e}")

            heartbeat_task = asyncio.create_task(_heartbeat_loop())

            try:
                # Select workflow based on job_type
                if job.job_type == "document_processing":
                    workflow = document_workflow
                    initial_state: dict[str, Any] = {
                        "document_id": str(job.resource_id),
                        "user_id": str(job.user_id),
                        "job_id": str(job.id),
                        "current_step": job.current_step or "validate_document",
                        "progress": float(job.progress or 0.0),
                        **dict(job.state or {}),
                    }
                else:
                    workflow = assessment_workflow
                    initial_state = {
                        "assessment_id": str(job.resource_id),
                        "user_id": str(job.user_id),
                        "job_id": str(job.id),
                        "current_step": job.current_step or "load_assessment",
                        "progress": float(job.progress or 0.0),
                        **dict(job.state or {}),
                    }

                config = {
                    "configurable": {
                        "session": session,
                        "job_id": str(job.id),
                    }
                }

                # Stream through graph nodes, persisting checkpoints after each node
                async for event in workflow.astream(initial_state, config=config):
                    # Check for cancellation
                    check_res = await session.execute(
                        select(Job.status).where(Job.id == job_id)
                    )
                    current_status = check_res.scalar_one_or_none()
                    if current_status == "cancelled":
                        logger.info(f"Job {job_id} cancellation detected; halting workflow execution.")
                        break

                    for node_name, node_output in event.items():
                        if isinstance(node_output, dict):
                            new_progress = float(node_output.get("progress", float(job.progress)))
                            job.progress = Decimal(str(round(new_progress, 2)))
                            job.current_step = str(node_output.get("current_step", node_name))
                            # Update compact state
                            compact_update = {k: v for k, v in node_output.items() if not k.startswith("_")}
                            job.state = {**dict(job.state or {}), **compact_update}
                            job.heartbeat_at = datetime.now(UTC)
                            await session.commit()
                            logger.info(
                                f"Job {job.id} checkpoint: {job.current_step} ({job.progress}%)",
                                extra={"job_id": str(job.id), "step": job.current_step},
                            )

                # Finalize job completion
                check_final = await session.execute(
                    select(Job.status).where(Job.id == job_id)
                )
                if check_final.scalar_one_or_none() != "cancelled":
                    job.status = "completed"
                    job.progress = Decimal("100.00")
                    job.error_code = None
                    job.error_message = None
                    await session.commit()
                    logger.info(f"Job {job.id} successfully completed.")

            except Exception as exc:
                logger.exception(f"Job {job.id} execution failed: {exc}")
                job.status = "failed"
                job.error_code = type(exc).__name__
                job.error_message = str(exc)
                await session.commit()

            finally:
                heartbeat_stop.set()
                heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat_task

    async def enqueue_job(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        job_type: str,
        initial_state: dict[str, Any] | None = None,
    ) -> Job:
        """Create or return existing queued/running job for a resource."""
        # 1. Prevent duplicate active jobs for the same resource
        active_job = await job_repo.get_active_job(
            session,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
        )
        if active_job is not None:
            logger.info(
                f"Returning existing active job {active_job.id} for {resource_type} {resource_id}"
            )
            return active_job

        # 2. Create new job record
        new_job = Job(
            id=uuid.uuid4(),
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            job_type=job_type,
            status="queued",
            progress=Decimal("0.00"),
            current_step=None,
            state=initial_state or {},
        )
        session.add(new_job)
        await session.commit()
        logger.info(
            f"Enqueued new job {new_job.id} (type: {job_type}, resource: {resource_id})"
        )
        return new_job

    async def cancel_job(
        self,
        session: AsyncSession,
        *,
        resource_type: str,
        resource_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Job | None:
        """Cancel any running or queued job for a resource."""
        active_job = await job_repo.get_active_job(
            session,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
        )
        if active_job is not None:
            active_job.status = "cancelled"
            active_job.error_code = "USER_CANCELLED"
            active_job.error_message = "Job was cancelled by the user."
            await session.commit()
            logger.info(f"Marked job {active_job.id} as cancelled.")
            return active_job
        return None


job_runner = PostgresJobRunner()
