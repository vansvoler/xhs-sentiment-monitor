import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.api import intel as intel_api
from src.collectors.intel_source_probe import ProbeResult
from src.collectors.university_sources import IntelSource
from src.models.intel import (
    IntelItem,
    IntelSourceSyncReport,
    IntelSourceSyncStatus,
    IntelSourceType,
)


def test_get_source_navigation_metadata(client: TestClient):
    response = client.get("/api/config/source-nav")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"key": "overview", "label": "总览"},
        {"key": "ucas", "label": "UCAS"},
        {"key": "university_site", "label": "海外大学官网"},
        {"key": "exam_board", "label": "考试局"},
        {"key": "visa_policy", "label": "签证政策"},
        {"key": "wechat_media", "label": "媒体公众号"},
    ]


def test_get_intel_overview_shape(client: TestClient):
    response = client.get("/api/intel/overview")

    assert response.status_code == 200
    payload = response.json()
    assert "sections" in payload
    assert "helper_rail" in payload
    assert payload["sections"][0]["source_key"] == "ucas"
    assert all(
        section["source_key"] != "xiaohongshu" for section in payload["sections"]
    )


def test_get_intel_source_feed_accepts_source_key(client: TestClient):
    response = client.get("/api/intel/sources/ucas")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_key"] == "ucas"
    assert len(payload["items"]) == 2


def test_get_intel_source_feed_prefers_live_university_items(
    client: TestClient,
    monkeypatch,
):
    async def fake_live_items(source_key: str, limit: int = 20):
        assert source_key == "university_site"
        return [
            IntelItem(
                item_id="oxford-news:https://example.com/story",
                source_type=IntelSourceType.UNIVERSITY_SITE,
                source_name="Oxford News",
                title="Oxford live story",
                summary_short="Oxford live story",
                summary_long="Oxford live story",
                published_at=datetime(2026, 5, 21, 8, 0, tzinfo=timezone.utc),
                collected_at=datetime(2026, 5, 21, 8, 5, tzinfo=timezone.utc),
                original_url="https://example.com/story",
                school_name="Oxford",
                source_group="重点学校",
            )
        ]

    monkeypatch.setattr(intel_api, "load_live_source_items", fake_live_items)
    monkeypatch.setattr(intel_api, "load_live_source_sync_reports", fake_sync_reports)

    response = client.get("/api/intel/sources/university_site")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_key"] == "university_site"
    assert payload["items"][0]["title"] == "Oxford live story"
    assert payload["sync_reports"][0]["status"] == "blocked"
    assert payload["sync_reports"][0]["source_id"] == "oxford-news"


async def fake_sync_reports(source_key: str):
    assert source_key == "university_site"
    return [
        IntelSourceSyncReport(
            source_id="oxford-news",
            source_type=IntelSourceType.UNIVERSITY_SITE,
            source_name="Oxford News",
            school_name="Oxford",
            status=IntelSourceSyncStatus.BLOCKED,
            item_count=0,
            error_message="Cloudflare challenge",
            synced_at=datetime(2026, 5, 21, 8, 10, tzinfo=timezone.utc),
        )
    ]


def test_get_source_sync_status_returns_reports(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setattr(intel_api, "load_live_source_sync_reports", fake_sync_reports)

    response = client.get("/api/intel/sources/university_site/sync-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_key"] == "university_site"
    assert payload["reports"][0]["source_id"] == "oxford-news"
    assert payload["reports"][0]["status"] == "blocked"


def test_probe_intel_source_endpoint_returns_recommendation(
    client: TestClient,
    monkeypatch,
):
    async def fake_probe(_session, url: str, **kwargs):
        assert url == "https://example.com/news"
        assert kwargs["source_type"] == "visa_policy"
        return ProbeResult(
            status="success",
            sample_count=3,
            message="页面中发现可用 feed。",
            recommended_source=IntelSource(
                source_id="example-com-news",
                source_type=IntelSourceType.VISA_POLICY,
                source_name="Example News",
                source_group="签证政策",
                adapter_type="feed",
                feed_url="https://example.com/news/feed.xml",
            ),
        )

    monkeypatch.setattr(intel_api, "probe_intel_source", fake_probe)

    response = client.post(
        "/api/intel/sources/probe",
        json={
            "url": "https://example.com/news",
            "source_type": "visa_policy",
            "source_name": "Example News",
            "source_group": "签证政策",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["sample_count"] == 3
    assert payload["recommended_source"]["source_id"] == "example-com-news"
    assert payload["recommended_source"]["adapter_type"] == "feed"
    assert (
        payload["recommended_source"]["feed_url"] == "https://example.com/news/feed.xml"
    )


def test_create_intel_source_appends_config(
    client: TestClient,
    monkeypatch,
    tmp_path,
):
    config_path = tmp_path / "intel_sources.json"
    config_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(intel_api, "CONFIG_PATH", config_path)

    async def fake_sync(source: IntelSource):
        report = IntelSourceSyncReport(
            source_id=source.source_id,
            source_type=source.source_type,
            source_name=source.source_name,
            status=IntelSourceSyncStatus.SUCCESS,
            item_count=2,
            synced_at=datetime(2026, 5, 28, 8, 10, tzinfo=timezone.utc),
        )
        return 2, report

    monkeypatch.setattr(intel_api, "sync_intel_source", fake_sync)

    response = client.post(
        "/api/intel/sources",
        json={
            "source_id": "example-com-news",
            "source_type": "visa_policy",
            "source_name": "Example News",
            "source_group": "签证政策",
            "adapter_type": "feed",
            "feed_url": "https://example.com/news/feed.xml",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source"]["source_id"] == "example-com-news"
    assert payload["sync_report"]["status"] == "success"
    assert payload["sync_report"]["item_count"] == 2
    assert payload["item_count"] == 2

    stored = json.loads(config_path.read_text(encoding="utf-8"))
    assert stored[0]["source_id"] == "example-com-news"
    assert stored[0]["source_type"] == "visa_policy"


def test_create_intel_source_rejects_duplicate_source_id(
    client: TestClient,
    monkeypatch,
    tmp_path,
):
    config_path = tmp_path / "intel_sources.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "source_id": "example-com-news",
                    "source_type": "visa_policy",
                    "source_name": "Example News",
                    "source_group": "签证政策",
                    "adapter_type": "feed",
                    "feed_url": "https://example.com/news/feed.xml",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(intel_api, "CONFIG_PATH", config_path)

    response = client.post(
        "/api/intel/sources",
        json={
            "source_id": "example-com-news",
            "source_type": "visa_policy",
            "source_name": "Example News",
            "source_group": "签证政策",
            "adapter_type": "feed",
            "feed_url": "https://example.com/news/feed.xml",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "信源已存在"


def test_create_intel_source_rejects_feed_without_feed_url(
    client: TestClient,
    monkeypatch,
    tmp_path,
):
    config_path = tmp_path / "intel_sources.json"
    config_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(intel_api, "CONFIG_PATH", config_path)

    response = client.post(
        "/api/intel/sources",
        json={
            "source_id": "broken-feed",
            "source_type": "visa_policy",
            "source_name": "Broken Feed",
            "source_group": "签证政策",
            "adapter_type": "feed",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "feed 类型信源必须包含 feed_url"
