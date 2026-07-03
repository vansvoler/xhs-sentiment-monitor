export type IntelSourceKey =
  | "overview"
  | "ucas"
  | "university_site"
  | "exam_board"
  | "visa_policy"
  | "wechat_media";

export type IntelSourceFeedKey = Exclude<IntelSourceKey, "overview">;

export type IntelAdapterType =
  | "feed"
  | "listing"
  | "rss"
  | "json_feed"
  | "html_listing";

export interface ListingSelectors {
  item: string;
  title: string;
  url: string;
  summary?: string | null;
  date?: string | null;
}

export interface IntelSourceConfig {
  source_id: string;
  source_type: IntelSourceFeedKey;
  school_name?: string | null;
  adapter_type: IntelAdapterType;
  source_group: string;
  source_name: string;
  feed_url?: string | null;
  listing_url?: string | null;
  selectors?: ListingSelectors | null;
  enabled?: boolean;
}

export interface ProbeIntelSourceRequest {
  url: string;
  source_type: IntelSourceFeedKey;
  source_name?: string | null;
  source_group: string;
}

export type ProbeIntelSourceStatus = "success" | "blocked" | "unsupported";

export interface ProbeIntelSourceResponse {
  status: ProbeIntelSourceStatus;
  message: string;
  sample_count: number;
  recommended_source: IntelSourceConfig;
}

export type CreateIntelSourceRequest = IntelSourceConfig;

export interface CreateIntelSourceResponse {
  source: IntelSourceConfig;
  item_count: number;
  sync_report: IntelSourceSyncReport;
}

export interface IntelItem {
  item_id: string;
  source_type: IntelSourceFeedKey;
  source_name: string;
  title: string;
  summary_short: string;
  summary_long: string;
  impact_targets: string[];
  published_at: string;
  collected_at: string;
  original_url: string;
  school_name?: string;
  source_group?: string;
}

export type IntelSourceSyncStatus = "success" | "blocked" | "error";

export interface IntelSourceSyncReport {
  source_id: string;
  source_type: IntelSourceFeedKey;
  source_name: string;
  school_name?: string;
  status: IntelSourceSyncStatus;
  item_count: number;
  error_message?: string | null;
  notes?: string | null;
  synced_at: string;
}

export interface IntelOverviewSection {
  source_key: IntelSourceFeedKey;
  source_label: string;
  total_items: number;
  preview_items: IntelItem[];
}

export interface IntelHelperRail {
  highlight_count: number;
  top_counts: Record<string, number>;
}

export interface IntelOverviewResponse {
  sections: IntelOverviewSection[];
  helper_rail: IntelHelperRail;
}

export interface IntelSourceResponse {
  source_key: IntelSourceFeedKey;
  items: IntelItem[];
  helper_rail: IntelHelperRail;
  sync_reports: IntelSourceSyncReport[];
}

export interface IntelSourceSyncStatusResponse {
  source_key: IntelSourceFeedKey;
  reports: IntelSourceSyncReport[];
}

export interface SourceNavItem {
  key: IntelSourceKey;
  label: string;
}
