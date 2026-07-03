import type { IntelHelperRail } from "@/types";

interface OperationsHelperRailProps {
  data: IntelHelperRail | null;
}

export function OperationsHelperRail({ data }: OperationsHelperRailProps) {
  if (!data) {
    return null;
  }

  return (
    <aside className="hidden w-64 shrink-0 rounded-[10px] border border-[#dce1e9] bg-[#ffffff] px-4 py-5 xl:block">
      <div className="space-y-5">
        <div>
          <p className="text-xs text-[#7b8494]">今日重点</p>
          <p className="mt-1 text-3xl font-semibold text-[#17233f]">
            {data.highlight_count}
          </p>
        </div>
        <div>
          <p className="text-xs text-[#7b8494]">影响对象</p>
          <div className="mt-3 space-y-2">
            {Object.entries(data.top_counts).map(([label, count]) => (
              <div
                key={label}
                className="flex items-center justify-between rounded-md bg-[#eef2f8] px-3 py-2 text-sm text-[#4b5563]"
              >
                <span>{label}</span>
                <span className="text-[#17233f]">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
