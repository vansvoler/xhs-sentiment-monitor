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
    <aside className="hidden w-56 shrink-0 rounded-[10px] border border-[#dce1e9] bg-[#ffffff] p-4 lg:block">
      <div className="mb-5 flex items-center gap-3">
        <div className="grid size-9 place-items-center rounded-md bg-[#1e51a2] text-[13px] font-bold text-white">
          AI
        </div>
        <div>
          <p className="text-sm font-bold leading-none text-[#17233f]">News</p>
          <p className="text-sm font-bold leading-none text-[#17233f]">Now</p>
        </div>
      </div>
      <nav className="space-y-1">
        {items.map((item) => {
          const isActive = item.key === activeKey;

          return (
            <button
              key={item.key}
              onClick={() => onChange(item.key)}
              className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                isActive
                  ? "bg-[#eef2f8] text-[#17233f]"
                  : "text-[#5a6474] hover:bg-[#eef2f8] hover:text-[#17233f]"
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
