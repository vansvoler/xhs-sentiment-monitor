import { XhsSentimentDashboard } from "@/components/xhs-sentiment/xhs-sentiment-dashboard";
import { WebSocketProvider } from "@/lib/websocket";

export default function LegacyDashboardPage() {
  return (
    <WebSocketProvider>
      <XhsSentimentDashboard />
    </WebSocketProvider>
  );
}
