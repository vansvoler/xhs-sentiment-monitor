from src.collectors.university_sources import (
    UNIVERSITY_SOURCES,
    load_intel_sources_from_file,
)
from src.models.intel import IntelSourceType


def test_university_sources_cover_first_wave_sites():
    source_ids = [source.source_id for source in UNIVERSITY_SOURCES]

    assert source_ids[:4] == [
        "oxford-news",
        "cambridge-news",
        "ucl-news",
        "imperial-news",
    ]
    first_wave_sources = {source.source_id: source for source in UNIVERSITY_SOURCES[:4]}
    assert first_wave_sources["oxford-news"].adapter_type == "listing"
    assert first_wave_sources["cambridge-news"].adapter_type == "feed"
    assert first_wave_sources["ucl-news"].adapter_type == "feed"
    assert first_wave_sources["imperial-news"].adapter_type == "feed"


def test_load_intel_sources_from_file_supports_configured_html_source(tmp_path):
    config_path = tmp_path / "intel_sources.json"
    config_path.write_text(
        """
        [
          {
            "source_id": "ukvi-news",
            "source_type": "visa_policy",
            "source_name": "UKVI News",
            "source_group": "签证政策",
            "adapter_type": "html_listing",
            "listing_url": "https://www.gov.uk/search/news-and-communications",
            "selectors": {
              "item": "article",
              "title": "h2 a",
              "url": "h2 a",
              "summary": "p",
              "date": "time"
            }
          }
        ]
        """,
        encoding="utf-8",
    )

    sources = load_intel_sources_from_file(config_path)

    assert len(sources) == 1
    assert sources[0].source_id == "ukvi-news"
    assert sources[0].source_type == IntelSourceType.VISA_POLICY
    assert sources[0].adapter_type == "html_listing"
    assert sources[0].selectors is not None
    assert sources[0].selectors.item == "article"
