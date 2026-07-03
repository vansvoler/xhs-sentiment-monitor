"use client";

import { Activity } from "lucide-react";
import type { ConnectionStatus } from "@/lib/websocket";

interface HeaderProps {
  wsStatus: ConnectionStatus;
}

const STATUS_CONFIG: Record<ConnectionStatus, { label: string; color: string }> = {
  connecting:   { label: "连接中", color: "#e08a1e" },
  connected:    { label: "实时",   color: "#16a34a" },
  disconnected: { label: "已断线", color: "#ea5457" },
};

export function DashboardHeader({ wsStatus }: HeaderProps) {
  const cfg = STATUS_CONFIG[wsStatus];

  return (
    <header className="sticky top-0 z-40 border-b border-[#dce1e9] bg-[#f4f6fa]/90 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-screen-2xl items-center justify-between px-6">
        {/* 品牌 */}
        <div className="flex items-center gap-3">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ background: "linear-gradient(135deg, #1e51a2, #1e51a2)" }}
          >
            <Activity size={15} className="text-white" aria-hidden="true" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold leading-tight text-[#17233f]">
              小红书舆情监控
            </span>
            <span className="text-[12px] leading-tight text-[#7b8494]">
              小红书品牌分析
            </span>
          </div>
        </div>

        {/* 实时状态 */}
        <div
          className="flex items-center gap-1.5 rounded-full border border-[#dce1e9] bg-[#ffffff] px-3 py-1"
          role="status"
          aria-label={`WebSocket 状态：${cfg.label}`}
        >
          <span
            className="h-2 w-2 rounded-full animate-pulse-dot"
            style={{ background: cfg.color }}
            aria-hidden="true"
          />
          <span className="text-xs text-[#5a6474]">{cfg.label}</span>
        </div>
      </div>
    </header>
  );
}
