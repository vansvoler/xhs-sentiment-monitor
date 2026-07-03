"use client";

import { Check, Loader2, Save, Search, X } from "lucide-react";
import { useState } from "react";

import { createIntelSource, probeIntelSource } from "@/lib/intel-api";
import type {
  IntelSourceConfig,
  IntelSourceFeedKey,
  ProbeIntelSourceResponse,
} from "@/types";

const SOURCE_OPTIONS: Array<{ key: IntelSourceFeedKey; label: string }> = [
  { key: "university_site", label: "海外大学官网" },
  { key: "exam_board", label: "考试局" },
  { key: "visa_policy", label: "签证政策" },
  { key: "wechat_media", label: "媒体公众号" },
  { key: "ucas", label: "UCAS" },
];

type DialogPhase = "idle" | "probing" | "preview" | "saving";

interface AddSourceDialogProps {
  open: boolean;
  onClose: () => void;
  onSaved: (source: IntelSourceConfig, itemCount: number) => void;
}

function statusLabel(status: ProbeIntelSourceResponse["status"]) {
  if (status === "success") return "可用";
  if (status === "blocked") return "被拦截";
  return "不支持";
}

function normalizeUrl(rawUrl: string) {
  const value = rawUrl.trim();
  const parsed = new URL(value);
  return parsed.toString();
}

