import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, get_db
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.user import User
from backend.app.schemas.query import (
    QueryAnalyzeRequest,
    QueryAnalyzeResponse,
    QueryHistoryResponse,
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


@router.get(
    "/history",
    response_model=QueryHistoryResponse,
)
def get_query_history(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page (max 100)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size

    total = db.scalar(
        select(func.count(QueryAnalysis.id)).where(
            QueryAnalysis.user_id == current_user.id
        )
    ) or 0

    stmt = (
        select(QueryAnalysis)
        .where(QueryAnalysis.user_id == current_user.id)
        .order_by(QueryAnalysis.created_at.desc(), QueryAnalysis.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = db.scalars(stmt).all()

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return QueryHistoryResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
