"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw, Users } from "lucide-react";

import type {
  CompetitorData,
  HotTopic,
  KeywordConfig,
  Note,
  NotesSummary,
  SentimentFilter,
  TrendDataPoint,
} from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CompetitorBar } from "@/components/charts/competitor-bar";
import { SentimentDonut } from "@/components/charts/sentiment-donut";
import { TrendLine } from "@/components/charts/trend-line";
import { AlertPanel } from "@/components/xhs-sentiment/alert-panel";
import { CategoryTabs, SentimentBar } from "@/components/xhs-sentiment/category-tabs";
import type { ActiveTab } from "@/components/xhs-sentiment/category-tabs";
import { DashboardHeader } from "@/components/xhs-sentiment/header";
import { KeywordManager } from "@/components/xhs-sentiment/keyword-manager";
import { HotTopics } from "@/components/xhs-sentiment/hot-topics";
import { NotesTable } from "@/components/xhs-sentiment/notes-table";
import { RealtimeFeed } from "@/components/xhs-sentiment/realtime-feed";
import {
  fetchCompetitors,
  fetchHotTopics,
  fetchKeywords,
  fetchNotes,
  fetchNotesSummary,
  fetchTrendSeries,
} from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { ConnectionStatus } from "@/lib/websocket";

// 趋势时间窗：存量数据多在数月前，默认「近一年」避免空图
const TREND_WINDOWS = [
  { days: 90, label: "90天" },
  { days: 180, label: "半年" },
  { days: 365, label: "近一年" },
];
// 高互动笔记的回看窗口（小时）——一年，取真正有互动的历史笔记
const HOT_HOURS = 24 * 365;

type LoadingState = { overview: boolean; notes: boolean; insights: boolean };

