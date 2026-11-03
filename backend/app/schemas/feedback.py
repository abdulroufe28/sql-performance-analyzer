from datetime import datetime
from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    category: str = Field(default="GENERAL", description="GENERAL, FEATURE_REQUEST, BUG_REPORT, or PERFORMANCE_ISSUE")
    rating: int = Field(default=5, ge=1, le=5, description="1 to 5 stars")
    comment: str = Field(min_length=3, max_length=2000, description="Feedback message")


class FeedbackResponse(BaseModel):
    id: int
    user_id: int
    category: str
    rating: int
    comment: str
    status: str
    created_at: datetime
    user_email: str | None = None

    model_config = {"from_attributes": True}


class FeedbackStatusUpdateRequest(BaseModel):
    status: str = Field(description="PENDING, REVIEWED, or RESOLVED")
