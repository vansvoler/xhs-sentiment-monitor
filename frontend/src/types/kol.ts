// KOL 挖掘域

export type KolStatus = "candidate" | "shortlisted" | "rejected";

export interface KolCandidate {
  user_id: string;
  nickname: string;
  avatar?: string | null;
  note_count: number;
  keywords_hit: string[];
  avg_engagement: number;
  positive_rate: number;
  avg_sentiment_score: number;
  last_post_at?: string | null;
  is_own: boolean;
  is_competitor: boolean;
  fit_score: number;
  score_breakdown: { relevance?: number; engagement?: number; sentiment?: number };
  fans_count?: number | null;
  verified?: boolean | null;
  bio?: string | null;
  ip_location?: string | null;
  enriched_at?: string | null;
  status: KolStatus;
  remark?: string | null;
}
