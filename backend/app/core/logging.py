import logging

import structlog


def configure_logging(level: str = "INFO") -> None:
    """구조화(JSON) 로그. 사용자 입력 원문·PII는 기록하지 않는다."""
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ]
    )
