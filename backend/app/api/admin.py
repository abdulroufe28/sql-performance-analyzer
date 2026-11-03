import threading
import psutil
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, require_admin
from backend.app.core.database import analysis_engine, app_engine
from backend.app.models.feedback import UserFeedback
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.query_comparison import QueryComparison
from backend.app.models.security_audit import SecurityAuditLog
from backend.app.models.user import User
from backend.app.schemas.admin import (
    AdminDashboardResponse,
    AdminUserItem,
    DatabaseHealth,
    SecurityLogItem,
    ServerTelemetry,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
    UsageStats,
    UserStats,
)
from backend.app.schemas.feedback import FeedbackResponse, FeedbackStatusUpdateRequest


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

    # Live Server Hardware Telemetry
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    active_threads = threading.active_count()

    telemetry = ServerTelemetry(
        cpu_percent=float(cpu_pct),
        memory_used_gb=round(mem.used / (1024**3), 2),
        memory_total_gb=round(mem.total / (1024**3), 2),
        memory_percent=float(mem.percent),
        disk_used_gb=round(disk.used / (1024**3), 2),
        disk_total_gb=round(disk.total / (1024**3), 2),
        disk_percent=float(disk.percent),
        active_threads=active_threads,
    )

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
        telemetry=telemetry,
    )


@router.get(
    "/users",
    response_model=list[AdminUserItem],
)
def list_users(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    results = []
    for u in users:
        q_count = db.scalar(
            select(func.count(QueryAnalysis.id)).where(QueryAnalysis.user_id == u.id)
        ) or 0
        results.append(
            AdminUserItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                is_active=u.is_active,
                total_queries=q_count,
                created_at=u.created_at,
            )
        )
    return results


@router.patch(
    "/users/{user_id}/status",
)
def update_user_status(
    user_id: int,
    data: UpdateUserStatusRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot alter your own status")

    user.is_active = data.is_active
    db.commit()
    return {"message": f"User status updated to {'active' if data.is_active else 'suspended'}"}


@router.patch(
    "/users/{user_id}/role",
)
def update_user_role(
    user_id: int,
    data: UpdateUserRoleRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot alter your own role")

    role_upper = data.role.upper()
    if role_upper not in ("USER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role. Must be USER or ADMIN")

    user.role = role_upper
    db.commit()
    return {"message": f"User role updated to {role_upper}"}


@router.get(
    "/feedback",
    response_model=list[FeedbackResponse],
)
def get_all_feedback(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    feedbacks = db.scalars(select(UserFeedback).order_by(UserFeedback.created_at.desc())).all()
    results = []
    for f in feedbacks:
        dto = FeedbackResponse.model_validate(f)
        user = db.get(User, f.user_id)
        dto.user_email = user.email if user else "deleted_user"
        results.append(dto)
    return results


@router.patch(
    "/feedback/{feedback_id}/status",
)
def update_feedback_status(
    feedback_id: int,
    data: FeedbackStatusUpdateRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    fb = db.get(UserFeedback, feedback_id)
    if not fb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    status_upper = data.status.upper()
    if status_upper not in ("PENDING", "REVIEWED", "RESOLVED"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    fb.status = status_upper
    db.commit()
    return {"message": f"Feedback status updated to {status_upper}"}


@router.get(
    "/security-logs",
    response_model=list[SecurityLogItem],
)
def get_security_audit_logs(
    limit: int = Query(default=20, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    logs = db.scalars(select(SecurityAuditLog).order_by(SecurityAuditLog.created_at.desc()).limit(limit)).all()
    results = []
    for l in logs:
        item = SecurityLogItem(
            id=l.id,
            user_id=l.user_id,
            violation_type=l.violation_type,
            attempted_query=l.attempted_query,
            client_ip=l.client_ip,
            created_at=l.created_at,
        )
        if l.user_id:
            u = db.get(User, l.user_id)
            item.user_email = u.email if u else None
        results.append(item)
    return results
