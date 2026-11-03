from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, get_db
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.query_comparison import QueryComparison
from backend.app.models.user import User
from backend.app.schemas.dashboard import (
    DashboardMetricsResponse,
    RecentQueryItem,
    SlowQueryItem,
)


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

FREE_COMPARISON_QUOTA = 10


@router.get(
    "/metrics",
    response_model=DashboardMetricsResponse,
)
def get_user_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user.id

    # Total queries
    total_queries = db.scalar(
        select(func.count(QueryAnalysis.id)).where(QueryAnalysis.user_id == user_id)
    ) or 0

    # Avg execution time
    avg_time = db.scalar(
        select(func.avg(QueryAnalysis.execution_time_ms)).where(QueryAnalysis.user_id == user_id)
    ) or 0.0

    # Full table scans
    fts_count = db.scalar(
        select(func.count(QueryAnalysis.id)).where(
            QueryAnalysis.user_id == user_id,
            QueryAnalysis.has_full_table_scan.is_(True),
        )
    ) or 0

    # Slow queries (> 50ms)
    slow_count = db.scalar(
        select(func.count(QueryAnalysis.id)).where(
            QueryAnalysis.user_id == user_id,
            QueryAnalysis.execution_time_ms > 50.0,
        )
    ) or 0

    # Total comparisons
    total_comparisons = db.scalar(
        select(func.count(QueryComparison.id)).where(QueryComparison.user_id == user_id)
    ) or 0

    # Slowest queries top 5
    slowest_stmt = (
        select(QueryAnalysis)
        .where(QueryAnalysis.user_id == user_id)
        .order_by(QueryAnalysis.execution_time_ms.desc())
        .limit(5)
    )
    slowest_models = db.scalars(slowest_stmt).all()
    slowest_queries = [
        SlowQueryItem(
            id=q.id,
            query=q.query,
            execution_time_ms=q.execution_time_ms,
            row_count=q.row_count,
            created_at=q.created_at,
        )
        for q in slowest_models
    ]

    # Recent queries top 5
    recent_stmt = (
        select(QueryAnalysis)
        .where(QueryAnalysis.user_id == user_id)
        .order_by(QueryAnalysis.created_at.desc(), QueryAnalysis.id.desc())
        .limit(5)
    )
    recent_models = db.scalars(recent_stmt).all()
    recent_queries = [
        RecentQueryItem(
            id=q.id,
            query=q.query,
            execution_time_ms=q.execution_time_ms,
            row_count=q.row_count,
            performance_rating=q.performance_rating,
            created_at=q.created_at,
        )
        for q in recent_models
    ]

    optimized_count = max(0, total_queries - fts_count)

    return DashboardMetricsResponse(
        total_queries=total_queries,
        avg_execution_time_ms=round(float(avg_time), 3),
        slow_queries_count=slow_count,
        full_table_scans_count=fts_count,
        optimized_queries_count=optimized_count,
        total_comparisons=total_comparisons,
        comparison_quota_limit=FREE_COMPARISON_QUOTA,
        comparison_quota_used=total_comparisons,
        slowest_queries=slowest_queries,
        recent_queries=recent_queries,
    )
