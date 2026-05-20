import type { IntelSourceKey, SourceNavItem } from "@/types";

interface OperationsSidebarProps {
  items: SourceNavItem[];
  activeKey: IntelSourceKey;
  onChange: (key: IntelSourceKey) => void;
}

export function OperationsSidebar({
  items,
  activeKey,
  onChange,
}: OperationsSidebarProps) {
  return (
    <aside className="hidden w-56 shrink-0 border-r border-[#27272a] p-4 lg:block">
      <div className="mb-4">
        <p className="text-xs uppercase tracking-[0.2em] text-[#71717a]">Operations</p>
        <h1 className="mt-2 text-lg font-semibold text-white">今日新增情报</h1>
      </div>
      <nav className="space-y-1">
        {items.map((item) => {
          const isActive = item.key === activeKey;

          return (
            <button
              key={item.key}
              onClick={() => onChange(item.key)}
              className={`w-full rounded px-3 py-2 text-left text-sm transition-colors ${
                isActive
                  ? "bg-[#18181b] text-white"
                  : "text-[#a1a1aa] hover:bg-[#111113] hover:text-white"
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
