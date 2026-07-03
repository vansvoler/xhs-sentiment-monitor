import type { IntelItem, IntelSourceSyncReport } from "@/types";

export interface UniversityTileData {
  key: string;
  title: string;
  sourceName: string;
  status: IntelSourceSyncReport["status"];
  totalItems: number;
  syncedAt?: string;
  errorMessage?: string | null;
  items: IntelItem[];
}

function getSchoolNameFromItem(item: IntelItem): string {
  return item.school_name ?? item.source_name.replace(/ News$/, "");
}

function getSchoolNameFromReport(report: IntelSourceSyncReport): string {
  return report.school_name ?? report.source_name.replace(/ News$/, "");
}

function getFallbackKey(label: string): string {
  return label.toLowerCase().replaceAll(/\s+/g, "-");
}

export function deriveUniversityTiles(
  items: IntelItem[],
  reports: IntelSourceSyncReport[],
): UniversityTileData[] {
  const itemGroups = new Map<string, IntelItem[]>();

  for (const item of items) {
    const schoolName = getSchoolNameFromItem(item);
    const group = itemGroups.get(schoolName) ?? [];
    group.push(item);
    itemGroups.set(schoolName, group);
  }

  const tiles: UniversityTileData[] = reports.map((report) => {
    const schoolName = getSchoolNameFromReport(report);
    const schoolItems = itemGroups.get(schoolName) ?? [];
    itemGroups.delete(schoolName);

    return {
      key: report.source_id,
      title: schoolName,
      sourceName: report.source_name,
      status: report.status,
      totalItems: report.item_count,
      syncedAt: report.synced_at,
      errorMessage: report.error_message,
      items: schoolItems,
    };
  });

  for (const [schoolName, schoolItems] of itemGroups.entries()) {
    tiles.push({
      key: getFallbackKey(schoolName),
      title: schoolName,
      sourceName: schoolItems[0]?.source_name ?? schoolName,
      status: "success",
      totalItems: schoolItems.length,
      items: schoolItems,
    });
  }

  return tiles;
}
