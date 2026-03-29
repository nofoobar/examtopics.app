from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from apis.deps import get_db
from db.models.exam_request import ExamRequest
from schemas.exam_request import ExamRequestCreate, ExamRequestResponse

router = APIRouter(prefix="/api/v1", tags=["exam-requests"])


@router.post(
    "/exam-requests",
    response_model=ExamRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exam_request(
    payload: ExamRequestCreate,
    session: Session = Depends(get_db),
):
    """Submit a request for a new exam to be added to the platform."""
    exam_request = ExamRequest(**payload.model_dump())
    session.add(exam_request)
    session.commit()
    session.refresh(exam_request)
    return exam_request
