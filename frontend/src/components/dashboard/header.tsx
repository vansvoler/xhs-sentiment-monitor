"use client";

import { Activity } from "lucide-react";
import type { ConnectionStatus } from "@/lib/websocket";

interface HeaderProps {
  wsStatus: ConnectionStatus;
  keywords: string[];
}

const STATUS_CONFIG: Record<ConnectionStatus, { label: string; color: string }> = {
  connecting:   { label: "连接中", color: "#f59e0b" },
  connected:    { label: "实时",   color: "#22c55e" },
  disconnected: { label: "已断线", color: "#f87171" },
};

const MAX_VISIBLE = 8;

export function DashboardHeader({ wsStatus, keywords }: HeaderProps) {
  const cfg = STATUS_CONFIG[wsStatus];
  const visible = keywords.slice(0, MAX_VISIBLE);
  const overflow = keywords.length - MAX_VISIBLE;

  return (
    <header className="sticky top-0 z-40 border-b border-[#27272a] bg-[#09090b]/90 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-screen-2xl items-center justify-between px-6">
        {/* 品牌 */}
        <div className="flex items-center gap-3">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ background: "linear-gradient(135deg, #1e51a2, #2563eb)" }}
          >
            <Activity size={15} className="text-white" aria-hidden="true" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold leading-tight text-[#ffffff]">
              小红书舆情监控
            </span>
            <span className="text-[10px] leading-tight text-[#71717a]">
              小红书品牌分析
            </span>
          </div>
        </div>

        {/* 监控关键词 */}
        {visible.length > 0 && (
          <div className="hidden md:flex items-center gap-1.5" aria-label="监控关键词">
            <span className="text-xs text-[#71717a]">监控：</span>
            <div className="flex flex-wrap gap-1">
              {visible.map((kw) => (
                <span
                  key={kw}
                  className="rounded px-1.5 py-0.5 text-xs bg-[#18181b] text-[#a1a1aa] border border-[#27272a]"
                >
                  {kw}
                </span>
              ))}
              {overflow > 0 && (
                <span className="rounded px-1.5 py-0.5 text-xs bg-[#18181b] text-[#71717a] border border-[#27272a]">
                  +{overflow}
                </span>
              )}
            </div>
          </div>
        )}

        {/* 实时状态 */}
        <div
          className="flex items-center gap-1.5 rounded-full border border-[#27272a] bg-[#111113] px-3 py-1"
          role="status"
          aria-label={`WebSocket 状态：${cfg.label}`}
        >
          <span
            className="h-2 w-2 rounded-full animate-pulse-dot"
            style={{ background: cfg.color }}
            aria-hidden="true"
          />
          <span className="text-xs text-[#a1a1aa]">{cfg.label}</span>
        </div>
      </div>
    </header>
  );
}
