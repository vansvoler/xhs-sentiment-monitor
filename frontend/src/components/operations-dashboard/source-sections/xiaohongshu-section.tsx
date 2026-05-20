import type { IntelSourceResponse } from "@/types";

import { SourceHeader } from "../source-header";
import { SourceList } from "../source-list";

export function XiaohongshuSection({ data }: { data: IntelSourceResponse }) {
  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <div className="rounded-[10px] border border-[#27272a] bg-[#111113] px-4 py-3 text-sm text-[#a1a1aa]">
        这里先看正在升温的讨论、问答和经验帖。重点不是官方确定性，而是用户此刻在关心什么。
      </div>
      <SourceList items={data.items} />
    </section>
  );
}
