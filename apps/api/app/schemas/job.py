from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
