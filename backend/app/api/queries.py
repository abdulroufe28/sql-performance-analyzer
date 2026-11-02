from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_current_user, get_db
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.user import User
from backend.app.schemas.query import (
    QueryAnalyzeRequest,
    QueryAnalyzeResponse,
)
from backend.app.services.query_execution_service import (
    execute_read_only_query,
)


router = APIRouter(
    prefix="/queries",
    tags=["Queries"],
)


@router.post(
    "/analyze",
    response_model=QueryAnalyzeResponse,
)
def analyze_query(
    data: QueryAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = execute_read_only_query(data.query)

    analysis = QueryAnalysis(
        user_id=current_user.id,
        query=result["query"],
        execution_time_ms=result["execution_time_ms"],
        row_count=result["row_count"],
    )

    db.add(analysis)
    db.commit()

    return result