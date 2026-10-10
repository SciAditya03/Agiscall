from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db import SessionDep
from app.schemas import to_response
from app.services import customers

router = APIRouter(tags=["customers"])


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str, session: SessionDep) -> JSONResponse:
    return to_response(customers.lookup_customer(session, customer_id))
