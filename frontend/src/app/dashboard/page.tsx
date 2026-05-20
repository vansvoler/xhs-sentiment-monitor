"use client";

import { useEffect, useState } from "react";

import { OperationsErrorState } from "@/components/operations-dashboard/error-state";
import { OperationsHelperRail } from "@/components/operations-dashboard/helper-rail";
import { OperationsLoadingState } from "@/components/operations-dashboard/loading-state";
import { OverviewPanel } from "@/components/operations-dashboard/overview-panel";
import { OperationsSidebar } from "@/components/operations-dashboard/sidebar";
import { SourcePanel } from "@/components/operations-dashboard/source-panel";
import {
  fetchIntelOverview,
  fetchIntelSource,
  fetchSourceNav,
} from "@/lib/intel-api";
import type {
  IntelOverviewResponse,
  IntelSourceKey,
  IntelSourceResponse,
  SourceNavItem,
} from "@/types";

type PageStatus = "loading" | "ready" | "error";

const FALLBACK_NAV_ITEMS: SourceNavItem[] = [
  { key: "overview", label: "总览" },
  { key: "xiaohongshu", label: "小红书" },
  { key: "ucas", label: "UCAS" },
  { key: "university_site", label: "海外大学官网" },
  { key: "wechat_media", label: "媒体公众号" },
];

export default function DashboardPage() {
  const [navItems, setNavItems] = useState<SourceNavItem[]>(FALLBACK_NAV_ITEMS);
  const [activeKey, setActiveKey] = useState<IntelSourceKey>("overview");
  const [overview, setOverview] = useState<IntelOverviewResponse | null>(null);
  const [sourceData, setSourceData] = useState<IntelSourceResponse | null>(null);
  const [status, setStatus] = useState<PageStatus>("loading");

  const handleSourceChange = (nextKey: IntelSourceKey) => {
    setStatus("loading");
    setActiveKey(nextKey);
  };

  useEffect(() => {
    fetchSourceNav()
      .then((payload) => setNavItems(payload.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        if (activeKey === "overview") {
          const payload = await fetchIntelOverview();
          if (!cancelled) {
            setOverview(payload);
            setSourceData(null);
            setStatus("ready");
          }
          return;
        }

        const payload = await fetchIntelSource(activeKey);
        if (!cancelled) {
          setSourceData(payload);
          setOverview(null);
          setStatus("ready");
        }
      } catch {
        if (!cancelled) {
          setStatus("error");
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [activeKey]);

  return (
    <div className="min-h-screen bg-[#09090b] text-[#f4f4f5]">
      <main className="mx-auto flex min-h-screen max-w-screen-2xl">
        <OperationsSidebar
          items={navItems}
          activeKey={activeKey}
          onChange={handleSourceChange}
        />
        <section className="min-w-0 flex-1 px-6 py-6">
          {status === "loading" && <OperationsLoadingState />}
          {status === "error" && <OperationsErrorState />}
          {status === "ready" && overview && <OverviewPanel data={overview} />}
          {status === "ready" && sourceData && <SourcePanel data={sourceData} />}
        </section>
        <OperationsHelperRail data={overview?.helper_rail ?? sourceData?.helper_rail ?? null} />
      </main>
    </div>
  );
}
