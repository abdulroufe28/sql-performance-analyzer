from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SlowQueryItem(BaseModel):
    id: int
    query: str
    execution_time_ms: float
    row_count: int
    created_at: datetime


class RecentQueryItem(BaseModel):
    id: int
    query: str
    execution_time_ms: float
    row_count: int
    performance_rating: str | None = None
    created_at: datetime


class DashboardMetricsResponse(BaseModel):
    total_queries: int
    avg_execution_time_ms: float
    slow_queries_count: int  # e.g. queries > 50ms or rated CRITICAL/NEEDS_OPTIMIZATION
    full_table_scans_count: int
    optimized_queries_count: int
    total_comparisons: int
    comparison_quota_limit: int
    comparison_quota_used: int
    slowest_queries: list[SlowQueryItem]
    recent_queries: list[RecentQueryItem]