export function AddSourceDialog({
  open,
  onClose,
  onSaved,
}: AddSourceDialogProps) {
  const [phase, setPhase] = useState<DialogPhase>("idle");
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] =
    useState<IntelSourceFeedKey>("university_site");
  const [sourceName, setSourceName] = useState("");
  const [sourceGroup, setSourceGroup] = useState("自定义来源");
  const [probeResult, setProbeResult] = useState<ProbeIntelSourceResponse | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!open) return null;

  const isProbing = phase === "probing";
  const isSaving = phase === "saving";
  const canSave =
    phase === "preview" &&
    probeResult?.status === "success" &&
    sourceName.trim().length > 0 &&
    sourceGroup.trim().length > 0;

  const handleProbe = async () => {
    setErrorMessage(null);
    setProbeResult(null);

    let normalizedUrl: string;
    try {
      normalizedUrl = normalizeUrl(url);
    } catch {
      setErrorMessage("请输入完整 URL，例如 https://example.com/news");
      return;
    }

    setPhase("probing");
    try {
      const result = await probeIntelSource({
        url: normalizedUrl,
        source_type: sourceType,
        source_name: sourceName.trim() || null,
        source_group: sourceGroup.trim() || "自定义来源",
      });
      setUrl(normalizedUrl);
      setProbeResult(result);
      setSourceType(result.recommended_source.source_type);
      setSourceName(result.recommended_source.source_name);
      setSourceGroup(result.recommended_source.source_group);
      setPhase("preview");
    } catch (error) {
      setPhase("idle");
      setErrorMessage(error instanceof Error ? error.message : "探测失败");
    }
  };

  const handleSave = async () => {
    if (!probeResult || !canSave) return;

    setErrorMessage(null);
    setPhase("saving");
    try {
      const payload: IntelSourceConfig = {
        ...probeResult.recommended_source,
        source_type: sourceType,
        source_name: sourceName.trim(),
        source_group: sourceGroup.trim(),
      };
      const result = await createIntelSource(payload);
      onSaved(result.source, result.item_count);
      onClose();
    } catch (error) {
      setPhase("preview");
      setErrorMessage(error instanceof Error ? error.message : "保存失败");
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 px-4">
      <section className="w-full max-w-2xl rounded-[10px] border border-[#dce1e9] bg-[#ffffff] shadow-2xl">
        <header className="flex items-center justify-between gap-4 border-b border-[#dce1e9] px-5 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#7b8494]">
              Source Setup
            </p>
            <h2 className="mt-1 text-lg font-semibold text-[#17233f]">添加信源</h2>
          </div>
          <button
            type="button"
            aria-label="关闭"
            onClick={onClose}
            className="grid size-9 place-items-center rounded-md text-[#5a6474] transition-colors hover:bg-[#eef2f8] hover:text-[#17233f]"
          >
            <X className="size-4" />
          </button>
        </header>

        <div className="space-y-4 px-5 py-5">
          <label className="block">
            <span className="text-xs font-medium text-[#5a6474]">目标 URL</span>
            <input
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com/news"
              className="mt-2 h-11 w-full rounded-md border border-[#dce1e9] bg-[#ffffff] px-3 text-sm text-[#17233f] outline-none transition-colors placeholder:text-[#727171] focus:border-[#1e51a2]"
            />
          </label>

          <div className="grid gap-3 md:grid-cols-[1fr_1fr_1.2fr]">
            <label className="block">
              <span className="text-xs font-medium text-[#5a6474]">分类</span>
              <select
                value={sourceType}
                onChange={(event) =>
                  setSourceType(event.target.value as IntelSourceFeedKey)
                }
                className="mt-2 h-11 w-full rounded-md border border-[#dce1e9] bg-[#ffffff] px-3 text-sm text-[#17233f] outline-none transition-colors focus:border-[#1e51a2]"
              >
                {SOURCE_OPTIONS.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-medium text-[#5a6474]">分组</span>
              <input
                value={sourceGroup}
                onChange={(event) => setSourceGroup(event.target.value)}
                className="mt-2 h-11 w-full rounded-md border border-[#dce1e9] bg-[#ffffff] px-3 text-sm text-[#17233f] outline-none transition-colors focus:border-[#1e51a2]"
              />
            </label>

            <label className="block">
              <span className="text-xs font-medium text-[#5a6474]">名称</span>
              <input
                value={sourceName}
                onChange={(event) => setSourceName(event.target.value)}
                placeholder="留空则由后端推断"
                className="mt-2 h-11 w-full rounded-md border border-[#dce1e9] bg-[#ffffff] px-3 text-sm text-[#17233f] outline-none transition-colors placeholder:text-[#727171] focus:border-[#1e51a2]"
              />
            </label>
          </div>

          {probeResult && (
            <div className="rounded-lg border border-[#dce1e9] bg-[#ffffff] p-4">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="rounded bg-[#eef2f8] px-2 py-1 text-[#17233f]">
                  {statusLabel(probeResult.status)}
                </span>
                <span className="text-[#5a6474]">
                  {probeResult.recommended_source.adapter_type}
                </span>
                <span className="text-[#7b8494]">
                  样本 {probeResult.sample_count}
                </span>
              </div>
              <p className="mt-3 text-sm text-[#4b5563]">{probeResult.message}</p>
              <p className="mt-2 break-all text-xs text-[#7b8494]">
                {probeResult.recommended_source.feed_url ??
                  probeResult.recommended_source.listing_url}
              </p>
            </div>
          )}

          {errorMessage && (
            <div className="rounded-md border border-rose-500/25 bg-rose-500/10 px-3 py-2 text-sm text-[#b91c1c]">
              {errorMessage}
            </div>
          )}
        </div>

        <footer className="flex items-center justify-end gap-3 border-t border-[#dce1e9] px-5 py-4">
          <button
            type="button"
            onClick={handleProbe}
            disabled={isProbing || isSaving}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-[#dce1e9] px-4 text-sm text-[#17233f] transition-colors hover:bg-[#eef2f8] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isProbing ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Search className="size-4" />
            )}
            探测
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave || isSaving}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-[#1e51a2] px-4 text-sm font-medium text-white transition-colors hover:bg-[#1a4690] disabled:cursor-not-allowed disabled:bg-[#dce1e9] disabled:text-[#7b8494]"
          >
            {isSaving ? (
              <Loader2 className="size-4 animate-spin" />
            ) : canSave ? (
              <Save className="size-4" />
            ) : (
              <Check className="size-4" />
            )}
            保存
          </button>
        </footer>
      </section>
    </div>
  );
}
