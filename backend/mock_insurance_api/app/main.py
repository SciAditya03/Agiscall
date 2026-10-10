import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import DomainError, ErrorCode
from app.routers import customers, policies, verifications
from app.schemas import Envelope, InvalidField, to_response

logger = logging.getLogger(__name__)

_HTTP_ERRORS = {
    404: (ErrorCode.ROUTE_NOT_FOUND, "That endpoint does not exist."),
    405: (ErrorCode.METHOD_NOT_ALLOWED, "That method is not allowed on this endpoint."),
}


async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
    envelope = Envelope(status="REJECTED", code=exc.code.value, message=exc.message, data=exc.data)
    return to_response(envelope, exc.http_status)


def _field_name(error: dict) -> str:
    if error.get("type") == "json_invalid":
        return "body"
    loc = [str(part) for part in error.get("loc", ())]
    # Drop the "body"/"query"/"header" prefix unless it's all there is.
    return ".".join(loc[1:]) if len(loc) > 1 else ".".join(loc) or "body"


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    missing: list[str] = []
    invalid: list[InvalidField] = []
    for error in exc.errors():
        field = _field_name(error)
        if error.get("type") == "missing":
            if field not in missing:
                missing.append(field)
        elif all(item.field != field for item in invalid):
            reason = str(error.get("msg", "Invalid value")).removeprefix("Value error, ")
            invalid.append(InvalidField(field=field, reason=reason))

    if missing:
        code, message = ErrorCode.MISSING_FIELDS, f"Missing required details: {', '.join(missing)}."
    else:
        fields = ", ".join(item.field for item in invalid)
        code, message = ErrorCode.INVALID_FIELDS, f"Some details are not valid: {fields}."
    envelope = Envelope(
        status="NEEDS_INFO", code=code.value, message=message, missing_fields=missing, invalid_fields=invalid
    )
    return to_response(envelope, 422)


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _HTTP_ERRORS.get(exc.status_code, (ErrorCode.HTTP_ERROR, str(exc.detail)))
    return to_response(Envelope(status="REJECTED", code=code.value, message=message), exc.status_code)


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    envelope = Envelope(
        status="FAILED",
        code=ErrorCode.INTERNAL_ERROR.value,
        message="Something went wrong on our side. Please try again in a moment.",
    )
    return to_response(envelope, 500)


def create_app() -> FastAPI:
    app = FastAPI(title="AegisCall Mock Insurance API", version="0.1.0")
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)

    @app.get("/health")
    def health() -> JSONResponse:
        return to_response(Envelope(status="SUCCESS", code="OK", message="Service is healthy."))

    for router in (customers.router, policies.router, verifications.router):
        app.include_router(router)
    return app


app = create_app()
