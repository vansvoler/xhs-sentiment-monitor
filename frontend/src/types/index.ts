// ── 枚举 ──────────────────────────────────────────────────────────────────────

export type SentimentLabel = "positive" | "negative" | "neutral";
export type EmotionType = "anger" | "joy" | "sadness" | "fear" | "surprise" | "neutral";
export type NoteType = "normal" | "video" | "live";
export type CategoryType = "brand" | "competitor" | "industry";

// ── 嵌套结构 ──────────────────────────────────────────────────────────────────

export interface SentimentResult {
  label: SentimentLabel;
  score: number;
  emotion: EmotionType;
}

export interface AuthorInfo {
  user_id: string;
  nickname: string;
  avatar?: string;
  fans_count: number;
}

export interface StatsInfo {
  likes: number;
  comments: number;
  shares: number;
  collects: number;
}

// ── 主数据模型 ────────────────────────────────────────────────────────────────

export interface Note {
  id?: string;
  note_id: string;
  title: string;
  content: string;
  type: NoteType;
  author: AuthorInfo;
  tags: string[];
  stats: StatsInfo;
  published_at: string;
  collected_at: string;
  sentiment?: SentimentResult;
  keywords: string[];
  category?: string;
}

export interface TrendDataPoint {
  timestamp: string;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total_notes: number;
  total_comments: number;
  avg_sentiment_score: number;
  hot_keywords: string[];
}

export interface CompetitorData {
  name: string;
  note_count: number;
  avg_sentiment_score: number;
  positive_rate: number;
  negative_rate: number;
  total_mentions: number;
}

// ── API 响应 ──────────────────────────────────────────────────────────────────

export interface NotesSummary {
  total_notes: number;
  today_notes: number;
  sentiment_distribution: Partial<Record<SentimentLabel, number>>;
}

export interface SentimentStats {
  notes: Partial<Record<SentimentLabel, { count: number; avg_score: number }>>;
  comments: Partial<Record<SentimentLabel, { count: number; avg_score: number }>>;
}

export interface CommentAuthor {
  user_id: string;
  nickname: string;
  avatar?: string;
  fans_count: number;
}

export interface Comment {
  comment_id: string;
  note_id: string;
  content: string;
  author: CommentAuthor;
  likes: number;
  created_at: string;
  sentiment?: SentimentResult;
}

export interface HotTopic {
  note_id: string;
  title: string;
  tags: string[];
  likes: number;
  comments: number;
  sentiment?: SentimentResult | null;
}

// ── WebSocket 消息 ────────────────────────────────────────────────────────────

export type WsMessageType = "new_note" | "sentiment_update" | "alert" | "heartbeat";

export interface WsMessage {
  type: WsMessageType;
  data?: Note | { note_id: string; sentiment: SentimentResult } | { message: string };
  timestamp?: string;
}

// ── 配置 ──────────────────────────────────────────────────────────────────────

export interface KeywordConfig {
  brand: string[];
  competitor: string[];
  industry: string[];
  all: string[];
}

export type SentimentFilter = "all" | "positive" | "negative" | "neutral";

export * from "./intel";
