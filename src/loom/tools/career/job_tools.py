"""Job queue management tools for Loom.

Provides MCP tools for submitting, monitoring, and managing long-running jobs:
  - research_job_submit: Submit a job to the queue
  - research_job_status: Get job status (pending/running/completed/failed)
  - research_job_result: Get job result when completed
  - research_job_list: List jobs with optional status filter
  - research_job_cancel: Cancel a pending or running job
"""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import json
import logging
from typing import Any

try:
    from loom.job_queue import get_job_queue
    _JOB_QUEUE_AVAILABLE = True
except ImportError:
    _JOB_QUEUE_AVAILABLE = False
    get_job_queue = None  # type: ignore[assignment]

logger = logging.getLogger("loom.tools.job_tools")


@handle_tool_errors("research_job_submit")
async def research_job_submit(
    tool_name: str,
    params: dict[str, Any],
    callback_url: str | None = None,
) -> dict[str, Any]:
    """Submit a long-running tool job to the async queue.

    Accepts the name of a Loom tool and its parameters, submits to the job queue,
    and returns immediately with a job_id. Use research_job_status to poll.

    Args:
        tool_name: Name of the tool to execute (e.g., "research_expert")
        params: Parameters to pass to the tool as a dict
        callback_url: Optional webhook URL for completion callback (POST with job data)

    Returns:
        Dict with job_id (str) for status polling

    Example:
        >>> result = await research_job_submit("research_expert", {"query": "AI safety"})
        >>> job_id = result["job_id"]
        >>> # Later, poll status:
        >>> status = await research_job_status(job_id)
    """
    if not _JOB_QUEUE_AVAILABLE:
        return {"error": "Job queue not available", "tool": "research_job_submit"}
    try:
        queue = get_job_queue()
        job_id = await queue.submit(
            tool_name=tool_name,
            params=params,
            callback_url=callback_url,
        )
        logger.info("job_submit_success job_id=%s tool=%s", job_id, tool_name)
        return {
            "job_id": job_id,
            "status": "pending",
            "message": f"Job submitted. Use research_job_status('{job_id}') to poll.",
        }
    except Exception as exc:
        logger.exception("research_job_submit failed")
        return {"error": str(exc), "tool": "research_job_submit"}


@handle_tool_errors("research_job_status")
async def research_job_status(job_id: str) -> dict[str, Any]:
    """Get the current status of a job.

    Returns status (pending/running/completed/failed) along with timestamps.
    Does not return result data; use research_job_result for that.

    Args:
        job_id: Job ID returned by research_job_submit

    Returns:
        Dict with job_id, status, timestamps (created_at, started_at, completed_at), error

    Example:
        >>> status = await research_job_status("abc123")
        >>> print(status["status"])  # "running"
    """
    if not _JOB_QUEUE_AVAILABLE:
        return {"error": "Job queue not available", "tool": "research_job_status"}
    try:
        queue = get_job_queue()
        status = await queue.get_status(job_id)
        logger.debug("job_status_retrieved job_id=%s status=%s", job_id, status.get("status"))
        return status
    except Exception as exc:
        logger.exception("research_job_status failed")
        return {"error": str(exc), "tool": "research_job_status"}


@handle_tool_errors("research_job_result")
async def research_job_result(job_id: str) -> dict[str, Any]:
    """Get the result of a completed job.

    Only available after the job finishes (status == "completed").
    Returns error dict if job failed or is still in progress.

    Args:
        job_id: Job ID returned by research_job_submit

    Returns:
        Dict with status and either 'result' (completed) or 'error' (failed/pending)

    Example:
        >>> result = await research_job_result("abc123")
        >>> if result["status"] == "completed":
        ...     data = result["result"]
    """
    if not _JOB_QUEUE_AVAILABLE:
        return {"error": "Job queue not available", "tool": "research_job_result"}
    try:
        queue = get_job_queue()
        result = await queue.get_result(job_id)
        if "error" not in result:
            logger.info("job_result_retrieved job_id=%s status=%s", job_id, result.get("status"))
        return result
    except Exception as exc:
        logger.exception("research_job_result failed")
        return {"error": str(exc), "tool": "research_job_result"}


@handle_tool_errors("research_job_list")
async def research_job_list(
    status: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List jobs in the queue with optional status filter.

    Returns a list of recent jobs (default 20, max 100) optionally filtered by status.

    Args:
        status: Filter by status: "pending", "running", "completed", or "failed"
                If None, returns jobs in all statuses
        limit: Max jobs to return (default 20, max 100)

    Returns:
        Dict with 'jobs' list containing job summaries

    Example:
        >>> jobs = await research_job_list(status="running")
        >>> for job in jobs["jobs"]:
        ...     print(job["job_id"], job["status"])
    """
    if not _JOB_QUEUE_AVAILABLE:
        return {"error": "Job queue not available", "tool": "research_job_list"}
    try:
        queue = get_job_queue()
        jobs = await queue.list_jobs(status=status, limit=limit)
        logger.debug("job_list_retrieved count=%d status=%s", len(jobs), status)
        return {
            "jobs": jobs,
            "count": len(jobs),
            "status_filter": status,
        }
    except Exception as exc:
        logger.exception("research_job_list failed")
        return {"error": str(exc), "tool": "research_job_list"}


@handle_tool_errors("research_job_cancel")
async def research_job_cancel(job_id: str) -> dict[str, Any]:
    """Cancel a pending or running job.

    Does nothing if job is already completed or failed.

    Args:
        job_id: Job ID returned by research_job_submit

    Returns:
        Dict with success (bool) and message

    Example:
        >>> result = await research_job_cancel("abc123")
        >>> print(result["success"])  # True
    """
    if not _JOB_QUEUE_AVAILABLE:
        return {"error": "Job queue not available", "tool": "research_job_cancel"}
    try:
        queue = get_job_queue()
        success = await queue.cancel(job_id)
        if success:
            logger.info("job_cancelled job_id=%s", job_id)
            return {
                "success": True,
                "message": f"Job {job_id} has been cancelled",
            }
        else:
            logger.warning("job_cancel_failed job_id=%s", job_id)
            return {
                "success": False,
                "message": f"Job {job_id} not found or already completed",
            }
    except Exception as exc:
        logger.exception("research_job_cancel failed")
        return {"error": str(exc), "tool": "research_job_cancel"}
