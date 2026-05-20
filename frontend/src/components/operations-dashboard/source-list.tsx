import type { IntelItem } from "@/types";

import { IntelCard } from "./intel-card";

interface SourceListProps {
  items: IntelItem[];
}

export function SourceList({ items }: SourceListProps) {
  if (items.length === 0) {
    return (
      <p className="rounded-[10px] border border-dashed border-[#27272a] px-4 py-5 text-sm text-[#71717a]">
        今日暂无新增
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <IntelCard key={item.item_id} item={item} />
      ))}
    </div>
  );
}
