import type { ReactNode } from "react";

import type { IntelHelperRail, IntelSourceKey, SourceNavItem } from "@/types";

import { OperationsHelperRail } from "./helper-rail";
import { OperationsSidebar } from "./sidebar";

interface DashboardShellProps {
  items: SourceNavItem[];
  activeKey: IntelSourceKey;
  helperRail: IntelHelperRail | null;
  onChange: (key: IntelSourceKey) => void;
  action?: ReactNode;
  children: ReactNode;
}

export function DashboardShell({
  items,
  activeKey,
  helperRail,
  onChange,
  action,
  children,
}: DashboardShellProps) {
  return (
    <div className="min-h-screen bg-[#f4f6fa] text-[#1f2a44]">
      <main className="mx-auto flex min-h-screen max-w-[1920px] gap-4 px-4 py-4">
        <OperationsSidebar items={items} activeKey={activeKey} onChange={onChange} />
        <section className="min-w-0 flex-1 space-y-4">
          {action && <div className="flex justify-end">{action}</div>}
          {children}
        </section>
        <OperationsHelperRail data={helperRail} />
      </main>
    </div>
  );
}
