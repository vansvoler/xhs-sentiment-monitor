import type {
  IntelItem,
  IntelOverviewResponse,
  IntelSourceFeedKey,
  IntelSourceSyncReport,
} from "@/types";

import { NewsNowOverview } from "./newsnow-overview";

export function OverviewPanel({
  data,
  universityItems,
  universitySyncReports,
  onOpenSource,
}: {
  data: IntelOverviewResponse;
  universityItems: IntelItem[];
  universitySyncReports: IntelSourceSyncReport[];
  onOpenSource: (sourceKey: IntelSourceFeedKey) => void;
}) {
  return (
    <NewsNowOverview
      data={data}
      universityItems={universityItems}
      universitySyncReports={universitySyncReports}
      onOpenSource={onOpenSource}
    />
  );
}
