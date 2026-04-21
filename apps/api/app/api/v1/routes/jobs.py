from fastapi import APIRouter

from app.schemas.job import JobStatusResponse
from app.workers.queue import get_job_status_by_job_id

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    status = await get_job_status_by_job_id(job_id)
    return JobStatusResponse(job_id=job_id, status=status)
