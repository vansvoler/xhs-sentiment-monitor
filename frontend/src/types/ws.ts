// WebSocket 实时消息

import type { Alert } from "./alert";
import type { Note, SentimentResult } from "./note";

export type WsMessageType = "new_note" | "sentiment_update" | "alert" | "heartbeat";

export interface WsMessage {
  type: WsMessageType;
  data?: Note | { note_id: string; sentiment: SentimentResult } | Alert;
  timestamp?: string;
}
