import type { IntelItem } from "@/types";

import { IntelCard } from "./intel-card";

interface SourceListProps {
  items: IntelItem[];
}

export function SourceList({ items }: SourceListProps) {
  if (items.length === 0) {
    return (
      <p className="rounded-[10px] border border-dashed border-[#dce1e9] px-4 py-5 text-sm text-[#7b8494]">
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
