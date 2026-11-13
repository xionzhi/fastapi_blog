from fastapi import APIRouter
from sqlalchemy import select

from app.common.models import HealthResponse
from app.core.dependencies import DbSession

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health(db_session: DbSession) -> HealthResponse:
    db_session.execute(select(1)).scalar_one()
    return HealthResponse()
