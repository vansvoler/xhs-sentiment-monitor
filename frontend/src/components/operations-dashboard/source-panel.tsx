import type { IntelSourceResponse } from "@/types";

import { SourceHeader } from "./source-header";
import { SourceList } from "./source-list";
import { UcasSection } from "./source-sections/ucas-section";
import { UniversitySection } from "./source-sections/university-section";
import { WechatSection } from "./source-sections/wechat-section";
import { XiaohongshuSection } from "./source-sections/xiaohongshu-section";

export function SourcePanel({ data }: { data: IntelSourceResponse }) {
  if (data.source_key === "xiaohongshu") {
    return <XiaohongshuSection data={data} />;
  }

  if (data.source_key === "ucas") {
    return <UcasSection data={data} />;
  }

  if (data.source_key === "university_site") {
    return <UniversitySection data={data} />;
  }

  if (data.source_key === "wechat_media") {
    return <WechatSection data={data} />;
  }

  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <SourceList items={data.items} />
    </section>
  );
}
