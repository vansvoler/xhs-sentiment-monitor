import type { IntelOverviewResponse } from "@/types";

import { IntelCard } from "./intel-card";

export function OverviewPanel({ data }: { data: IntelOverviewResponse }) {
  return (
    <section className="space-y-6">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-[10px] border border-[#27272a] bg-[#111113] p-4">
          <p className="text-xs text-[#71717a]">今日新增</p>
          <p className="mt-2 text-2xl font-semibold text-white">
            {data.sections.reduce((sum, section) => sum + section.total_items, 0)}
          </p>
        </div>
        <div className="rounded-[10px] border border-[#27272a] bg-[#111113] p-4">
          <p className="text-xs text-[#71717a]">已读</p>
          <p className="mt-2 text-2xl font-semibold text-white">0</p>
        </div>
        <div className="rounded-[10px] border border-[#27272a] bg-[#111113] p-4">
          <p className="text-xs text-[#71717a]">来源状态</p>
          <p className="mt-2 text-2xl font-semibold text-white">4/4</p>
        </div>
      </div>

      {data.sections.map((section) => (
        <div key={section.source_key} className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-white">{section.source_label}</h2>
            <span className="text-xs text-[#71717a]">今日 {section.total_items} 条</span>
          </div>
          {section.preview_items.length === 0 ? (
            <p className="rounded-[10px] border border-dashed border-[#27272a] px-4 py-5 text-sm text-[#71717a]">
              今日暂无新增
            </p>
          ) : (
            <div className="space-y-3">
              {section.preview_items.map((item) => (
                <IntelCard key={item.item_id} item={item} compact />
              ))}
            </div>
          )}
        </div>
      ))}
    </section>
  );
}
