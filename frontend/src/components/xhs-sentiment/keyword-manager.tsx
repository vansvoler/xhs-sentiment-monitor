"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";

import type { CategoryType, KeywordConfig } from "@/types";
import type { ActiveTab } from "./category-tabs";
import { addKeyword, removeKeyword } from "@/lib/api";

const CAT_LABEL: Record<CategoryType, string> = {
  brand: "品牌词",
  competitor: "竞品词",
  industry: "行业词",
};

// 当前 tab 决定展示哪些分类的词
function categoriesFor(tab: ActiveTab): CategoryType[] {
  return tab === "all" ? ["brand", "competitor", "industry"] : [tab];
}

interface KeywordManagerProps {
  config: KeywordConfig | null;
  activeTab: ActiveTab;
  onMutate: (next: KeywordConfig) => void;
}

export function KeywordManager({ config, activeTab, onMutate }: KeywordManagerProps) {
  if (!config) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
      <span className="text-xs text-[#9aa1ac]">监控词</span>
      {categoriesFor(activeTab).map((cat) => (
        <KeywordGroup
          key={cat}
          category={cat}
          label={CAT_LABEL[cat]}
          keywords={config[cat]}
          onMutate={onMutate}
        />
      ))}
    </div>
  );
}

interface KeywordGroupProps {
  category: CategoryType;
  label: string;
  keywords: string[];
  onMutate: (next: KeywordConfig) => void;
}

function KeywordGroup({ category, label, keywords, onMutate }: KeywordGroupProps) {
  const [adding, setAdding] = useState(false);
  const [value, setValue] = useState("");

  const submit = async () => {
    const v = value.trim();
    setValue("");
    setAdding(false);
    if (!v) return;
    try {
      onMutate(await addKeyword(v, category));
    } catch {
      /* 静默失败 */
    }
  };

  const remove = async (kw: string) => {
    try {
      onMutate(await removeKeyword(kw));
    } catch {
      /* 静默失败 */
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs font-medium text-[#5a6474]">{label}</span>
      {keywords.map((kw) => (
        <span
          key={kw}
          className="inline-flex items-center gap-1 rounded border border-[#dce1e9] bg-[#eef2f8] px-1.5 py-0.5 text-xs text-[#5a6474]"
        >
          {kw}
          <button
            onClick={() => remove(kw)}
            aria-label={`删除 ${kw}`}
            className="cursor-pointer text-[#9aa1ac] transition-colors hover:text-[#ea5457]"
          >
            <X size={12} aria-hidden="true" />
          </button>
        </span>
      ))}
      {adding ? (
        <input
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={submit}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
            if (e.key === "Escape") {
              setValue("");
              setAdding(false);
            }
          }}
          placeholder="新词"
          className="w-20 rounded border border-[#1e51a2] bg-white px-1.5 py-0.5 text-xs text-[#1f2a44] outline-none"
        />
      ) : (
        <button
          onClick={() => setAdding(true)}
          aria-label={`添加${label}`}
          className="inline-flex cursor-pointer items-center gap-0.5 rounded px-1.5 py-0.5 text-xs text-[#1e51a2] transition-colors hover:bg-[#eef2f8]"
        >
          <Plus size={12} aria-hidden="true" /> 添加
        </button>
      )}
    </div>
  );
}
