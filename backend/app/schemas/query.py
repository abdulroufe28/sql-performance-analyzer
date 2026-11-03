from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QueryAnalyzeRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=10000,
    )


class BottleneckItem(BaseModel):
    type: str
    severity: str
    table: str
    message: str


class RecommendationItem(BaseModel):
    category: str
    suggestion: str


class QueryAnalyzeResponse(BaseModel):
    query: str
    execution_time_ms: float
    row_count: int
    rows: list[dict[str, Any]]
    query_cost: float | None = None
    total_rows_examined: int = 0
    indexes_used: list[str] = []
    has_full_table_scan: bool = False
    using_filesort: bool = False
    using_temporary: bool = False
    performance_rating: str = "OPTIMIZED"
    bottlenecks: list[BottleneckItem] = []
    recommendations: list[RecommendationItem] = []
    tabular_plan: list[dict[str, Any]] = []
    json_plan: dict[str, Any] = {}


class QueryHistoryItem(BaseModel):
    id: int
    query: str
    execution_time_ms: float
    row_count: int
    query_cost: float | None = None
    rows_examined: int | None = None
    performance_rating: str | None = None
    has_full_table_scan: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class QueryHistoryResponse(BaseModel):
    items: list[QueryHistoryItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class QueryCompareRequest(BaseModel):
    query_a: str = Field(min_length=1, max_length=10000)
    query_b: str = Field(min_length=1, max_length=10000)
    title: str | None = Field(default=None, max_length=255)


class QueryComparisonMetric(BaseModel):
    query: str
    execution_time_ms: float
    row_count: int
    query_cost: float | None = None
    total_rows_examined: int = 0
    indexes_used: list[str] = []
    has_full_table_scan: bool = False
    using_filesort: bool = False
    using_temporary: bool = False
    performance_rating: str = "OPTIMIZED"
    bottlenecks: list[BottleneckItem] = []
    recommendations: list[RecommendationItem] = []


class QueryCompareResponse(BaseModel):
    id: int | None = None
    title: str | None = None
    query_a: QueryComparisonMetric
    query_b: QueryComparisonMetric
    faster_query: str  # "QUERY_A", "QUERY_B", "TIE"
    time_diff_ms: float
    speedup_percentage: float
    rows_examined_diff: int
    verdict: str


class SavedComparisonItem(BaseModel):
    id: int
    title: str | None = None
    query_a: str
    query_b: str
    query_a_time_ms: float
    query_b_time_ms: float
    query_a_rows_examined: int | None = None
    query_b_rows_examined: int | None = None
    faster_query: str
    speedup_percentage: float
    created_at: datetime

    model_config = {"from_attributes": True}


class SavedComparisonsResponse(BaseModel):
    items: list[SavedComparisonItem]
    page: int
    page_size: int
    total: int
    total_pages: int
