from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db import SessionDep
from app.schemas import VerificationRequest, to_response
from app.services import verification

router = APIRouter(tags=["verifications"])


@router.post("/verifications")
def create_verification(body: VerificationRequest, session: SessionDep) -> JSONResponse:
    return to_response(verification.verify_caller(session, body), 201)
