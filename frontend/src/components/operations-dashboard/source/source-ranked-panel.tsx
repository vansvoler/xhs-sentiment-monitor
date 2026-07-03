import type { IntelItem, IntelSourceResponse } from "@/types";

import { SourceHeader } from "./source-header";

function SourceDetailRow({ item, rank }: { item: IntelItem; rank: number }) {
  const targets = item.impact_targets.slice(0, 2);

  return (
    <a
      className="grid grid-cols-[34px_1fr_auto] gap-3 rounded-lg px-3 py-3 text-left transition-colors hover:bg-[#eef2f8]"
      href={item.original_url}
      target="_blank"
      rel="noreferrer"
    >
      <span className="rounded bg-[#eef2f8] py-1 text-center text-xs font-semibold text-[#5a6474]">
        {rank}
      </span>
      <span className="min-w-0">
        <span className="block line-clamp-2 text-sm font-medium text-[#17233f]">
          {item.title}
        </span>
        <span className="mt-1 block line-clamp-1 text-xs text-[#5a6474]">
          {item.school_name ?? item.source_name}
        </span>
      </span>
      <span className="hidden items-center gap-1 md:flex">
        {targets.map((target) => (
          <span
            key={target}
            className="rounded bg-[#eef2f8] px-2 py-1 text-[13px] text-[#7b8494]"
          >
            {target}
          </span>
        ))}
      </span>
    </a>
  );
}

function SourceSyncStrip({ data }: { data: IntelSourceResponse }) {
  if (data.sync_reports.length === 0) {
    return null;
  }

  const counts = data.sync_reports.reduce(
    (acc, report) => ({
      ...acc,
      [report.status]: acc[report.status] + 1,
    }),
    { success: 0, blocked: 0, error: 0 },
  );

  return (
    <div className="grid gap-2 md:grid-cols-3">
      <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-sm text-[#15803d]">
        正常 {counts.success}
      </div>
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-[#b45309]">
        被拦截 {counts.blocked}
      </div>
      <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-[#b91c1c]">
        失败 {counts.error}
      </div>
    </div>
  );
}

export function SourceRankedPanel({ data }: { data: IntelSourceResponse }) {
  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <SourceSyncStrip data={data} />
      <div className="rounded-[10px] border border-[#dce1e9] bg-[#ffffff] p-2">
        {data.items.length === 0 ? (
          <div className="grid min-h-[260px] place-items-center rounded-lg border border-dashed border-[#dce1e9] text-sm text-[#7b8494]">
            今日暂无新增
          </div>
        ) : (
          data.items.map((item, index) => (
            <SourceDetailRow
              key={item.item_id}
              item={item}
              rank={index + 1}
            />
          ))
        )}
      </div>
    </section>
  );
}
