"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bell, Check, TrendingUp } from "lucide-react";

import type {
  Alert,
  AlertLevel,
  AlertType,
  CategoryType,
  KeywordConfig,
  WsMessage,
} from "@/types";
import { fetchAlerts, acknowledgeAlert } from "@/lib/api";
import { useWebSocket } from "@/lib/websocket";
import { formatRelative } from "@/lib/utils";

// 级别 → 配色（左边框 / 文字 / 背景）
const LEVEL_STYLE: Record<AlertLevel, { bar: string; text: string; bg: string }> = {
  critical: { bar: "#dc2626", text: "#dc2626", bg: "rgba(239,68,68,0.06)" },
  warning: { bar: "#e08a1e", text: "#b45309", bg: "rgba(245,158,11,0.06)" },
  info: { bar: "#1e51a2", text: "#6f94cd", bg: "rgba(30,81,162,0.06)" },
};

const TYPE_ICON: Record<AlertType, typeof AlertTriangle> = {
  negative_note: AlertTriangle,
  negative_comment: AlertTriangle,
  negative_rate: AlertTriangle,
  volume_spike: TrendingUp,
};

type CatFilter = CategoryType | "all";
const CAT_TABS: { key: CatFilter; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "brand", label: "品牌" },
  { key: "competitor", label: "竞品" },
  { key: "industry", label: "行业" },
];

const MAX_ITEMS = 60;

export function AlertPanel({ keywordConfig }: { keywordConfig: KeywordConfig | null }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [cat, setCat] = useState<CatFilter>("all");

  useEffect(() => {
    fetchAlerts({ limit: MAX_ITEMS })
      .then(setAlerts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type !== "alert") return;
    const incoming = msg.data as Alert;
    setAlerts((prev) => {
      if (prev.some((a) => a.alert_id === incoming.alert_id)) return prev;
      return [incoming, ...prev].slice(0, MAX_ITEMS);
    });
  }, []);
  useWebSocket(handleMessage);

  const handleAck = useCallback(async (id: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.alert_id === id ? { ...a, status: "acknowledged" } : a)),
    );
    await acknowledgeAlert(id).catch(() => {});
  }, []);

  // 关键词 → 分类映射（用于把每条预警归到品牌/竞品/行业）
  const kwCat = useMemo(() => {
    const m = new Map<string, CategoryType>();
    if (keywordConfig) {
      for (const k of keywordConfig.brand) m.set(k, "brand");
      for (const k of keywordConfig.competitor) m.set(k, "competitor");
      for (const k of keywordConfig.industry) m.set(k, "industry");
    }
    return m;
  }, [keywordConfig]);

  const catOf = useCallback(
    (a: Alert): CatFilter => (a.keyword ? kwCat.get(a.keyword) ?? "all" : "all"),
    [kwCat],
  );

  // 各分类条数（用于 tab 徽标）
  const counts = useMemo(() => {
    const c: Record<CatFilter, number> = { all: alerts.length, brand: 0, competitor: 0, industry: 0 };
    for (const a of alerts) {
      const k = catOf(a);
      if (k !== "all") c[k] += 1;
    }
    return c;
  }, [alerts, catOf]);

  const visible = cat === "all" ? alerts : alerts.filter((a) => catOf(a) === cat);
  const openCount = alerts.filter((a) => a.status === "open").length;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Bell size={14} className="text-[#e08a1e]" aria-hidden="true" />
        <span className="text-sm font-medium text-[#1f2a44]">舆情预警</span>
        {openCount > 0 && (
          <span className="rounded-full bg-[#dc2626] px-1.5 py-0.5 text-[12px] font-semibold text-white">
            {openCount}
          </span>
        )}
        {/* 分类子标签 */}
        {!loading && alerts.length > 0 && (
          <div className="ml-auto flex items-center gap-1">
            {CAT_TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setCat(t.key)}
                className={`rounded px-2 py-0.5 text-xs transition-colors ${
                  cat === t.key
                    ? "bg-[#1e51a2] text-white"
                    : "text-[#7b8494] hover:bg-[#eef2f8] hover:text-[#1f2a44]"
                }`}
              >
                {t.label}
                <span className={cat === t.key ? "opacity-80" : "text-[#9aa1ac]"}> {counts[t.key]}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {loading ? (
        <div className="h-[120px] animate-pulse rounded bg-[#eaeef4]" />
      ) : alerts.length === 0 ? (
        <p className="py-1 text-xs text-[#16a34a]">舆情平稳 · 暂无预警 ✓</p>
      ) : visible.length === 0 ? (
        <p className="py-4 text-center text-xs text-[#7b8494]">该分类暂无预警</p>
      ) : (
        <div
          className="max-h-[320px] space-y-2 overflow-y-auto pr-1"
          aria-live="polite"
          aria-label="舆情预警列表"
        >
          {visible.map((a) => (
            <AlertRow key={a.alert_id} alert={a} onAck={handleAck} />
          ))}
        </div>
      )}
    </div>
  );
}

function AlertRow({ alert, onAck }: { alert: Alert; onAck: (id: string) => void }) {
  const s = LEVEL_STYLE[alert.level];
  const Icon = TYPE_ICON[alert.type];
  const acked = alert.status === "acknowledged";

  return (
    <div
      className={`flex items-start gap-2.5 rounded-lg border-l-2 p-2.5 transition-opacity ${acked ? "opacity-50" : ""}`}
      style={{ borderLeftColor: s.bar, backgroundColor: s.bg }}
    >
      <Icon size={14} className="mt-0.5 shrink-0" style={{ color: s.bar }} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium" style={{ color: s.text }}>
            {alert.title}
          </span>
          {alert.keyword && (
            <span className="rounded bg-[#eaeef4] px-1.5 py-0.5 text-[12px] text-[#5a6474]">
              {alert.keyword}
            </span>
          )}
        </div>
        <p className="mt-0.5 truncate text-xs text-[#5a6474]">{alert.message}</p>
        <span className="text-[12px] text-[#7b8494]">{formatRelative(alert.created_at)}</span>
      </div>
      {!acked && (
        <button
          onClick={() => onAck(alert.alert_id)}
          className="flex shrink-0 cursor-pointer items-center gap-1 rounded px-1.5 py-1 text-[12px] text-[#7b8494] transition-colors hover:bg-[#eef2f8] hover:text-[#1f2a44]"
          aria-label="标记已读"
        >
          <Check size={11} aria-hidden="true" />
          已读
        </button>
      )}
    </div>
  );
}
