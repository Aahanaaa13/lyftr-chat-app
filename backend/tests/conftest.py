import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


def _build(tmp_path, monkeypatch, simulation):
    monkeypatch.setenv("LLM_API_KEYS", "mock-key-1,mock-key-2")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("ENABLE_FAILURE_SIMULATION", simulation)
    return create_app(load_settings())


@pytest.fixture
def client(tmp_path, monkeypatch):
    with TestClient(_build(tmp_path, monkeypatch, "true")) as c:
        yield c


@pytest.fixture
def client_no_sim(tmp_path, monkeypatch):
    with TestClient(_build(tmp_path, monkeypatch, "false")) as c:
        yield c
