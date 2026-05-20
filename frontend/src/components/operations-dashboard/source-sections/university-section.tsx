import type { IntelSourceResponse } from "@/types";

import { SourceHeader } from "../source-header";
import { SourceList } from "../source-list";

export function UniversitySection({ data }: { data: IntelSourceResponse }) {
  const keySchoolCount = new Set(
    data.items
      .filter((item) => item.source_group === "重点学校" && item.school_name)
      .map((item) => item.school_name as string),
  ).size;

  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <div className="rounded-[10px] border border-[#27272a] bg-[#111113] px-4 py-3 text-sm text-[#a1a1aa]">
        重点学校更新 {keySchoolCount} 所。这里应先扫重点学校，再看全部学校里的奖学金、招生动态和开放日变化。
      </div>
      <SourceList items={data.items} />
    </section>
  );
}
