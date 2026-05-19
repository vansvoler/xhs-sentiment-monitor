"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import type {
  CompetitorData,
  HotTopic,
  Note,
  NotesSummary,
  SentimentFilter,
  TrendDataPoint,
} from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CompetitorBar } from "@/components/charts/competitor-bar";
import { SentimentDonut } from "@/components/charts/sentiment-donut";
import { TrendLine } from "@/components/charts/trend-line";
import { CategoryTabs, SentimentBar } from "@/components/dashboard/category-tabs";
import type { ActiveTab } from "@/components/dashboard/category-tabs";
import { DashboardHeader } from "@/components/dashboard/header";
import { HotTopics } from "@/components/dashboard/hot-topics";
import { NotesTable } from "@/components/dashboard/notes-table";
import { RealtimeFeed } from "@/components/dashboard/realtime-feed";
import { StatsOverview } from "@/components/dashboard/stats-overview";
import {
  fetchCompetitors,
  fetchHotTopics,
  fetchKeywords,
  fetchNotes,
  fetchNotesSummary,
  fetchTrendSeries,
} from "@/lib/api";
import type { ConnectionStatus } from "@/lib/websocket";

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

export function LegacyXhsDashboard() {
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

  const loadStatic = useCallback(async () => {
    setLoading((prev) => ({ ...prev, trends: true, topics: true, competitors: true }));
    await Promise.allSettled([
      fetchTrendSeries(trendDays)
        .then(setTrends)
        .finally(() => setLoading((prev) => ({ ...prev, trends: false }))),
      fetchHotTopics(10, 24)
        .then(setTopics)
        .finally(() => setLoading((prev) => ({ ...prev, topics: false }))),
      fetchCompetitors(30)
        .then(setCompetitors)
        .finally(() => setLoading((prev) => ({ ...prev, competitors: false }))),
    ]);
  }, [trendDays]);

  const loadTabData = useCallback(async (tab: ActiveTab, sentiment: SentimentFilter) => {
    const category = tab === "all" ? undefined : tab;
    const sentimentValue = sentiment === "all" ? undefined : sentiment;

    setLoading((prev) => ({ ...prev, summary: true, notes: true }));
    await Promise.allSettled([
      fetchNotesSummary(category)
        .then(setSummary)
        .finally(() => setLoading((prev) => ({ ...prev, summary: false }))),
      fetchNotes(0, 20, category, sentimentValue)
        .then(setNotes)
        .finally(() => setLoading((prev) => ({ ...prev, notes: false }))),
    ]);
  }, []);

  useEffect(() => {
    fetchKeywords()
      .then((config) => setKeywords(config.all))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const task = setTimeout(() => {
      void loadStatic();
    }, 0);

    return () => {
      clearTimeout(task);
    };
  }, [loadStatic]);

  useEffect(() => {
    const task = setTimeout(() => {
      void loadTabData(activeTab, sentimentFilter);
    }, 0);

    return () => {
      clearTimeout(task);
    };
  }, [activeTab, sentimentFilter, loadTabData]);

  const handleTabChange = useCallback((tab: ActiveTab) => {
    setActiveTab(tab);
    setSentimentFilter("all");
  }, []);

  const handleRefresh = useCallback(() => {
    loadStatic();
    loadTabData(activeTab, sentimentFilter);
  }, [activeTab, loadStatic, loadTabData, sentimentFilter]);

  return (
    <div className="min-h-screen bg-[#09090b]">
      <DashboardHeader wsStatus={wsStatus} keywords={keywords} />

      <main className="mx-auto max-w-screen-2xl space-y-5 px-6 py-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <CategoryTabs active={activeTab} onChange={handleTabChange} />
            <button
              onClick={handleRefresh}
              className="flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-[#71717a] transition-colors hover:bg-[#18181b] hover:text-[#f4f4f5]"
              aria-label="刷新数据"
            >
              <RefreshCw size={12} aria-hidden="true" />
              刷新
            </button>
          </div>
          <SentimentBar active={sentimentFilter} onChange={setSentimentFilter} />
        </div>

        <section aria-labelledby="stats-heading">
          <h2 id="stats-heading" className="sr-only">
            数据概览
          </h2>
          <StatsOverview summary={summary} loading={loading.summary} />
        </section>

        <section aria-labelledby="charts-heading" className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <h2 id="charts-heading" className="sr-only">
            图表分析
          </h2>

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
                {[7, 14, 30].map((day) => (
                  <button
                    key={day}
                    onClick={() => setTrendDays(day)}
                    className={`cursor-pointer rounded px-2 py-0.5 text-xs transition-colors ${
                      trendDays === day
                        ? "bg-[#1e51a2] text-white"
                        : "text-[#71717a] hover:text-[#a1a1aa]"
                    }`}
                    aria-pressed={trendDays === day}
                  >
                    {day}天
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

        <section aria-labelledby="insights-heading" className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <h2 id="insights-heading" className="sr-only">
            深度洞察
          </h2>

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

        <section aria-labelledby="notes-heading" className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <h2 id="notes-heading" className="sr-only">
            笔记数据
          </h2>

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
