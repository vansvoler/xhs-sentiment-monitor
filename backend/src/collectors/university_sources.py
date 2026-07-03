"""运营情报官网信源配置。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.models.intel import IntelItem, IntelSourceType

AdapterType = Literal["feed", "listing", "rss", "json_feed", "html_listing"]


class ListingSelectors(BaseModel):
    """HTML 列表页解析选择器。"""

    item: str
    title: str
    url: str
    summary: str | None = None
    date: str | None = None


class IntelSource(BaseModel):
    """单个官网/机构情报信源配置。"""

    source_id: str
    source_type: IntelSourceType = IntelSourceType.UNIVERSITY_SITE
    school_name: str | None = None
    adapter_type: AdapterType
    source_group: str
    source_name: str
    feed_url: str | None = None
    listing_url: str | None = None
    selectors: ListingSelectors | None = None
    enabled: bool = True

    def build_item(
        self,
        *,
        title: str,
        link: str,
        summary: str,
        published_at: datetime,
        collected_at: datetime,
        external_id: str | None = None,
        content_html: str | None = None,
        impact_targets: list[str] | None = None,
    ) -> IntelItem:
        """构建统一情报项。"""

        summary_short = summary[:80] if summary else title
        summary_long = summary[:180] if summary else title

        return IntelItem(
            item_id=f"{self.source_id}:{link}",
            source_type=self.source_type,
            source_name=self.source_name,
            title=title,
            summary_short=summary_short,
            summary_long=summary_long,
            impact_targets=impact_targets or [],
            published_at=published_at,
            collected_at=collected_at,
            original_url=link,
            school_name=self.school_name,
            source_group=self.source_group,
            external_id=external_id,
            content_html=content_html,
        )


UniversitySource = IntelSource

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "intel_sources.json"


FALLBACK_SOURCES = [
    UniversitySource(
        source_id="oxford-news",
        school_name="Oxford",
        source_type=IntelSourceType.UNIVERSITY_SITE,
        adapter_type="listing",
        source_group="重点学校",
        source_name="Oxford News",
        listing_url="https://www.ox.ac.uk/News-listing?category=All",
    ),
    UniversitySource(
        source_id="cambridge-news",
        school_name="Cambridge",
        source_type=IntelSourceType.UNIVERSITY_SITE,
        adapter_type="feed",
        source_group="重点学校",
        source_name="Cambridge News",
        feed_url="https://www.cam.ac.uk/news/feed",
    ),
    UniversitySource(
        source_id="ucl-news",
        school_name="UCL",
        source_type=IntelSourceType.UNIVERSITY_SITE,
        adapter_type="feed",
        source_group="重点学校",
        source_name="UCL News",
        feed_url=(
            "https://cms-feed.ucl.ac.uk/s/search.json"
            "?collection=drupal-push-news-news&profile=_default&size=20"
        ),
    ),
    UniversitySource(
        source_id="imperial-news",
        school_name="Imperial",
        source_type=IntelSourceType.UNIVERSITY_SITE,
        adapter_type="feed",
        source_group="重点学校",
        source_name="Imperial News",
        feed_url=(
            "https://www.imperial.ac.uk/news/articles/feeds/"
            "admin-services/all-imperial-news/articles.json"
        ),
    ),
]


def load_intel_sources_from_file(path: Path) -> list[IntelSource]:
    """从 JSON 文件读取官网/机构信源配置。"""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("intel_sources.json must contain a list")

    return [IntelSource.model_validate(item) for item in payload]


def load_intel_sources(path: Path = CONFIG_PATH) -> list[IntelSource]:
    """读取配置化信源，文件缺失时回退到内置第一批来源。"""

    if not path.exists():
        return FALLBACK_SOURCES

    sources = load_intel_sources_from_file(path)
    return sources or FALLBACK_SOURCES


UNIVERSITY_SOURCES = load_intel_sources()
