"""运营情报信源配置写入服务。"""

import json
from pathlib import Path

from src.collectors.university_sources import IntelSource, load_intel_sources_from_file


class DuplicateIntelSourceError(ValueError):
    """信源 ID 已存在。"""


def source_exists(sources: list[IntelSource], source_id: str) -> bool:
    """判断信源 ID 是否已存在。"""

    return any(source.source_id == source_id for source in sources)


def load_existing_sources(path: Path) -> list[IntelSource]:
    """读取现有配置；文件不存在时按空配置处理。"""

    if not path.exists():
        return []

    return load_intel_sources_from_file(path)


def atomic_write_sources(path: Path, sources: list[IntelSource]) -> None:
    """以临时文件替换方式写入信源配置。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [source.model_dump(mode="json", exclude_none=True) for source in sources]
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def append_intel_source(path: Path, source: IntelSource) -> IntelSource:
    """追加单个信源配置。"""

    sources = load_existing_sources(path)
    if source_exists(sources, source.source_id):
        raise DuplicateIntelSourceError(source.source_id)

    atomic_write_sources(path, [*sources, source])
    return source
