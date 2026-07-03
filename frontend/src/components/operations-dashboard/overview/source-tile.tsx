import { MoreVertical, RefreshCcw, Star } from "lucide-react";

import type { IntelItem, IntelSourceFeedKey } from "@/types";

import { RankedIntelRow } from "./ranked-intel-row";

// 每个信源的品牌色徽章
const BADGE_BG: Record<IntelSourceFeedKey, string> = {
  ucas: "#1e51a2",
  university_site: "#16a34a",
  exam_board: "#727171",
  visa_policy: "#ea5457",
  wechat_media: "#26b7bc",
};

const SOURCE_INITIALS: Record<IntelSourceFeedKey, string> = {
  ucas: "U",
  university_site: "校",
  exam_board: "考",
  visa_policy: "签",
  wechat_media: "媒",
};

interface SourceTileProps {
  sourceKey: IntelSourceFeedKey;
  title: string;
  subtitle: string;
  items: IntelItem[];
  onOpen: (sourceKey: IntelSourceFeedKey) => void;
}

export function SourceTile({
  sourceKey,
  title,
  subtitle,
  items,
  onOpen,
}: SourceTileProps) {
  const visibleItems = items.slice(0, 8);

  return (
    <article className="rounded-[10px] border border-[#dce1e9] bg-white p-3">
      <header className="mb-3 flex items-center justify-between gap-3">
        <button
          className="flex min-w-0 items-center gap-2 text-left"
          onClick={() => onOpen(sourceKey)}
          type="button"
        >
          <span
            className="grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold text-white"
            style={{ background: BADGE_BG[sourceKey] }}
          >
            {SOURCE_INITIALS[sourceKey]}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-[#17233f]">
              {title}
            </span>
            <span className="block truncate text-[13px] text-[#7b8494]">
              {subtitle}
            </span>
          </span>
        </button>
        <div className="flex items-center gap-1 text-[#9aa1ac]">
          <RefreshCcw className="size-4" />
          <Star className="size-4" />
          <MoreVertical className="size-4" />
        </div>
      </header>

      <div className="min-h-[250px] rounded-lg bg-[#f4f6fa] p-1">
        {visibleItems.length === 0 ? (
          <div className="grid h-full min-h-[220px] place-items-center rounded-md border border-dashed border-[#dce1e9] text-xs text-[#7b8494]">
            今日暂无新增
          </div>
        ) : (
          visibleItems.map((item, index) => (
            <RankedIntelRow
              key={item.item_id}
              item={item}
              rank={index + 1}
              compact
            />
          ))
        )}
      </div>
    </article>
  );
}
