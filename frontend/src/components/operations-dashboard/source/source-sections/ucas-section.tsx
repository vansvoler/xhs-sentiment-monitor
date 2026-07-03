import type { IntelSourceResponse } from "@/types";

import { SourceHeader } from "../source-header";
import { SourceList } from "../source-list";

export function UcasSection({ data }: { data: IntelSourceResponse }) {
  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <div className="rounded-[10px] border border-[#dce1e9] bg-[#ffffff] px-4 py-3 text-sm text-[#5a6474]">
        这里优先处理政策、时间节点和申请流程变更。看到关键更新时，默认应考虑是否要做提醒类内容。
      </div>
      <SourceList items={data.items} />
    </section>
  );
}
