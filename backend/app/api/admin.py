from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, require_admin
from backend.app.core.database import analysis_engine, app_engine
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.query_comparison import QueryComparison
from backend.app.models.user import User
from backend.app.schemas.admin import (
    AdminDashboardResponse,
    DatabaseHealth,
    UsageStats,
    UserStats,
)


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
)
def get_admin_dashboard(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # User Statistics
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_users = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    inactive_users = total_users - active_users
    admin_users = db.scalar(select(func.count(User.id)).where(User.role == "ADMIN")) or 0

    # Usage Statistics
    total_queries = db.scalar(select(func.count(QueryAnalysis.id))) or 0
    total_comparisons = db.scalar(select(func.count(QueryComparison.id))) or 0
    avg_latency = db.scalar(select(func.avg(QueryAnalysis.execution_time_ms))) or 0.0
    total_fts = db.scalar(
        select(func.count(QueryAnalysis.id)).where(QueryAnalysis.has_full_table_scan.is_(True))
    ) or 0

    # Database Health Monitoring
    app_db_status = "ONLINE"
    try:
        with app_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        app_db_status = f"ERROR: {str(e)[:50]}"

    analysis_db_status = "ONLINE"
    try:
        with analysis_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        analysis_db_status = f"ERROR: {str(e)[:50]}"

    overall_status = "HEALTHY" if app_db_status == "ONLINE" and analysis_db_status == "ONLINE" else "DEGRADED"

    return AdminDashboardResponse(
        user_stats=UserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            admin_users=admin_users,
        ),
        usage_stats=UsageStats(
            total_queries=total_queries,
            total_comparisons=total_comparisons,
            avg_platform_latency_ms=round(float(avg_latency), 3),
            total_full_table_scans=total_fts,
        ),
        health=DatabaseHealth(
            app_database=app_db_status,
            analysis_database=analysis_db_status,
            status=overall_status,
        ),
    )
