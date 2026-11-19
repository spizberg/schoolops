"""ASGI entrypoint: ``uvicorn schoolops.main:app``."""

from schoolops.factory import create_app

app = create_app()
