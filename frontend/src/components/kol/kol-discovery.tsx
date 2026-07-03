"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Download, RefreshCw, Sparkles, X } from "lucide-react";

import type { KolCandidate, KolStatus } from "@/types";
import {
  enrichKol,
  fetchKeywords,
  fetchKolCandidates,
  kolExportUrl,
  setKolStatus,
  type KolFilters,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { TagBadge } from "@/components/ui/badge";
import { formatNumber } from "@/lib/utils";

const STATUS_TABS: { key: KolStatus | "all"; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "candidate", label: "候选" },
  { key: "shortlisted", label: "名单" },
  { key: "rejected", label: "已排除" },
];

function scoreColor(score: number): string {
  if (score >= 70) return "#16a34a";
  if (score >= 50) return "#e08a1e";
  return "#7b8494";
}

export function KolDiscovery() {
  const [rows, setRows] = useState<KolCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [keywords, setKeywords] = useState<string[]>([]);

  // 筛选状态
  const [keyword, setKeyword] = useState("");
  const [minEngagement, setMinEngagement] = useState(0);
  const [onlyPositive, setOnlyPositive] = useState(false);
  const [hideCompetitor, setHideCompetitor] = useState(true);
  const [statusTab, setStatusTab] = useState<KolStatus | "all">("all");

  const filters = useMemo<KolFilters>(
    () => ({
      keyword: keyword || undefined,
      minEngagement: minEngagement || undefined,
      sentiment: onlyPositive ? "positive" : undefined,
      hideCompetitor,
      status: statusTab === "all" ? undefined : statusTab,
      limit: 100,
    }),
    [keyword, minEngagement, onlyPositive, hideCompetitor, statusTab],
  );

  const load = useCallback(() => {
    setLoading(true);
    fetchKolCandidates(filters)
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => {
    fetchKeywords().then((c) => setKeywords(c.all)).catch(() => {});
  }, []);
  useEffect(() => {
    const t = setTimeout(load, 0);
    return () => clearTimeout(t);
  }, [load]);

  const updateStatus = useCallback(
    async (userId: string, status: KolStatus) => {
      setRows((prev) =>
        prev.map((r) => (r.user_id === userId ? { ...r, status } : r)),
      );
      await setKolStatus(userId, status).catch(() => {});
    },
    [],
  );

  const doEnrich = useCallback(async (userId: string) => {
    try {
      const res = await enrichKol(userId);
      const fans = res.profile?.fans_count as number | undefined;
      setRows((prev) =>
        prev.map((r) =>
          r.user_id === userId ? { ...r, fans_count: fans ?? r.fans_count } : r,
        ),
      );
    } catch {
      alert("富化失败：TikHub 可能欠费或达每日上限");
    }
  }, []);

  return (
    <div className="min-h-screen bg-[#f4f6fa]">
      <header className="border-b border-[#eaeef4] px-6 py-4">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex items-center gap-1 text-xs text-[#7b8494] hover:text-[#1f2a44]"
            >
              <ArrowLeft size={14} /> 返回舆情
            </Link>
            <h1 className="text-base font-semibold text-[#1f2a44]">KOL 挖掘</h1>
            <span className="text-xs text-[#7b8494]">
              从话题作者中挖掘可签约的发声者 · 按综合分排序
            </span>
          </div>
          <a
            href={kolExportUrl}
            className="flex items-center gap-1.5 rounded-lg border border-[#dce1e9] px-3 py-1.5 text-xs text-[#5a6474] hover:bg-[#eef2f8] hover:text-[#1f2a44]"
          >
            <Download size={13} /> 导出 CSV
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-screen-2xl space-y-4 px-6 py-6">
        {/* 筛选条 */}
        <Card>
          <CardContent className="flex flex-wrap items-center gap-4 pt-5">
            <label className="flex items-center gap-2 text-xs text-[#5a6474]">
              话题词
              <select
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                className="rounded border border-[#dce1e9] bg-[#eef2f8] px-2 py-1 text-xs text-[#1f2a44]"
              >
                <option value="">全部</option>
                {keywords.map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-xs text-[#5a6474]">
              最低篇均互动
              <input
                type="number"
                min={0}
                value={minEngagement}
                onChange={(e) => setMinEngagement(Number(e.target.value))}
                className="w-24 rounded border border-[#dce1e9] bg-[#eef2f8] px-2 py-1 text-xs text-[#1f2a44]"
              />
            </label>
            <label className="flex cursor-pointer items-center gap-1.5 text-xs text-[#5a6474]">
              <input type="checkbox" checked={onlyPositive}
                onChange={(e) => setOnlyPositive(e.target.checked)} />
              只看正面为主
            </label>
            <label className="flex cursor-pointer items-center gap-1.5 text-xs text-[#5a6474]">
              <input type="checkbox" checked={hideCompetitor}
                onChange={(e) => setHideCompetitor(e.target.checked)} />
              隐藏竞品账号
            </label>
            <div className="ml-auto flex items-center gap-1">
              {STATUS_TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setStatusTab(t.key)}
                  className={`rounded px-2.5 py-1 text-xs transition-colors ${
                    statusTab === t.key
                      ? "bg-[#1e51a2] text-white"
                      : "text-[#7b8494] hover:text-[#5a6474]"
                  }`}
                >
                  {t.label}
                </button>
              ))}
              <button onClick={load} className="ml-1 text-[#7b8494] hover:text-[#1f2a44]"
                aria-label="刷新">
                <RefreshCw size={13} />
              </button>
            </div>
          </CardContent>
        </Card>

        {/* 结果表 */}
        <Card>
          <CardContent className="pt-5">
            {loading ? (
              <div className="h-[300px] animate-pulse rounded bg-[#eaeef4]" />
            ) : rows.length === 0 ? (
              <p className="py-12 text-center text-xs text-[#7b8494]">无匹配候选</p>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="text-[#7b8494]">
                  <tr className="border-b border-[#eaeef4]">
                    <th className="pb-2 font-normal">KOL</th>
                    <th className="pb-2 font-normal">命中词</th>
                    <th className="pb-2 text-right font-normal">发文</th>
                    <th className="pb-2 text-right font-normal">篇均互动</th>
                    <th className="pb-2 text-right font-normal">正面率</th>
                    <th className="pb-2 text-right font-normal">粉丝</th>
                    <th className="pb-2 text-right font-normal">综合分</th>
                    <th className="pb-2 text-right font-normal">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <KolRow
                      key={r.user_id}
                      row={r}
                      onStatus={updateStatus}
                      onEnrich={doEnrich}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function KolRow({
  row,
  onStatus,
  onEnrich,
}: {
  row: KolCandidate;
  onStatus: (id: string, s: KolStatus) => void;
  onEnrich: (id: string) => void;
}) {
  const dimmed = row.status === "rejected";
  return (
    <tr className={`border-b border-[#eef2f8] ${dimmed ? "opacity-40" : ""}`}>
      <td className="py-2.5">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[#1f2a44]">{row.nickname}</span>
          {row.is_competitor && (
            <span className="rounded bg-[#e08a1e]/15 px-1.5 py-0.5 text-[12px] text-[#b45309]">
              竞品
            </span>
          )}
          {row.status === "shortlisted" && (
            <span className="rounded bg-[#16a34a]/15 px-1.5 py-0.5 text-[12px] text-[#16a34a]">
              名单
            </span>
          )}
        </div>
      </td>
      <td className="py-2.5">
        <div className="flex flex-wrap gap-1">
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
          title={`相关度 ${row.score_breakdown.relevance ?? "-"} · 互动 ${row.score_breakdown.engagement ?? "-"} · 情感 ${row.score_breakdown.sentiment ?? "-"}`}
        >
          {row.fit_score.toFixed(0)}
        </span>
      </td>
      <td className="py-2.5">
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
          {row.status !== "shortlisted" && (
            <button
              onClick={() => onStatus(row.user_id, "shortlisted")}
              className="flex items-center gap-1 rounded px-1.5 py-1 text-[12px] text-[#7b8494] hover:bg-[#eef2f8] hover:text-[#16a34a]"
              title="加入名单"
            >
              <Check size={11} /> 名单
            </button>
          )}
          {row.status !== "rejected" && (
            <button
              onClick={() => onStatus(row.user_id, "rejected")}
              className="flex items-center gap-1 rounded px-1.5 py-1 text-[12px] text-[#7b8494] hover:bg-[#eef2f8] hover:text-[#ea5457]"
              title="排除"
            >
              <X size={11} /> 排除
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
