// KOL 挖掘域

/** rejected 是人工的最后一道闸：从默认视图隐藏，可在「已排除」tab 恢复 */
export type KolStatus = "candidate" | "shortlisted" | "rejected";

/** 账号身份：按昵称含机构名判定，判不出一律 individual */
export type AccountType = "own_matrix" | "competitor_matrix" | "individual";

/** 命中词里最靠近品牌的一类 */
export type TopCategory = "brand" | "competitor" | "industry";

export interface KolCandidate {
  user_id: string;
  nickname: string;
  avatar?: string | null;
  note_count: number;
  keywords_hit: string[];
  top_category: TopCategory;
  avg_engagement: number;
  positive_rate: number;
  avg_sentiment_score: number;
  last_post_at?: string | null;
  account_type: AccountType;
  account_type_manual: boolean;
  fit_score: number;
  score_breakdown: { relevance?: number; engagement?: number };
  fans_count?: number | null;
  verified?: boolean | null;
  bio?: string | null;
  ip_location?: string | null;
  enriched_at?: string | null;
  status: KolStatus;
  remark?: string | null;
}

/** 候选名下命中监控词的一篇笔记——分数的原始依据 */
export interface KolNote {
  note_id: string;
  xsec_token?: string | null;
  title: string;
  search_keyword: string;
  published_at?: string | null;
  likes: number;
  comments: number;
  collects: number;
  sentiment?: string | null;
}
