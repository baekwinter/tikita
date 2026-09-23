import importlib
import sys

import pytest

from .conftest import open_event


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DG_TEST_MODE", "true")
    monkeypatch.setenv("DG_TEST_GUILD_ID", "42")
    monkeypatch.setenv("DG_TEST_CHANNEL_ID", "43")
    monkeypatch.setenv("DG_WEB_DEV_LOGIN", "true")
    monkeypatch.setenv("DG_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("DG_ADMIN_USER_IDS", "7")
    monkeypatch.delenv("DG_SESSION_SECRET", raising=False)
    sys.modules.pop("api.app", None)
    mod = importlib.import_module("api.app")
    from fastapi.testclient import TestClient
    c = TestClient(mod.app, follow_redirects=False)
    c.mod = mod
    return c


def login(client, uid=10):
    r = client.get(f"/api/auth/dev?uid={uid}&name=tester")
    assert r.status_code in (302, 307)


def test_requires_login(client):
    assert client.get("/api/state").status_code == 401


def test_state_and_ask(client):
    open_event(client.mod.db, 4)
    login(client)
    s = client.get("/api/state").json()
    assert s["case"]["current_episode"] == 4
    assert "answers" not in str(s.get("final", {}).get("form"))
    r = client.post("/api/ask", json={"text": "반휘혈은 온하늘을 좋아하나요?"})
    assert r.status_code == 200 and r.json()["verdict"] == "YES"
    r2 = client.post("/api/ask", json={"text": "차세리가 범인이야?"})
    assert r2.status_code == 409 and r2.json()["code"] == "cooldown"


def test_locked_evidence_and_media_are_404_or_409(client):
    open_event(client.mod.db, 1)
    login(client)
    assert client.post("/api/evidence/E-08/investigate").status_code == 409
    assert client.get("/api/media/evidence/E-08").status_code == 404
    assert client.get("/api/media/episode/5").status_code == 404


def test_before_start_blocks_play(client):
    login(client)
    r = client.post("/api/ask", json={"text": "반휘혈은 온하늘을 좋아하나요?"})
    assert r.status_code == 409 and r.json()["code"] == "before_start"


def test_admin_export(client):
    login(client, 10)
    assert client.get("/api/admin/export.csv").status_code == 403
    login(client, 7)
    r = client.get("/api/admin/export.csv")
    assert r.status_code == 200 and "user_id" in r.text
