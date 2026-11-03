from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, get_db, require_admin
from backend.app.models.feedback import UserFeedback
from backend.app.models.user import User
from backend.app.schemas.feedback import (
    FeedbackCreateRequest,
    FeedbackResponse,
    FeedbackStatusUpdateRequest,
)


router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
)


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    data: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    feedback = UserFeedback(
        user_id=current_user.id,
        category=data.category.upper(),
        rating=data.rating,
        comment=data.comment,
        status="PENDING",
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    res = FeedbackResponse.model_validate(feedback)
    res.user_email = current_user.email
    return res


@router.get(
    "/my",
    response_model=list[FeedbackResponse],
)
def get_my_feedback(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(UserFeedback)
        .where(UserFeedback.user_id == current_user.id)
        .order_by(UserFeedback.created_at.desc())
    )
    feedbacks = db.scalars(stmt).all()
    results = []
    for f in feedbacks:
        dto = FeedbackResponse.model_validate(f)
        dto.user_email = current_user.email
        results.append(dto)
    return results
