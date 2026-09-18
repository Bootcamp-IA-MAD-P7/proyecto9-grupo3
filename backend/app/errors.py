"""Never echo submitted credentials through validation error payloads."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    # Nested locations and extra field names are also client-controlled.
    # Retain only the trusted request source, never submitted keys or values.
    details = [
        {
            "loc": [item["loc"][0]]
            if item["loc"] and item["loc"][0] in {"body", "path", "query", "header", "cookie"}
            else [],
            "msg": "Invalid request value",
            "type": item["type"],
        }
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})
