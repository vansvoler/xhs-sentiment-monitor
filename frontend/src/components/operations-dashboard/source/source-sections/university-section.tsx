import type { IntelSourceResponse, IntelSourceSyncReport } from "@/types";

import { SourceHeader } from "../source-header";
import { SourceList } from "../source-list";

const STATUS_STYLES = {
  success: "border-emerald-500/30 bg-emerald-500/10 text-[#15803d]",
  blocked: "border-amber-500/30 bg-amber-500/10 text-[#b45309]",
  error: "border-rose-500/30 bg-rose-500/10 text-[#b91c1c]",
} as const;

const STATUS_LABELS = {
  success: "正常",
  blocked: "被拦截",
  error: "失败",
} as const;

function StatusCard({ report }: { report: IntelSourceSyncReport }) {
  return (
    <article
      className={`rounded-[10px] border px-4 py-3 ${
        STATUS_STYLES[report.status]
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[#17233f]">{report.school_name ?? report.source_name}</p>
          <p className="mt-1 text-xs text-inherit">{STATUS_LABELS[report.status]}</p>
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold text-[#17233f]">{report.item_count}</p>
          <p className="text-xs text-inherit">本轮条目</p>
        </div>
      </div>
      {report.error_message ? (
        <p className="mt-3 text-xs leading-5 text-[#4b5563]">{report.error_message}</p>
      ) : null}
    </article>
  );
}

export function UniversitySection({ data }: { data: IntelSourceResponse }) {
  const keySchoolCount = new Set(
    data.items
      .filter((item) => item.source_group === "重点学校" && item.school_name)
      .map((item) => item.school_name as string),
  ).size;

  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <div className="rounded-[10px] border border-[#dce1e9] bg-[#ffffff] px-4 py-3 text-sm text-[#5a6474]">
        重点学校更新 {keySchoolCount} 所。这里应先扫重点学校，再看全部学校里的奖学金、招生动态和开放日变化。
      </div>
      {data.sync_reports.length > 0 ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {data.sync_reports.map((report) => (
            <StatusCard key={report.source_id} report={report} />
          ))}
        </div>
      ) : null}
      <SourceList items={data.items} />
    </section>
  );
}
