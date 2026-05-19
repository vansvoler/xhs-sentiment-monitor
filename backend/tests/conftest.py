"""
Backend pytest fixtures.
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    async def noop_async() -> None:
        return None

    def noop() -> None:
        return None

    async def noop_heartbeat() -> None:
        return None

    async def noop_disconnect_all() -> None:
        return None

    monkeypatch.setattr(main, "init_mongodb", noop_async)
    monkeypatch.setattr(main, "close_mongodb", noop_async)
    monkeypatch.setattr(main, "start_scheduler", noop)
    monkeypatch.setattr(main, "stop_scheduler", noop)
    monkeypatch.setattr(main.websocket_manager, "heartbeat", noop_heartbeat)
    monkeypatch.setattr(main.websocket_manager, "disconnect_all", noop_disconnect_all)

    with TestClient(main.app) as test_client:
        yield test_client
