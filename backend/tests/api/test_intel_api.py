from fastapi.testclient import TestClient


def test_get_source_navigation_metadata(client: TestClient):
    response = client.get("/api/config/source-nav")

    assert response.status_code == 200
    assert response.json()["items"][0]["key"] == "overview"


def test_get_intel_overview_shape(client: TestClient):
    response = client.get("/api/intel/overview")

    assert response.status_code == 200
    payload = response.json()
    assert "sections" in payload
    assert "helper_rail" in payload
    assert payload["sections"][0]["source_key"] == "xiaohongshu"


def test_get_intel_source_feed_accepts_source_key(client: TestClient):
    response = client.get("/api/intel/sources/ucas")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_key"] == "ucas"
    assert len(payload["items"]) == 2
