"""Application construction tests."""

from fastapi import FastAPI

from app.main import app, create_app


def test_module_app_is_fastapi_without_database_connection() -> None:
    assert isinstance(app, FastAPI)


def test_application_factory_returns_fastapi() -> None:
    created_app = create_app()

    assert isinstance(created_app, FastAPI)
    assert created_app.title == "Lending Nelson V2 API"
