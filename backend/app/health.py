"""Report process liveness without reading data or contacting dependencies."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/health", response_model=HealthResponse, summary="Check process liveness")
def get_health() -> HealthResponse:
    """Confirm that the API responds; this does not check a database or model."""
    return HealthResponse()
