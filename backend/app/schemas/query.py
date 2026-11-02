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