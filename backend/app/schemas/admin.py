from datetime import datetime
from pydantic import BaseModel, Field


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


class ServerTelemetry(BaseModel):
    cpu_percent: float
    memory_used_gb: float
    memory_total_gb: float
    memory_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    active_threads: int


class AdminDashboardResponse(BaseModel):
    user_stats: UserStats
    usage_stats: UsageStats
    health: DatabaseHealth
    telemetry: ServerTelemetry


class AdminUserItem(BaseModel):
    id: int
    email: str
    full_name: str | None
    role: str
    is_active: bool
    total_queries: int
    created_at: datetime


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(description="USER or ADMIN")


class SecurityLogItem(BaseModel):
    id: int
    user_id: int | None
    user_email: str | None = None
    violation_type: str
    attempted_query: str
    client_ip: str | None = None
    created_at: datetime
