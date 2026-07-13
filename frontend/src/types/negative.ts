// 负面舆情工作台：笔记与评论统一成同构条目
import type { AuthorInfo, CategoryType, SentimentResult } from "./note";

export type NegativeKind = "note" | "comment";
export type HandleStatus = "open" | "handled";
export type NegativeStatusFilter = HandleStatus | "all";
export type NegativeSort = "influence" | "latest";

export interface NegativeItem {
  kind: NegativeKind;
  id: string;
  note_id: string;
  title: string;
  excerpt: string;
  author: AuthorInfo;
  sentiment: SentimentResult;
  keyword?: string | null;
  category?: CategoryType | null;
  happened_at: string;
  likes: number;
  url: string;
  handle_status: HandleStatus;
}

export interface NegativeSummary {
  notes_open: number;
  comments_open: number;
}
