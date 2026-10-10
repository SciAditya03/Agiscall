from typing import Annotated

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from app.db import SessionDep
from app.schemas import to_response
from app.services import policies

router = APIRouter(tags=["policies"])


@router.get("/policies/{policy_id}")
def get_policy(
    policy_id: str,
    session: SessionDep,
    x_verification_token: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    return to_response(policies.lookup_policy(session, policy_id, x_verification_token))
