from datetime import datetime
from pydantic import BaseModel


class UserStats(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    admin_users: int


class UsageStats(BaseModel):
    total_queries: int
    total_comparisons: int
    avg_platform_latency_ms: float
    total_full_table_scans: int


class DatabaseHealth(BaseModel):
    app_database: str
    analysis_database: str
    status: str


class AdminDashboardResponse(BaseModel):
    user_stats: UserStats
    usage_stats: UsageStats
    health: DatabaseHealth
