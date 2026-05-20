import type { IntelHelperRail } from "@/types";

interface OperationsHelperRailProps {
  data: IntelHelperRail | null;
}

export function OperationsHelperRail({ data }: OperationsHelperRailProps) {
  if (!data) {
    return null;
  }

  return (
    <aside className="hidden w-60 shrink-0 border-l border-[#27272a] px-4 py-6 xl:block">
      <div className="space-y-5">
        <div>
          <p className="text-xs text-[#71717a]">今日重点</p>
          <p className="mt-1 text-2xl font-semibold text-white">{data.highlight_count}</p>
        </div>
        <div>
          <p className="text-xs text-[#71717a]">影响对象</p>
          <div className="mt-3 space-y-2">
            {Object.entries(data.top_counts).map(([label, count]) => (
              <div key={label} className="flex items-center justify-between text-sm text-[#d4d4d8]">
                <span>{label}</span>
                <span>{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
