import type { IntelSourceResponse } from "@/types";

import { SourceHeader } from "../source-header";
import { SourceList } from "../source-list";

export function WechatSection({ data }: { data: IntelSourceResponse }) {
  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <div className="rounded-[10px] border border-[#dce1e9] bg-[#ffffff] px-4 py-3 text-sm text-[#5a6474]">
        这里是媒体与垂类号的外部解读层。它更适合给选题提供角度，不应替代官方来源本身。
      </div>
      <SourceList items={data.items} />
    </section>
  );
}
