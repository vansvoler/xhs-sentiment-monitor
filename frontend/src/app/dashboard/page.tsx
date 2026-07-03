"use client";

import { Plus } from "lucide-react";
import { useEffect, useState } from "react";

import { AddSourceDialog } from "@/components/operations-dashboard/shell/add-source-dialog";
import { DashboardShell } from "@/components/operations-dashboard/shell/dashboard-shell";
import { OperationsErrorState } from "@/components/operations-dashboard/shell/error-state";
import { OperationsLoadingState } from "@/components/operations-dashboard/shell/loading-state";
import { OverviewPanel } from "@/components/operations-dashboard/overview/overview-panel";
import { SourcePanel } from "@/components/operations-dashboard/source/source-panel";
import {
  fetchIntelOverview,
  fetchIntelSource,
  fetchIntelSourceSyncStatus,
  fetchSourceNav,
} from "@/lib/intel-api";
import type {
  IntelOverviewResponse,
  IntelSourceConfig,
  IntelSourceKey,
  IntelSourceResponse,
  IntelSourceSyncReport,
  IntelSourceSyncStatusResponse,
  SourceNavItem,
} from "@/types";

type PageStatus = "loading" | "ready" | "error";

const FALLBACK_NAV_ITEMS: SourceNavItem[] = [
  { key: "overview", label: "总览" },
  { key: "ucas", label: "UCAS" },
  { key: "university_site", label: "海外大学官网" },
  { key: "exam_board", label: "考试局" },
  { key: "visa_policy", label: "签证政策" },
  { key: "wechat_media", label: "媒体公众号" },
];

const EMPTY_UNIVERSITY_SYNC_STATUS: IntelSourceSyncStatusResponse = {
  source_key: "university_site",
  reports: [],
};

const EMPTY_UNIVERSITY_SOURCE: IntelSourceResponse = {
  source_key: "university_site",
  items: [],
  helper_rail: {
    highlight_count: 0,
    top_counts: {},
  },
  sync_reports: [],
};

export default function DashboardPage() {
  const [navItems, setNavItems] = useState<SourceNavItem[]>(FALLBACK_NAV_ITEMS);
  const [activeKey, setActiveKey] = useState<IntelSourceKey>("overview");
  const [overview, setOverview] = useState<IntelOverviewResponse | null>(null);
  const [sourceData, setSourceData] = useState<IntelSourceResponse | null>(null);
  const [universitySourceData, setUniversitySourceData] =
    useState<IntelSourceResponse>(EMPTY_UNIVERSITY_SOURCE);
  const [universitySyncReports, setUniversitySyncReports] = useState<IntelSourceSyncReport[]>([]);
  const [status, setStatus] = useState<PageStatus>("loading");
  const [isAddSourceOpen, setIsAddSourceOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);

  const handleSourceChange = (nextKey: IntelSourceKey) => {
    setStatus("loading");
    setActiveKey(nextKey);
  };

  useEffect(() => {
    fetchSourceNav()
      .then((payload) => setNavItems(payload.items))
      .catch(() => {});
  }, [reloadToken]);

  useEffect(() => {
    if (!saveNotice) return;

    const timer = window.setTimeout(() => setSaveNotice(null), 3600);
    return () => window.clearTimeout(timer);
  }, [saveNotice]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        if (activeKey === "overview") {
          const [overviewPayload, universityPayload, syncPayload] = await Promise.all([
            fetchIntelOverview(),
            fetchIntelSource("university_site").catch(() => EMPTY_UNIVERSITY_SOURCE),
            fetchIntelSourceSyncStatus("university_site").catch(
              () => EMPTY_UNIVERSITY_SYNC_STATUS,
            ),
          ]);
          if (!cancelled) {
            setOverview(overviewPayload);
            setUniversitySourceData(universityPayload);
            setUniversitySyncReports(
              universityPayload.sync_reports.length > 0
                ? universityPayload.sync_reports
                : syncPayload.reports,
            );
            setSourceData(null);
            setStatus("ready");
          }
          return;
        }

        const payload = await fetchIntelSource(activeKey);
        if (!cancelled) {
          setSourceData(payload);
          if (activeKey === "university_site") {
            setUniversitySourceData(payload);
            setUniversitySyncReports(payload.sync_reports);
          }
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
  }, [activeKey, reloadToken]);

  const handleSourceSaved = (source: IntelSourceConfig, itemCount: number) => {
    setSaveNotice(`${source.source_name} 已保存并同步 ${itemCount} 条`);
    setReloadToken((value) => value + 1);
  };

  return (
    <DashboardShell
      items={navItems}
      activeKey={activeKey}
      helperRail={overview?.helper_rail ?? sourceData?.helper_rail ?? null}
      onChange={handleSourceChange}
      action={
        <button
          type="button"
          onClick={() => setIsAddSourceOpen(true)}
          className="inline-flex h-10 items-center gap-2 rounded-md border border-[#1e51a2] bg-[#1e51a2] px-4 text-sm text-white transition-colors hover:bg-[#1a4690]"
        >
          <Plus className="size-4" />
          添加信源
        </button>
      }
    >
      {saveNotice && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-[#15803d]">
          {saveNotice}
        </div>
      )}
      {status === "loading" && <OperationsLoadingState />}
      {status === "error" && <OperationsErrorState />}
      {status === "ready" && overview && (
        <OverviewPanel
          data={overview}
          universityItems={universitySourceData.items}
          universitySyncReports={universitySyncReports}
          onOpenSource={handleSourceChange}
        />
      )}
      {status === "ready" && sourceData && <SourcePanel data={sourceData} />}
      <AddSourceDialog
        open={isAddSourceOpen}
        onClose={() => setIsAddSourceOpen(false)}
        onSaved={handleSourceSaved}
      />
    </DashboardShell>
  );
}
