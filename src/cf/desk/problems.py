"""Errors Desk shows to the Author: an English `detail` for the CLI and logs, plus a stable `code` and its
`params`, by which the frontend translates the message."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class Problem(HTTPException):
    def __init__(self, status_code: int, code: str, detail: str, /, **params: Any) -> None:
        super().__init__(status_code, detail)
        self.code = code
        self.params = params


def body(code: str, detail: str, params: dict | None = None, /, **extra: Any) -> dict:
    return {"detail": detail, "code": code, "params": params or {}, **extra}


def install(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def problem(_: Request, exc: Problem) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=body(exc.code, exc.detail, exc.params))

    @app.exception_handler(RequestValidationError)
    async def invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        where = [".".join(str(part) for part in e.get("loc", ())) for e in errors]
        detail = "invalid request: " + "; ".join(f"{w}: {e.get('msg', '')}" for w, e in zip(where, errors))
        return JSONResponse(status_code=422, content=body("request_invalid", detail, {"fields": ", ".join(where)}))
