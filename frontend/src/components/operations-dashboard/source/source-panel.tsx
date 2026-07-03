import type { IntelSourceResponse } from "@/types";

import { SourceRankedPanel } from "./source-ranked-panel";

export function SourcePanel({ data }: { data: IntelSourceResponse }) {
  return <SourceRankedPanel data={data} />;
}
