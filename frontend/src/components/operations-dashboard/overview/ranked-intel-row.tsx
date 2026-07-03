import type { IntelItem } from "@/types";

interface RankedIntelRowProps {
  item: IntelItem;
  rank: number;
  compact?: boolean;
}

export function RankedIntelRow({
  item,
  rank,
  compact = false,
}: RankedIntelRowProps) {
  const primaryTarget = item.impact_targets[0];

  return (
    <a
      className="grid grid-cols-[24px_1fr] gap-2 rounded-md px-2 py-2 text-left transition-colors hover:bg-[#eef2f8]"
      href={item.original_url}
      target="_blank"
      rel="noreferrer"
    >
      <span className="rounded bg-[#eef2f8] py-0.5 text-center text-[13px] font-medium text-[#5a6474]">
        {rank}
      </span>
      <span className="min-w-0">
        <span
          className={`block text-[#17233f] ${
            compact ? "line-clamp-1 text-xs" : "line-clamp-2 text-sm"
          }`}
        >
          {item.title}
        </span>
        {primaryTarget ? (
          <span className="mt-1 inline-flex rounded bg-[#eef2f8] px-1.5 py-0.5 text-[12px] text-[#7b8494]">
            {primaryTarget}
          </span>
        ) : null}
      </span>
    </a>
  );
}
