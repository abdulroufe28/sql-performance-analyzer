import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, get_db
from backend.app.core.database import analysis_engine
from backend.app.models.query_analysis import QueryAnalysis
from backend.app.models.query_comparison import QueryComparison
from backend.app.models.security_audit import SecurityAuditLog
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
from backend.app.services.sql_safety_service import SQLSafetyError


router = APIRouter(
    prefix="/queries",
    tags=["Queries"],
)

FREE_COMPARISON_QUOTA = 10


@router.get("/schema")
def get_analysis_schema(
    current_user: User = Depends(get_current_user),
):
    insp = inspect(analysis_engine)
    schema_tables = []
    for tbl_name in insp.get_table_names():
        cols = insp.get_columns(tbl_name)
        pk_constraint = insp.get_pk_constraint(tbl_name)
        pk_cols = set(pk_constraint.get("constrained_columns", [])) if pk_constraint else set()
        schema_tables.append({
            "name": tbl_name,
            "columns": [
                {
                    "name": c["name"],
                    "type": str(c["type"]).split(" COLLATE")[0],
                    "is_primary": c["name"] in pk_cols,
                }
                for c in cols
            ],
        })
    return {"tables": schema_tables}


@router.post(
    "/analyze",
    response_model=QueryAnalyzeResponse,
)
def analyze_query(
    data: QueryAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = execute_read_only_query(data.query)
    except SQLSafetyError as err:
        # Audit log malicious/blocked queries
        audit_entry = SecurityAuditLog(
            user_id=current_user.id,
            violation_type="DESTRUCTIVE_SQL_BLOCKED",
            attempted_query=data.query[:1000],
        )
        db.add(audit_entry)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )

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


@router.get(
    "/analyses/{analysis_id}/export",
)
def export_query_report(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.get(QueryAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis record not found")

    if analysis.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this report")

    return {
        "report_type": "Database Performance Analysis Report",
        "analysis_id": analysis.id,
        "query": analysis.query,
        "execution_time_ms": analysis.execution_time_ms,
        "row_count": analysis.row_count,
        "query_cost": analysis.query_cost,
        "rows_examined": analysis.rows_examined,
        "performance_rating": analysis.performance_rating,
        "has_full_table_scan": analysis.has_full_table_scan,
        "created_at": analysis.created_at.isoformat(),
        "exported_by": current_user.email,
        "verdict": "Query exhibits full table scan bottlenecks requiring index optimization." if analysis.has_full_table_scan else "Query is optimized with efficient index access."
    }

