from contextlib import contextmanager
from typing import Any

import elasticapm
from elasticapm.contrib.starlette import ElasticAPM, make_apm_client
from fastapi import FastAPI

from .configs import settings


def init_apm():
    if settings.APM_URL is None:
        return None
    apm_config = {
        "SERVICE_NAME": settings.PROJECT_NAME,
        "API_KEY": settings.APM_TOKEN,
        "SERVER_URL": settings.APM_URL,
        "ENVIRONMENT": settings.ENV.lower(),
        "CAPTURE_BODY": "all",
        "TRANSACTION_SAMPLE_RATE": 1.0,
        "VERIFY_SERVER_CERT": False,
    }

    return make_apm_client(apm_config)


apm_client = init_apm()


@contextmanager
def safe_capture_transaction(name, type: str):
    """Safely captures a transaction for APM monitoring."""
    if apm_client is not None:
        apm_client.begin_transaction(transaction_type=type)
        try:
            yield
            apm_client.end_transaction(name=name, result="success")
        except Exception:
            apm_client.capture_exception()
            apm_client.end_transaction(name=name, result="failure")
            raise
    else:
        yield


@contextmanager
def safe_capture_span(name, type: str = "custom"):
    """Safely captures a custom span for APM monitoring."""
    if apm_client is not None:
        with elasticapm.capture_span(name=name, span_type=type):
            yield
    else:
        yield


def safe_capture_exception(
    exc_info: Any | None = None, handled: bool = True, **kwargs: Any
):
    """Safely captures an exception for APM monitoring."""
    if apm_client is not None:
        apm_client.capture_exception(exc_info=exc_info, handled=handled, kwargs=kwargs)


def safe_set_context(data: dict, key: str):
    """Safely sets a custom context for APM monitoring."""
    if apm_client is not None:
        elasticapm.set_context(data, key=key)
