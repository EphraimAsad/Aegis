"""Celery tasks for system maintenance."""

from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy import delete, select

from app.db.session import get_sync_session
from app.models.job import Job, JobStatus


@shared_task(name="app.worker.tasks.maintenance.cleanup_old_jobs")
def cleanup_old_jobs(days_old: int = 30) -> dict:
    """
    Clean up old completed/failed jobs from the database.

    Args:
        days_old: Delete jobs older than this many days

    Returns:
        dict with cleanup statistics
    """
    db = next(get_sync_session())

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Count jobs to delete
        count_query = (
            select(Job)
            .where(Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED]))
            .where(Job.updated_at < cutoff_date)
        )
        jobs_to_delete = db.execute(count_query).scalars().all()
        count = len(jobs_to_delete)

        if count > 0:
            # Delete old jobs
            delete_query = (
                delete(Job)
                .where(Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED]))
                .where(Job.updated_at < cutoff_date)
            )
            db.execute(delete_query)
            db.commit()

        return {
            "status": "success",
            "jobs_deleted": count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
            "jobs_deleted": 0,
        }

    finally:
        db.close()


@shared_task(name="app.worker.tasks.maintenance.cleanup_stale_jobs")
def cleanup_stale_jobs(hours_stale: int = 24) -> dict:
    """
    Mark stale running jobs as failed.

    Jobs that have been running for too long without updates
    are likely stuck and should be marked as failed.

    Args:
        hours_stale: Mark jobs as failed if running longer than this

    Returns:
        dict with cleanup statistics
    """
    db = next(get_sync_session())

    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_stale)

        # Find stale jobs
        stale_jobs = (
            db.execute(
                select(Job)
                .where(Job.status == JobStatus.RUNNING)
                .where(Job.updated_at < cutoff_time)
            )
            .scalars()
            .all()
        )

        count = 0
        for job in stale_jobs:
            job.status = JobStatus.FAILED
            job.error_message = (
                f"Job marked as failed: no progress for {hours_stale} hours"
            )
            count += 1

        if count > 0:
            db.commit()

        return {
            "status": "success",
            "jobs_marked_failed": count,
            "cutoff_time": cutoff_time.isoformat(),
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
            "jobs_marked_failed": 0,
        }

    finally:
        db.close()
