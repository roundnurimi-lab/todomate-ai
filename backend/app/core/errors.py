from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """도메인 예외 기본 클래스. 응답 형식: {"code": ..., "message": ...}"""

    status_code: int = 400
    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )
