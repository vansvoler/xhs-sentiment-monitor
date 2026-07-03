import type { IntelItem } from "@/types";

interface IntelCardProps {
  item: IntelItem;
  compact?: boolean;
}

export function IntelCard({ item, compact = false }: IntelCardProps) {
  return (
    <article className="rounded-[10px] border border-[#dce1e9] bg-[#ffffff] p-4">
      <h3 className="text-sm font-medium text-[#17233f]">{item.title}</h3>
      <p className="mt-2 text-sm leading-6 text-[#4b5563]">
        {compact ? item.summary_short : item.summary_long}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[#7b8494]">
        <span>{item.school_name ?? item.source_name}</span>
        {item.impact_targets.map((target) => (
          <span key={target} className="rounded bg-[#eef2f8] px-2 py-0.5">
            {target}
          </span>
        ))}
      </div>
      <a
        className="mt-3 inline-flex text-xs text-[#6f94cd] transition-colors hover:text-[#17233f]"
        href={item.original_url}
        target="_blank"
        rel="noreferrer"
      >
        去原文
      </a>
    </article>
  );
}
