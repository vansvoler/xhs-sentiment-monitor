"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Download, RefreshCw } from "lucide-react";

import type { AccountType, KolCandidate, KolStatus } from "@/types";
import {
  enrichKol,
  fetchKeywords,
  fetchKolCandidates,
  kolExportUrl,
  setKolAccountType,
  setKolStatus,
  type KolFilters,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

import { KolRow } from "./kol-row";

// "全部" = 候选 + 名单；已排除的只在自己的 tab 里现身，可随时恢复
const STATUS_TABS: { key: KolStatus | "all"; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "candidate", label: "候选" },
  { key: "shortlisted", label: "名单" },
  { key: "rejected", label: "已排除" },
];

// 账号身份筛选：默认只看素人（真正的招募池），矩阵号一键可查而非默认隐藏
const TYPE_TABS: { key: AccountType | "all"; label: string }[] = [
  { key: "individual", label: "素人" },
  { key: "competitor_matrix", label: "竞品官号" },
  { key: "own_matrix", label: "自家官号" },
  { key: "all", label: "全部" },
];

export function KolDiscovery() {
  const [rows, setRows] = useState<KolCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [keywords, setKeywords] = useState<string[]>([]);

  // 筛选状态
  const [keyword, setKeyword] = useState("");
  const [nickname, setNickname] = useState("");
  const [nicknameQuery, setNicknameQuery] = useState(""); // 防抖后的实际查询值
  const [minEngagement, setMinEngagement] = useState(0);
  const [typeTab, setTypeTab] = useState<AccountType | "all">("individual");
  const [statusTab, setStatusTab] = useState<KolStatus | "all">("all");

  // 昵称输入防抖：停顿 300ms 才发起查询
  useEffect(() => {
    const t = setTimeout(() => setNicknameQuery(nickname.trim()), 300);
    return () => clearTimeout(t);
  }, [nickname]);

  const filters = useMemo<KolFilters>(
    () => ({
      keyword: keyword || undefined,
      nickname: nicknameQuery || undefined,
      minEngagement: minEngagement || undefined,
      accountType: typeTab === "all" ? undefined : typeTab,
      status: statusTab === "all" ? undefined : statusTab,
      limit: 100,
    }),
    [keyword, nicknameQuery, minEngagement, typeTab, statusTab],
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

  // 改状态/分类都会让该行落到别的 tab（排除后从默认视图消失），故重拉而非就地更新
  const updateStatus = useCallback(
    async (userId: string, status: KolStatus) => {
      await setKolStatus(userId, status).catch(() => {});
      load();
    },
    [load],
  );

  const updateAccountType = useCallback(
    async (userId: string, accountType: AccountType | "") => {
      await setKolAccountType(userId, accountType).catch(() => {});
      load();
    },
    [load],
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
              从话题作者中挖掘可签约的发声者 · 按综合分排序 · 点击展开看相关笔记
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
              昵称
              <input
                type="search"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="搜索昵称…"
                className="w-32 rounded border border-[#dce1e9] bg-[#eef2f8] px-2 py-1 text-xs text-[#1f2a44] placeholder:text-[#a3acbc]"
              />
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
            <div className="flex items-center gap-1 rounded-lg bg-[#eef2f8] p-0.5">
              {TYPE_TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTypeTab(t.key)}
                  className={`rounded px-2.5 py-1 text-xs transition-colors ${
                    typeTab === t.key
                      ? "bg-white font-medium text-[#1f2a44] shadow-sm"
                      : "text-[#7b8494] hover:text-[#5a6474]"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
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
                    <th className="pb-2 font-normal">账号类型</th>
                    <th className="pb-2 font-normal">关联性 / 命中词</th>
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
                      onAccountType={updateAccountType}
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
