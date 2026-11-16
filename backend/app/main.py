from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name)
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
