"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Check,
  ExternalLink,
  Heart,
  RotateCcw,
  Users,
} from "lucide-react";

import type {
  CategoryType,
  NegativeItem,
  NegativeSort,
  NegativeStatusFilter,
  NegativeSummary,
} from "@/types";
import {
  fetchNegativeItems,
  fetchNegativeSummary,
  setNegativeStatus,
} from "@/lib/api";
import { formatNumber, formatRelative } from "@/lib/utils";
import { SentimentBadge, TagBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

const PAGE_SIZE = 20;

type CatFilter = CategoryType | "";
const CAT_TABS: { key: CatFilter; label: string }[] = [
  { key: "", label: "全部" },
  { key: "brand", label: "品牌" },
  { key: "competitor", label: "竞品" },
  { key: "industry", label: "行业" },
];
const STATUS_TABS: { key: NegativeStatusFilter; label: string }[] = [
  { key: "open", label: "未处置" },
  { key: "handled", label: "已处置" },
  { key: "all", label: "全部" },
];
const SORT_TABS: { key: NegativeSort; label: string }[] = [
  { key: "influence", label: "按影响力" },
  { key: "latest", label: "按时间" },
];

export function NegativeWorkspace() {
  const [category, setCategory] = useState<CatFilter>("");
  const [status, setStatus] = useState<NegativeStatusFilter>("open");
  const [sort, setSort] = useState<NegativeSort>("influence");

  const [items, setItems] = useState<NegativeItem[]>([]);
  const [summary, setSummary] = useState<NegativeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);

  // 评论采集已关停，工作台只看负面笔记
  const query = useCallback(
    (skip: number) =>
      fetchNegativeItems({
        kind: "note",
        skip,
        limit: PAGE_SIZE,
        category: category || undefined,
        status,
        sort,
      }),
    [category, status, sort],
  );

  // 筛选变化 → 重载第一页
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    query(0)
      .then((data) => {
        if (cancelled) return;
        setItems(data);
        setHasMore(data.length === PAGE_SIZE);
      })
      .catch(() => setItems([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [query]);

  useEffect(() => {
    fetchNegativeSummary().then(setSummary).catch(() => {});
  }, []);

  const loadMore = useCallback(async () => {
    const data = await query(items.length).catch(() => []);
    setItems((prev) => [...prev, ...data]);
    setHasMore(data.length === PAGE_SIZE);
  }, [query, items.length]);

  // 处置/恢复：乐观更新本地状态与徽标计数
  const toggle = useCallback(
    async (item: NegativeItem) => {
      const next = item.handle_status === "handled" ? "open" : "handled";
      setItems((prev) =>
        prev.map((i) =>
          i.id === item.id ? { ...i, handle_status: next } : i,
        ),
      );
      setSummary((s) => {
        if (!s) return s;
        const delta = next === "handled" ? -1 : 1;
        return { ...s, notes_open: Math.max(0, s.notes_open + delta) };
      });
      await setNegativeStatus("note", item.id, next).catch(() => {});
    },
    [],
  );

  return (
    <div className="min-h-screen bg-[#f4f6fa]">
      <header className="sticky top-0 z-40 border-b border-[#dce1e9] bg-[#f4f6fa]/90 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-screen-lg items-center gap-3 px-6">
          <Link
            href="/dashboard"
            className="flex items-center gap-1 text-xs text-[#7b8494] transition-colors hover:text-[#1f2a44]"
          >
            <ArrowLeft size={13} aria-hidden="true" />
            返回
          </Link>
          <span className="text-sm font-semibold text-[#17233f]">
            负面舆情工作台
          </span>
          {summary && (
            <span className="text-xs text-[#7b8494]">
              待处置负面笔记 {summary.notes_open}
            </span>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-screen-lg space-y-4 px-6 py-6">
        {/* 筛选条 */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <FilterGroup value={category} options={CAT_TABS} onChange={setCategory} />
          <div className="flex items-center gap-3">
            <FilterGroup value={sort} options={SORT_TABS} onChange={setSort} />
            <FilterGroup value={status} options={STATUS_TABS} onChange={setStatus} />
          </div>
        </div>

        {/* 列表 */}
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="rounded-lg border border-[#eaeef4] bg-white p-4 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <p className="py-16 text-center text-sm text-[#16a34a]">
            {status === "open" ? "该筛选下没有待处置的负面内容 ✓" : "暂无数据"}
          </p>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <ItemCard key={item.id} item={item} onToggle={toggle} />
            ))}
          </div>
        )}

        {hasMore && !loading && (
          <button
            onClick={loadMore}
            className="w-full cursor-pointer rounded-lg border border-[#dce1e9] bg-white py-2 text-xs text-[#5a6474] transition-colors hover:bg-[#eef2f8]"
          >
            加载更多
          </button>
        )}
      </main>
    </div>
  );
}

function FilterGroup<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { key: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex gap-1">
      {options.map((o) => (
        <button
          key={o.key}
          onClick={() => onChange(o.key)}
          aria-pressed={value === o.key}
          className={`cursor-pointer rounded px-2 py-0.5 text-xs transition-colors ${
            value === o.key
              ? "bg-[#1e51a2] text-white"
              : "text-[#7b8494] hover:bg-[#eef2f8] hover:text-[#1f2a44]"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function ItemCard({
  item,
  onToggle,
}: {
  item: NegativeItem;
  onToggle: (item: NegativeItem) => void;
}) {
  const handled = item.handle_status === "handled";
  return (
    <article
      className={`rounded-lg border border-[#eaeef4] bg-white p-4 transition-opacity animate-fade-in ${
        handled ? "opacity-50" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <SentimentBadge label={item.sentiment.label} score={item.sentiment.score} />
            {item.keyword && <TagBadge>{item.keyword}</TagBadge>}
          </div>
          <p className="mt-2 text-sm text-[#1f2a44]">{item.title}</p>
          {item.excerpt && (
            <p className="mt-0.5 line-clamp-2 text-xs text-[#5a6474]">{item.excerpt}</p>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-[#7b8494]">
        <span>{item.author.nickname}</span>
        {item.author.fans_count > 0 && (
          <span className="flex items-center gap-1">
            <Users size={11} aria-hidden="true" />
            <span className="font-mono">{formatNumber(item.author.fans_count)}</span>
          </span>
        )}
        <span className="flex items-center gap-1">
          <Heart size={11} aria-hidden="true" />
          <span className="font-mono">{formatNumber(item.likes)}</span>
        </span>
        <span>{formatRelative(item.happened_at)}</span>
        <div className="ml-auto flex items-center gap-1">
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-[#1e51a2] transition-colors hover:bg-[#eef2f8]"
          >
            <ExternalLink size={11} aria-hidden="true" />
            原文
          </a>
          <button
            onClick={() => onToggle(item)}
            className="flex cursor-pointer items-center gap-1 rounded px-2 py-1 text-xs text-[#7b8494] transition-colors hover:bg-[#eef2f8] hover:text-[#1f2a44]"
          >
            {handled ? (
              <>
                <RotateCcw size={11} aria-hidden="true" />
                恢复
              </>
            ) : (
              <>
                <Check size={11} aria-hidden="true" />
                标记已处置
              </>
            )}
          </button>
        </div>
      </div>
    </article>
  );
}
