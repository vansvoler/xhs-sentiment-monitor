"use client";

import { useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  RotateCcw,
  Sparkles,
  Undo2,
  X,
} from "lucide-react";

import type { AccountType, KolCandidate, KolStatus, TopCategory } from "@/types";
import { TagBadge } from "@/components/ui/badge";
import { formatNumber, userUrl } from "@/lib/utils";

import { KolNotes } from "./kol-notes";

// 命中词离品牌越近，招募价值越高——与后端 _CATEGORY_SCORE 同序
const CATEGORY_BADGE: Record<TopCategory, { label: string; cls: string }> = {
  brand: { label: "提过我们", cls: "bg-[#16a34a]/15 text-[#16a34a]" },
  competitor: { label: "提过竞品", cls: "bg-[#e08a1e]/15 text-[#b45309]" },
  industry: { label: "行业垂类", cls: "bg-[#7b8494]/15 text-[#5a6474]" },
};

const TYPE_OPTIONS: { value: AccountType; label: string }[] = [
  { value: "individual", label: "素人" },
  { value: "competitor_matrix", label: "竞品官号" },
  { value: "own_matrix", label: "自家官号" },
];

function scoreColor(score: number): string {
  if (score >= 70) return "#16a34a";
  if (score >= 50) return "#e08a1e";
  return "#7b8494";
}

export interface KolRowActions {
  onStatus: (id: string, s: KolStatus) => void;
  onEnrich: (id: string) => void;
  onAccountType: (id: string, t: AccountType | "") => void;
}

export function KolRow({ row, ...actions }: { row: KolCandidate } & KolRowActions) {
  const [open, setOpen] = useState(false);
  const cat = CATEGORY_BADGE[row.top_category];

  return (
    <>
      <tr className="border-b border-[#eef2f8]">
        <td className="py-2.5">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setOpen((v) => !v)}
              className="text-[#7b8494] hover:text-[#1f2a44]"
              aria-label={open ? "收起相关笔记" : "展开相关笔记"}
            >
              {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </button>
            <a
              href={userUrl(row.user_id)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 font-medium text-[#1f2a44] hover:text-[#1e51a2] hover:underline"
              title="在小红书打开主页"
            >
              {row.nickname}
              <ExternalLink size={10} className="text-[#7b8494]" />
            </a>
          </div>
        </td>

        <td className="py-2.5">
          <AccountTypePicker row={row} onAccountType={actions.onAccountType} />
        </td>

        <td className="py-2.5">
          <div className="flex flex-wrap items-center gap-1">
            <span className={`rounded px-1.5 py-0.5 text-[12px] ${cat.cls}`}>
              {cat.label}
            </span>
            {row.keywords_hit.map((k) => (
              <TagBadge key={k}>{k}</TagBadge>
            ))}
          </div>
        </td>

        <td className="py-2.5 text-right text-[#5a6474]">{row.note_count}</td>
        <td className="py-2.5 text-right text-[#5a6474]">
          {formatNumber(Math.round(row.avg_engagement))}
        </td>
        <td className="py-2.5 text-right text-[#5a6474]">
          {(row.positive_rate * 100).toFixed(0)}%
        </td>
        <td className="py-2.5 text-right text-[#5a6474]">
          {row.fans_count != null ? formatNumber(row.fans_count) : "—"}
        </td>
        <td className="py-2.5 text-right">
          <span
            className="font-mono font-semibold"
            style={{ color: scoreColor(row.fit_score) }}
            title={`关联度 ${row.score_breakdown.relevance ?? "-"} · 互动 ${row.score_breakdown.engagement ?? "-"}（各占一半，情感不入分）`}
          >
            {row.fit_score.toFixed(0)}
          </span>
        </td>
        <td className="py-2.5">
          <RowActions row={row} {...actions} />
        </td>
      </tr>

      {open && (
        <tr className="border-b border-[#eef2f8] bg-[#f8fafc]">
          <td colSpan={9} className="px-8 py-3">
            <KolNotes userId={row.user_id} />
          </td>
        </tr>
      )}
    </>
  );
}

/** 昵称规则会看走眼（如「聪聪-活力校长版」），这里让人工说了算 */
function AccountTypePicker({
  row,
  onAccountType,
}: {
  row: KolCandidate;
  onAccountType: KolRowActions["onAccountType"];
}) {
  return (
    <div className="flex items-center gap-1">
      <select
        value={row.account_type}
        onChange={(e) => onAccountType(row.user_id, e.target.value as AccountType)}
        className={`rounded border border-[#dce1e9] bg-white px-1.5 py-0.5 text-[12px] ${
          row.account_type_manual ? "text-[#1e51a2]" : "text-[#5a6474]"
        }`}
      >
        {TYPE_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {row.account_type_manual && (
        <button
          onClick={() => onAccountType(row.user_id, "")}
          className="flex items-center gap-0.5 rounded bg-[#1e51a2]/10 px-1 py-0.5 text-[12px] text-[#1e51a2] hover:bg-[#1e51a2]/20"
          title="已人工校正，点击撤销、交还昵称自动规则"
        >
          <RotateCcw size={9} /> 人工
        </button>
      )}
    </div>
  );
}

function RowActions({ row, onStatus, onEnrich }: { row: KolCandidate } & KolRowActions) {
  // 已排除的行只提供"恢复"——排除是隐藏而非删除
  if (row.status === "rejected") {
    return (
      <div className="flex items-center justify-end">
        <button
          onClick={() => onStatus(row.user_id, "candidate")}
          className="flex items-center gap-1 rounded px-1.5 py-1 text-[12px] text-[#7b8494] hover:bg-[#eef2f8] hover:text-[#1f2a44]"
          title="恢复到候选池"
        >
          <Undo2 size={11} /> 恢复
        </button>
      </div>
    );
  }

  const shortlisted = row.status === "shortlisted";
  return (
    <div className="flex items-center justify-end gap-1.5">
      {row.fans_count == null && (
        <button
          onClick={() => onEnrich(row.user_id)}
          className="flex items-center gap-1 rounded px-1.5 py-1 text-[12px] text-[#7b8494] hover:bg-[#eef2f8] hover:text-[#6f94cd]"
          title="补粉丝数（付费）"
        >
          <Sparkles size={11} /> 富化
        </button>
      )}
      <button
        onClick={() => onStatus(row.user_id, shortlisted ? "candidate" : "shortlisted")}
        className={`flex items-center gap-1 rounded px-1.5 py-1 text-[12px] ${
          shortlisted
            ? "bg-[#16a34a]/15 text-[#16a34a] hover:bg-[#16a34a]/25"
            : "text-[#7b8494] hover:bg-[#eef2f8] hover:text-[#16a34a]"
        }`}
        title={shortlisted ? "移出名单" : "加入名单"}
      >
        <Check size={11} /> 名单
      </button>
      <button
        onClick={() => onStatus(row.user_id, "rejected")}
        className="flex items-center gap-1 rounded px-1.5 py-1 text-[12px] text-[#7b8494] hover:bg-[#eef2f8] hover:text-[#ea5457]"
        title="排除：从默认视图隐藏，可在「已排除」tab 恢复"
      >
        <X size={11} /> 排除
      </button>
    </div>
  );
}
