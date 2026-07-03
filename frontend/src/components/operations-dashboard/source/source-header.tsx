import type { IntelSourceFeedKey } from "@/types";

const SOURCE_HINTS: Record<IntelSourceFeedKey, string> = {
  ucas: "优先关注政策、时间节点和申请流程变更。",
  university_site: "优先关注重点学校更新，再看全部学校动态。",
  exam_board: "优先关注考试安排、成绩发布和考试政策变更。",
  visa_policy: "优先关注签证规则、材料要求和政策生效时间。",
  wechat_media: "这里是媒体与垂类号的外部解读层。",
};

const SOURCE_LABELS: Record<IntelSourceFeedKey, string> = {
  ucas: "UCAS",
  university_site: "海外大学官网",
  exam_board: "考试局",
  visa_policy: "签证政策",
  wechat_media: "媒体公众号",
};

interface SourceHeaderProps {
  sourceKey: IntelSourceFeedKey;
  itemCount: number;
}

export function SourceHeader({ sourceKey, itemCount }: SourceHeaderProps) {
  return (
    <header className="rounded-[10px] border border-[#dce1e9] bg-[#ffffff] p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[#7b8494]">Source Feed</p>
          <h2 className="mt-2 text-lg font-semibold text-[#17233f]">{SOURCE_LABELS[sourceKey]}</h2>
        </div>
        <span className="text-xs text-[#7b8494]">当前 {itemCount} 条</span>
      </div>
      <p className="mt-3 text-sm text-[#5a6474]">{SOURCE_HINTS[sourceKey]}</p>
    </header>
  );
}
