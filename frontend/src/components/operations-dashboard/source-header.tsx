import type { IntelSourceFeedKey } from "@/types";

const SOURCE_HINTS: Record<IntelSourceFeedKey, string> = {
  xiaohongshu: "先看新增讨论，再看正在放量的话题。",
  ucas: "优先关注政策、时间节点和申请流程变更。",
  university_site: "优先关注重点学校更新，再看全部学校动态。",
  wechat_media: "这里是媒体与垂类号的外部解读层。",
};

const SOURCE_LABELS: Record<IntelSourceFeedKey, string> = {
  xiaohongshu: "小红书",
  ucas: "UCAS",
  university_site: "海外大学官网",
  wechat_media: "媒体公众号",
};

interface SourceHeaderProps {
  sourceKey: IntelSourceFeedKey;
  itemCount: number;
}

export function SourceHeader({ sourceKey, itemCount }: SourceHeaderProps) {
  return (
    <header className="rounded-[10px] border border-[#27272a] bg-[#111113] p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[#71717a]">Source Feed</p>
          <h2 className="mt-2 text-lg font-semibold text-white">{SOURCE_LABELS[sourceKey]}</h2>
        </div>
        <span className="text-xs text-[#71717a]">当前 {itemCount} 条</span>
      </div>
      <p className="mt-3 text-sm text-[#a1a1aa]">{SOURCE_HINTS[sourceKey]}</p>
    </header>
  );
}