export function XhsSentimentDashboard() {
  const [wsStatus, setWsStatus] = useState<ConnectionStatus>("connecting");
  const [loading, setLoading] = useState<LoadingState>({
    overview: true,
    notes: true,
    insights: true,
  });
  const [activeTab, setActiveTab] = useState<ActiveTab>("all");
  const [sentimentFilter, setSentimentFilter] = useState<SentimentFilter>("all");
  const [keywordConfig, setKeywordConfig] = useState<KeywordConfig | null>(null);

  const [summary, setSummary] = useState<NotesSummary | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [trends, setTrends] = useState<TrendDataPoint[]>([]);
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [competitors, setCompetitors] = useState<CompetitorData[]>([]);
  const [trendDays, setTrendDays] = useState(365);

  // 单一加载入口：顶部筛选（tab/情感/时间窗）全页生效
  const load = useCallback(
    async (tab: ActiveTab, sentiment: SentimentFilter, days: number) => {
      const category = tab === "all" ? undefined : tab;
      const sentimentValue = sentiment === "all" ? undefined : sentiment;
      setLoading({ overview: true, notes: true, insights: true });

      const overview = Promise.allSettled([
        fetchNotesSummary(category).then(setSummary),
        fetchTrendSeries(days, category).then(setTrends),
      ]).finally(() => setLoading((p) => ({ ...p, overview: false })));

      const insights = Promise.allSettled([
        fetchHotTopics(10, HOT_HOURS, category).then(setTopics),
        fetchCompetitors(90).then(setCompetitors),
      ]).finally(() => setLoading((p) => ({ ...p, insights: false })));

      const notesReq = fetchNotes(0, 20, category, sentimentValue)
        .then(setNotes)
        .finally(() => setLoading((p) => ({ ...p, notes: false })));

      await Promise.allSettled([overview, insights, notesReq]);
    },
    [],
  );

  useEffect(() => {
    fetchKeywords().then(setKeywordConfig).catch(() => {});
  }, []);

  useEffect(() => {
    const t = setTimeout(() => void load(activeTab, sentimentFilter, trendDays), 0);
    return () => clearTimeout(t);
  }, [activeTab, sentimentFilter, trendDays, load]);

  const handleTabChange = useCallback((tab: ActiveTab) => {
    setActiveTab(tab);
    setSentimentFilter("all");
  }, []);

  return (
    <div className="min-h-screen bg-[#f4f6fa]">
      <DashboardHeader wsStatus={wsStatus} />

      <main className="mx-auto max-w-screen-2xl space-y-4 px-6 py-6">
        {/* 控制条：顶部筛选全页生效 */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="space-y-2">
            <CategoryTabs active={activeTab} onChange={handleTabChange} />
            <SentimentBar active={sentimentFilter} onChange={setSentimentFilter} />
          </div>
          <div className="flex items-center gap-1">
            <Link
              href="/dashboard/kol"
              className="flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-[#7b8494] transition-colors hover:bg-[#eef2f8] hover:text-[#1f2a44]"
            >
              <Users size={12} aria-hidden="true" />
              KOL 挖掘
            </Link>
            <button
              onClick={() => load(activeTab, sentimentFilter, trendDays)}
              className="flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-[#7b8494] transition-colors hover:bg-[#eef2f8] hover:text-[#1f2a44]"
              aria-label="刷新数据"
            >
              <RefreshCw size={12} aria-hidden="true" />
              刷新
            </button>
          </div>
        </div>

        {/* 监控词：按当前 tab 分组展示，可增删 */}
        <KeywordManager
          config={keywordConfig}
          activeTab={activeTab}
          onMutate={setKeywordConfig}
        />

        {/* ① 健康状态带：关键指标 + 预警，最抢眼 */}
        <Card>
          <CardContent className="space-y-3 pt-4">
            <MetricStrip summary={summary} loading={loading.overview} />
            <div className="border-t border-[#eaeef4] pt-3">
              <AlertPanel />
            </div>
          </CardContent>
        </Card>

        {/* ② 情感趋势（主角）+ 情感分布（副） */}
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>情感趋势</CardTitle>
              <div className="flex gap-1" role="group" aria-label="时间范围">
                {TREND_WINDOWS.map((w) => (
                  <button
                    key={w.days}
                    onClick={() => setTrendDays(w.days)}
                    className={`cursor-pointer rounded px-2 py-0.5 text-xs transition-colors ${
                      trendDays === w.days
                        ? "bg-[#1e51a2] text-white"
                        : "text-[#7b8494] hover:text-[#5a6474]"
                    }`}
                    aria-pressed={trendDays === w.days}
                  >
                    {w.label}
                  </button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              {loading.overview ? (
                <div className="h-[240px] animate-pulse rounded bg-[#eaeef4]" />
              ) : (
                <TrendLine data={trends} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>情感分布</CardTitle>
            </CardHeader>
            <CardContent>
              <SentimentDonut distribution={summary?.sentiment_distribution ?? {}} />
            </CardContent>
          </Card>
        </section>

        {/* ③ 洞察：竞品 + 高互动笔记 */}
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>竞品对比</CardTitle>
              <span className="text-xs text-[#7b8494]">近 90 天</span>
            </CardHeader>
            <CardContent>
              {loading.insights ? (
                <div className="h-[220px] animate-pulse rounded bg-[#eaeef4]" />
              ) : (
                <CompetitorBar data={competitors} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>高互动笔记</CardTitle>
              <span className="text-xs text-[#7b8494]">近一年 · 按互动排序</span>
            </CardHeader>
            <CardContent>
              <HotTopics topics={topics} loading={loading.insights} />
            </CardContent>
          </Card>
        </section>

        {/* ④ 笔记明细（主体）+ 实时动态 */}
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>最新笔记</CardTitle>
              <span className="text-xs text-[#7b8494]">跟随顶部筛选</span>
            </CardHeader>
            <CardContent>
              <NotesTable
                notes={notes}
                loading={loading.notes}
                keywords={keywordConfig?.all ?? []}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>实时动态</CardTitle>
            </CardHeader>
            <CardContent>
              <RealtimeFeed onStatusChange={setWsStatus} />
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}

// 紧凑指标条：替代原先四张大卡
function MetricStrip({
  summary,
  loading,
}: {
  summary: NotesSummary | null;
  loading: boolean;
}) {
  if (loading || !summary) {
    return <div className="h-6 w-full animate-pulse rounded bg-[#eaeef4]" />;
  }
  const dist = summary.sentiment_distribution ?? {};
  const positive = dist.positive ?? 0;
  const negative = dist.negative ?? 0;
  const total = summary.total_notes || 0;
  const positiveRate = total ? Math.round((positive / total) * 100) : 0;

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
      <Metric label="累计笔记" value={formatNumber(total)} />
      <Metric label="今日新增" value={String(summary.today_notes ?? 0)} />
      <Metric label="正面率" value={`${positiveRate}%`} tone="#16a34a" />
      <Metric label="负面笔记" value={formatNumber(negative)} tone="#ea5457" />
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-xs text-[#7b8494]">{label}</span>
      <span className="font-semibold" style={{ color: tone ?? "#1f2a44" }}>
        {value}
      </span>
    </span>
  );
}
