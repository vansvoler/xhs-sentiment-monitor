import type {
  IntelItem,
  IntelOverviewResponse,
  IntelSourceFeedKey,
  IntelSourceSyncReport,
} from "@/types";

import { SourceTile } from "./source-tile";
import { deriveUniversityTiles, type UniversityTileData } from "./university-tiles";

const SOURCE_SUBTITLES: Record<IntelSourceFeedKey, string> = {
  ucas: "政策与申请节点",
  university_site: "重点学校官网动态",
  exam_board: "考试安排与成绩政策",
  visa_policy: "签证规则与材料要求",
  wechat_media: "媒体与垂类解读",
};

interface NewsNowOverviewProps {
  data: IntelOverviewResponse;
  universityItems: IntelItem[];
  universitySyncReports: IntelSourceSyncReport[];
  onOpenSource: (sourceKey: IntelSourceFeedKey) => void;
}

const STATUS_LABELS: Record<UniversityTileData["status"], string> = {
  success: "同步成功",
  blocked: "被拦截",
  error: "同步失败",
};

const STATUS_STYLES: Record<UniversityTileData["status"], string> = {
  success: "bg-emerald-400/15 text-[#15803d]",
  blocked: "bg-amber-400/15 text-[#b45309]",
  error: "bg-rose-400/15 text-[#b91c1c]",
};

function UniversitySchoolTile({
  tile,
  onOpenSource,
}: {
  tile: UniversityTileData;
  onOpenSource: (sourceKey: IntelSourceFeedKey) => void;
}) {
  const visibleItems = tile.items.slice(0, 4);

  return (
    <article className="rounded-lg border border-[#dce1e9] bg-[#ffffff] p-3">
      <header className="mb-3 flex items-start justify-between gap-3">
        <button
          className="min-w-0 text-left"
          onClick={() => onOpenSource("university_site")}
          type="button"
        >
          <span className="block truncate text-sm font-semibold text-[#17233f]">
            {tile.title}
          </span>
          <span className="mt-1 block truncate text-[13px] text-[#5a6474]">
            {tile.sourceName} · {tile.totalItems} 条
          </span>
        </button>
        <span
          className={`shrink-0 rounded px-2 py-1 text-[13px] ${STATUS_STYLES[tile.status]}`}
        >
          {STATUS_LABELS[tile.status]}
        </span>
      </header>

      <div className="space-y-2">
        {visibleItems.map((item) => (
          <a
            key={item.item_id}
            className="block rounded-md px-2 py-2 text-xs text-[#5a6474] transition-colors hover:bg-[#eef2f8]"
            href={item.original_url}
            target="_blank"
            rel="noreferrer"
          >
            <span className="line-clamp-2">{item.title}</span>
          </a>
        ))}
        {visibleItems.length === 0 ? (
          <div className="rounded-md border border-dashed border-[#dce1e9] px-2 py-4 text-xs text-[#7b8494]">
            {tile.errorMessage ?? "暂无可展示条目"}
          </div>
        ) : null}
      </div>
    </article>
  );
}

export function NewsNowOverview({
  data,
  universityItems,
  universitySyncReports,
  onOpenSource,
}: NewsNowOverviewProps) {
  const universityReportCount = universitySyncReports.length;
  const universityTiles = deriveUniversityTiles(
    universityItems,
    universitySyncReports,
  );

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[#7b8494]">
            Intelligence Radar
          </p>
          <h1 className="mt-1 text-xl font-semibold text-[#17233f]">
            News Now 留学情报
          </h1>
        </div>
        <div className="flex rounded-full border border-[#dce1e9] bg-[#eef2f8] p-1 text-xs">
          <span className="rounded-full bg-[#eef2f8] px-3 py-1 text-[#17233f]">
            最新
          </span>
          <span className="px-3 py-1 text-[#7b8494]">最热</span>
          <span className="px-3 py-1 text-[#7b8494]">待读</span>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {data.sections.map((section) => (
          <SourceTile
            key={section.source_key}
            sourceKey={section.source_key}
            title={section.source_label}
            subtitle={
              section.source_key === "university_site" && universityReportCount > 0
                ? `${universityReportCount} 个学校同步状态`
                : SOURCE_SUBTITLES[section.source_key]
            }
            items={section.preview_items}
            onOpen={onOpenSource}
          />
        ))}
      </div>

      {universityTiles.length > 0 ? (
        <section className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-[#17233f]">重点学校官网</h2>
            <p className="mt-1 text-xs text-[#7b8494]">
              按配置来源拆分同步结果
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {universityTiles.map((tile) => (
              <UniversitySchoolTile
                key={tile.key}
                tile={tile}
                onOpenSource={onOpenSource}
              />
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
