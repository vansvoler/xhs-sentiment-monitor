"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import type { Note, NotesSummary, TrendDataPoint, CompetitorData, HotTopic, SentimentFilter } from "@/types";
import type { ConnectionStatus } from "@/lib/websocket";
import {
  fetchNotes,
  fetchNotesSummary,
  fetchTrendSeries,
  fetchHotTopics,
  fetchCompetitors,
  fetchKeywords,
} from "@/lib/api";
import { DashboardHeader } from "@/components/dashboard/header";
import { CategoryTabs, SentimentBar } from "@/components/dashboard/category-tabs";
import type { ActiveTab } from "@/components/dashboard/category-tabs";
import { StatsOverview } from "@/components/dashboard/stats-overview";
import { NotesTable } from "@/components/dashboard/notes-table";
import { HotTopics } from "@/components/dashboard/hot-topics";
import { RealtimeFeed } from "@/components/dashboard/realtime-feed";
import { SentimentDonut } from "@/components/charts/sentiment-donut";
import { TrendLine } from "@/components/charts/trend-line";
import { CompetitorBar } from "@/components/charts/competitor-bar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

// ── 数据层 ────────────────────────────────────────────────────────────────────

type LoadingState = {
  summary: boolean;
  notes: boolean;
  trends: boolean;
  topics: boolean;
  competitors: boolean;
};

const INITIAL_LOADING: LoadingState = {
  summary: true,
  notes: true,
  trends: true,
  topics: true,
  competitors: true,
};

