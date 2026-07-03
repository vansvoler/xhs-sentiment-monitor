// 舆情预警域

export type AlertType =
  | "negative_note"
  | "negative_comment"
  | "negative_rate"
  | "volume_spike";
export type AlertLevel = "info" | "warning" | "critical";
export type AlertStatus = "open" | "acknowledged";

export interface Alert {
  alert_id: string;
  type: AlertType;
  level: AlertLevel;
  title: string;
  message: string;
  keyword?: string | null;
  note_id?: string | null;
  sentiment_score?: number | null;
  metric: Record<string, number>;
  status: AlertStatus;
  created_at: string;
}
