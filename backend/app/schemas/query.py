from datetime import datetime

from pydantic import BaseModel, Field


class QueryAnalyzeRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=10000,
    )


class QueryAnalyzeResponse(BaseModel):
    query: str
    execution_time_ms: float
    row_count: int
    rows: list[dict]


class QueryHistoryItem(BaseModel):
    id: int
    query: str
    execution_time_ms: float
    row_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class QueryHistoryResponse(BaseModel):
    items: list[QueryHistoryItem]
    page: int
    page_size: int
    total: int
    total_pages: int
