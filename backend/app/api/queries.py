import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, get_db
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.query_comparison import QueryComparison
from backend.app.models.user import User
from backend.app.schemas.query import (
    QueryAnalyzeRequest,
    QueryAnalyzeResponse,
    QueryCompareRequest,
    QueryCompareResponse,
    QueryHistoryResponse,
    SavedComparisonsResponse,
)
from backend.app.services.comparison_service import compare_queries
from backend.app.services.query_execution_service import (
    execute_read_only_query,
)


router = APIRouter(
    prefix="/queries",
    tags=["Queries"],
)

FREE_COMPARISON_QUOTA = 10


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
        query_cost=result.get("query_cost"),
        rows_examined=result.get("total_rows_examined"),
        performance_rating=result.get("performance_rating"),
        has_full_table_scan=result.get("has_full_table_scan", False),
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


@router.post(
    "/compare",
    response_model=QueryCompareResponse,
)
def compare_sql_queries(
    data: QueryCompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Free tier quota enforcement
    if current_user.role != "ADMIN":
        used_comparisons = db.scalar(
            select(func.count(QueryComparison.id)).where(
                QueryComparison.user_id == current_user.id
            )
        ) or 0

        if used_comparisons >= FREE_COMPARISON_QUOTA:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Comparison quota reached. Your free tier allows {FREE_COMPARISON_QUOTA} comparisons. Contact support or upgrade for unlimited queries.",
            )

    comparison_result = compare_queries(data.query_a, data.query_b)

    saved = QueryComparison(
        user_id=current_user.id,
        title=data.title or "SQL Comparison",
        query_a=comparison_result["query_a"]["query"],
        query_b=comparison_result["query_b"]["query"],
        query_a_time_ms=comparison_result["query_a"]["execution_time_ms"],
        query_b_time_ms=comparison_result["query_b"]["execution_time_ms"],
        query_a_rows_examined=comparison_result["query_a"].get("total_rows_examined"),
        query_b_rows_examined=comparison_result["query_b"].get("total_rows_examined"),
        faster_query=comparison_result["faster_query"],
        speedup_percentage=comparison_result["speedup_percentage"],
    )

    db.add(saved)
    db.commit()
    db.refresh(saved)

    comparison_result["id"] = saved.id
    comparison_result["title"] = saved.title

    return comparison_result


@router.get(
    "/comparisons",
    response_model=SavedComparisonsResponse,
)
def get_user_comparisons(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page (max 100)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size

    total = db.scalar(
        select(func.count(QueryComparison.id)).where(
            QueryComparison.user_id == current_user.id
        )
    ) or 0

    stmt = (
        select(QueryComparison)
        .where(QueryComparison.user_id == current_user.id)
        .order_by(QueryComparison.created_at.desc(), QueryComparison.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = db.scalars(stmt).all()

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return SavedComparisonsResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
