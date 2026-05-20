import type { IntelSourceResponse } from "@/types";

import { SourceHeader } from "./source-header";
import { SourceList } from "./source-list";

export function SourcePanel({ data }: { data: IntelSourceResponse }) {
  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <SourceList items={data.items} />
    </section>
  );
}
