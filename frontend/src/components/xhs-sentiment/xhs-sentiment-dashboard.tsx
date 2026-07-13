"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw, Users } from "lucide-react";

import type {
  CompetitorData,
  HotTopic,
  KeywordConfig,
  NegativeSummary,
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
  fetchNegativeSummary,
  fetchNotes,
  fetchNotesSummary,
  fetchTrendSeries,
} from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { ConnectionStatus } from "@/lib/websocket";

// 趋势时间窗：默认 30 天看近期舆情，长窗用于回溯
const TREND_WINDOWS = [
  { days: 7, label: "7天" },
  { days: 30, label: "30天" },
  { days: 90, label: "90天" },
  { days: 365, label: "近一年" },
];
// 竞品对比 / 高互动笔记的时间窗选项
const WINDOW_OPTIONS = [
  { days: 7, label: "7天" },
  { days: 30, label: "30天" },
  { days: 180, label: "半年" },
  { days: 365, label: "一年" },
];

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
  const [keywordFilter, setKeywordFilter] = useState("");
  const [keywordConfig, setKeywordConfig] = useState<KeywordConfig | null>(null);
  const [competitorDays, setCompetitorDays] = useState(90);
  const [hotDays, setHotDays] = useState(365);

  const [summary, setSummary] = useState<NotesSummary | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [notesHasMore, setNotesHasMore] = useState(false);
  const [trends, setTrends] = useState<TrendDataPoint[]>([]);
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [competitors, setCompetitors] = useState<CompetitorData[]>([]);
  const [trendDays, setTrendDays] = useState(30);
  const [negativeSummary, setNegativeSummary] = useState<NegativeSummary | null>(null);

  // 概览 + 笔记：顶部筛选（tab/情感/关键词/时间窗）驱动
  const load = useCallback(
    async (
      tab: ActiveTab, sentiment: SentimentFilter, days: number, keyword: string,
    ) => {
      const category = tab === "all" ? undefined : tab;
      const sentimentValue = sentiment === "all" ? undefined : sentiment;
      setLoading((p) => ({ ...p, overview: true, notes: true }));

      const overview = Promise.allSettled([
        fetchNotesSummary(category).then(setSummary),
        fetchTrendSeries(days, category).then(setTrends),
      ]).finally(() => setLoading((p) => ({ ...p, overview: false })));

      const notesReq = fetchNotes(0, 20, category, sentimentValue, keyword || undefined)
        .then((data) => {
          setNotes(data);
          setNotesHasMore(data.length === 20);
        })
        .finally(() => setLoading((p) => ({ ...p, notes: false })));

      await Promise.allSettled([overview, notesReq]);
    },
    [],
  );

  // 洞察区：竞品对比 / 高互动笔记各带独立时间窗
  const loadInsights = useCallback(
    async (tab: ActiveTab, hotD: number, compD: number) => {
      const category = tab === "all" ? undefined : tab;
      setLoading((p) => ({ ...p, insights: true }));
      await Promise.allSettled([
        fetchHotTopics(10, hotD * 24, category).then(setTopics),
        fetchCompetitors(compD).then(setCompetitors),
      ]);
      setLoading((p) => ({ ...p, insights: false }));
    },
    [],
  );

  useEffect(() => {
    fetchKeywords().then(setKeywordConfig).catch(() => {});
    fetchNegativeSummary().then(setNegativeSummary).catch(() => {});
  }, []);

  const loadMoreNotes = useCallback(async () => {
    const category = activeTab === "all" ? undefined : activeTab;
    const sentimentValue = sentimentFilter === "all" ? undefined : sentimentFilter;
    const more = await fetchNotes(
      notes.length, 20, category, sentimentValue, keywordFilter || undefined,
    ).catch(() => []);
    setNotes((prev) => [...prev, ...more]);
    setNotesHasMore(more.length === 20);
  }, [activeTab, sentimentFilter, keywordFilter, notes.length]);

  useEffect(() => {
    const t = setTimeout(
      () => void load(activeTab, sentimentFilter, trendDays, keywordFilter), 0,
    );
    return () => clearTimeout(t);
  }, [activeTab, sentimentFilter, trendDays, keywordFilter, load]);

  useEffect(() => {
    void loadInsights(activeTab, hotDays, competitorDays);
  }, [activeTab, hotDays, competitorDays, loadInsights]);

  const handleTabChange = useCallback((tab: ActiveTab) => {
    setActiveTab(tab);
    setSentimentFilter("all");
    setKeywordFilter("");
  }, []);

  return (
    <div className="min-h-screen bg-[#f4f6fa]">
      <DashboardHeader wsStatus={wsStatus} />

      <main className="mx-auto max-w-screen-2xl space-y-4 px-6 py-6">
        {/* 控制条：顶部筛选全页生效 */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CategoryTabs active={activeTab} onChange={handleTabChange} />
          <div className="flex items-center gap-1">
            <Link
              href="/dashboard/negative"
              className="flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-[#7b8494] transition-colors hover:bg-[#eef2f8] hover:text-[#1f2a44]"
            >
              <AlertTriangle size={12} className="text-[#ea5457]" aria-hidden="true" />
              负面舆情
              {negativeSummary &&
                negativeSummary.notes_open + negativeSummary.comments_open > 0 && (
                <span className="rounded-full bg-[#ea5457] px-1.5 text-[11px] font-semibold text-white">
                  {negativeSummary.notes_open + negativeSummary.comments_open}
                </span>
              )}
            </Link>
            <Link
              href="/dashboard/kol"
              className="flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-[#7b8494] transition-colors hover:bg-[#eef2f8] hover:text-[#1f2a44]"
            >
              <Users size={12} aria-hidden="true" />
              KOL 挖掘
            </Link>
            <button
              onClick={() => {
                void load(activeTab, sentimentFilter, trendDays, keywordFilter);
                void loadInsights(activeTab, hotDays, competitorDays);
              }}
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
              <AlertPanel keywordConfig={keywordConfig} activeTab={activeTab} />
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
              <SentimentDonut
                distribution={summary?.sentiment_distribution ?? {}}
              />
            </CardContent>
          </Card>
        </section>

        {/* ③ 洞察：竞品 + 高互动笔记 */}
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>竞品对比</CardTitle>
              <WindowTabs value={competitorDays} onChange={setCompetitorDays} />
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
              <WindowTabs value={hotDays} onChange={setHotDays} />
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
              {/* 情感筛选只作用于本列表，收进卡片内 */}
              <SentimentBar active={sentimentFilter} onChange={setSentimentFilter} />
            </CardHeader>
            <CardContent>
              <NotesTable
                notes={notes}
                loading={loading.notes}
                keywords={
                  // 关键词下拉跟随顶部分类：只列当前分类下的监控词
                  activeTab === "all"
                    ? keywordConfig?.all ?? []
                    : keywordConfig?.[activeTab] ?? []
                }
                selectedKw={keywordFilter}
                onSelectKw={setKeywordFilter}
              />
              {notesHasMore && !loading.notes && (
                <button
                  onClick={loadMoreNotes}
                  className="mt-3 w-full cursor-pointer rounded-lg border border-[#dce1e9] bg-white py-2 text-xs text-[#5a6474] transition-colors hover:bg-[#eef2f8]"
                >
                  加载更多
                </button>
              )}
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

// 时间窗切换（竞品对比 / 高互动笔记共用）
function WindowTabs({
  value,
  onChange,
}: {
  value: number;
  onChange: (days: number) => void;
}) {
  return (
    <div className="flex gap-1" role="group" aria-label="时间范围">
      {WINDOW_OPTIONS.map((w) => (
        <button
          key={w.days}
          onClick={() => onChange(w.days)}
          className={`cursor-pointer rounded px-2 py-0.5 text-xs transition-colors ${
            value === w.days
              ? "bg-[#1e51a2] text-white"
              : "text-[#7b8494] hover:text-[#5a6474]"
          }`}
          aria-pressed={value === w.days}
        >
          {w.label}
        </button>
      ))}
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
      <Link
        href="/dashboard/negative"
        className="rounded transition-colors hover:bg-[#eef2f8]"
        aria-label="打开负面舆情工作台"
      >
        <Metric label="负面笔记" value={formatNumber(negative)} tone="#ea5457" />
      </Link>
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
