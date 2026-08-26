"""Domain exceptions and their JSON representations."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFound(Exception):
    def __init__(self, entity: str, identifier: object) -> None:
        super().__init__(f"{entity} {identifier} does not exist")
        self.entity = entity
        self.identifier = identifier


class Conflict(Exception):
    """A write the data model refuses, e.g. a duplicate name."""


class InvalidReference(Exception):
    """A write pointing at a row that does not exist, e.g. an unknown category."""


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFound)
    async def _not_found(request: Request, error: NotFound) -> JSONResponse:
        return JSONResponse({"error": "not_found", "message": str(error)}, status_code=404)

    @app.exception_handler(Conflict)
    async def _conflict(request: Request, error: Conflict) -> JSONResponse:
        return JSONResponse({"error": "conflict", "message": str(error)}, status_code=409)

    @app.exception_handler(InvalidReference)
    async def _invalid_reference(request: Request, error: InvalidReference) -> JSONResponse:
        return JSONResponse(
            {"error": "invalid_reference", "message": str(error)}, status_code=422
        )