// ── 页面 ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [wsStatus, setWsStatus] = useState<ConnectionStatus>("connecting");
  const [loading, setLoading] = useState<LoadingState>(INITIAL_LOADING);
  const [activeTab, setActiveTab] = useState<ActiveTab>("all");
  const [sentimentFilter, setSentimentFilter] = useState<SentimentFilter>("all");
  const [keywords, setKeywords] = useState<string[]>([]);

  const [summary, setSummary] = useState<NotesSummary | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [trends, setTrends] = useState<TrendDataPoint[]>([]);
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [competitors, setCompetitors] = useState<CompetitorData[]>([]);
  const [trendDays, setTrendDays] = useState(7);

  // 趋势/竞品/热门话题不随 Tab 变
  const loadStatic = useCallback(async () => {
    setLoading((p) => ({ ...p, trends: true, topics: true, competitors: true }));
    await Promise.allSettled([
      fetchTrendSeries(trendDays)
        .then(setTrends)
        .finally(() => setLoading((p) => ({ ...p, trends: false }))),
      fetchHotTopics(10, 24)
        .then(setTopics)
        .finally(() => setLoading((p) => ({ ...p, topics: false }))),
      fetchCompetitors(30)
        .then(setCompetitors)
        .finally(() => setLoading((p) => ({ ...p, competitors: false }))),
    ]);
  }, [trendDays]);

  // 统计卡片 + 笔记列表随 Tab / sentiment 变
  const loadTabData = useCallback(async (tab: ActiveTab, sentiment: SentimentFilter) => {
    const cat = tab === "all" ? undefined : tab;
    const sent = sentiment === "all" ? undefined : sentiment;
    setLoading((p) => ({ ...p, summary: true, notes: true }));
    await Promise.allSettled([
      fetchNotesSummary(cat)
        .then(setSummary)
        .finally(() => setLoading((p) => ({ ...p, summary: false }))),
      fetchNotes(0, 20, cat, sent)
        .then(setNotes)
        .finally(() => setLoading((p) => ({ ...p, notes: false }))),
    ]);
  }, []);

  // 初始化：拉取关键词（静默失败）
  useEffect(() => {
    fetchKeywords()
      .then((cfg) => setKeywords(cfg.all))
      .catch(() => {});
  }, []);

  useEffect(() => { loadStatic(); }, [loadStatic]);
  useEffect(() => { loadTabData(activeTab, sentimentFilter); }, [activeTab, sentimentFilter, loadTabData]);

  // Tab 切换时重置情感筛选
  const handleTabChange = useCallback((tab: ActiveTab) => {
    setActiveTab(tab);
    setSentimentFilter("all");
  }, []);

  const handleRefresh = useCallback(() => {
    loadStatic();
    loadTabData(activeTab, sentimentFilter);
  }, [loadStatic, loadTabData, activeTab, sentimentFilter]);

  return (
    <div className="min-h-screen bg-[#09090b]">
      <DashboardHeader wsStatus={wsStatus} keywords={keywords} />

      <main className="mx-auto max-w-screen-2xl px-6 py-6 space-y-5">

        {/* ── Tab + 情感筛选 + 刷新 ────────────────────────────────────────────── */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <CategoryTabs active={activeTab} onChange={handleTabChange} />
            <button
              onClick={handleRefresh}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-[#71717a] transition-colors hover:bg-[#18181b] hover:text-[#f4f4f5] cursor-pointer"
              aria-label="刷新数据"
            >
              <RefreshCw size={12} aria-hidden="true" />
              刷新
            </button>
          </div>
          <SentimentBar active={sentimentFilter} onChange={setSentimentFilter} />
        </div>

        {/* ── 统计概览 ────────────────────────────────────────────────────────── */}
        <section aria-labelledby="stats-heading">
          <h2 id="stats-heading" className="sr-only">数据概览</h2>
          <StatsOverview summary={summary} loading={loading.summary} />
        </section>

        {/* ── 图表行 ─────────────────────────────────────────────────────────── */}
        <section
          aria-labelledby="charts-heading"
          className="grid grid-cols-1 gap-4 lg:grid-cols-3"
        >
          <h2 id="charts-heading" className="sr-only">图表分析</h2>

          <Card>
            <CardHeader>
              <CardTitle>情感分布</CardTitle>
            </CardHeader>
            <CardContent>
              <SentimentDonut distribution={summary?.sentiment_distribution ?? {}} />
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>情感趋势</CardTitle>
              <div className="flex gap-1" role="group" aria-label="时间范围">
                {[7, 14, 30].map((d) => (
                  <button
                    key={d}
                    onClick={() => setTrendDays(d)}
                    className={`rounded px-2 py-0.5 text-xs transition-colors cursor-pointer ${
                      trendDays === d
                        ? "bg-[#1e51a2] text-white"
                        : "text-[#71717a] hover:text-[#a1a1aa]"
                    }`}
                    aria-pressed={trendDays === d}
                  >
                    {d}天
                  </button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              {loading.trends ? (
                <div className="h-[220px] animate-pulse rounded bg-[#1c1c1f]" />
              ) : (
                <TrendLine data={trends} />
              )}
            </CardContent>
          </Card>
        </section>

        {/* ── 竞品 + 热门话题 ────────────────────────────────────────────────── */}
        <section
          aria-labelledby="insights-heading"
          className="grid grid-cols-1 gap-4 lg:grid-cols-2"
        >
          <h2 id="insights-heading" className="sr-only">深度洞察</h2>

          <Card>
            <CardHeader>
              <CardTitle>竞品对比</CardTitle>
            </CardHeader>
            <CardContent>
              {loading.competitors ? (
                <div className="h-[220px] animate-pulse rounded bg-[#1c1c1f]" />
              ) : (
                <CompetitorBar data={competitors} />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>热门话题</CardTitle>
              <span className="text-xs text-[#71717a]">过去 24h</span>
            </CardHeader>
            <CardContent>
              <HotTopics topics={topics} loading={loading.topics} />
            </CardContent>
          </Card>
        </section>

        {/* ── 笔记列表 + 实时动态 ────────────────────────────────────────────── */}
        <section
          aria-labelledby="notes-heading"
          className="grid grid-cols-1 gap-4 lg:grid-cols-3"
        >
          <h2 id="notes-heading" className="sr-only">笔记数据</h2>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>最新笔记</CardTitle>
              <span className="text-xs text-[#71717a]">按采集时间倒序</span>
            </CardHeader>
            <CardContent>
              <NotesTable notes={notes} loading={loading.notes} keywords={keywords} />
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
