from fastapi import APIRouter
from pydantic import BaseModel

from app.security.auth import create_access_token
from app.security.guardrails import validate_student_id

router = APIRouter(prefix="/auth", tags=["Auth"])


class TokenRequest(BaseModel):
    student_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
async def issue_token(request: TokenRequest):
    validate_student_id(request.student_id)
    return TokenResponse(access_token=create_access_token(request.student_id))
