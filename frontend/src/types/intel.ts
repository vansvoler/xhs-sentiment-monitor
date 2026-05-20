export type IntelSourceKey =
  | "overview"
  | "xiaohongshu"
  | "ucas"
  | "university_site"
  | "wechat_media";

export type IntelSourceFeedKey = Exclude<IntelSourceKey, "overview">;

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
}

export interface SourceNavItem {
  key: IntelSourceKey;
  label: string;
}
