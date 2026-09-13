import type {
  AnalyticsSummary,
  AnalyticsSummaryParams,
} from "@/types/analytics";
import { apiGet } from "@/lib/api/client";

export function getAnalyticsSummary(
  params: AnalyticsSummaryParams = {},
): Promise<AnalyticsSummary> {
  const search = new URLSearchParams();
  if (params.month) {
    search.set("month", params.month);
  }
  if (params.accountId !== undefined) {
    search.set("account_id", String(params.accountId));
  }
  const query = search.toString();
  const path = query ? `/analytics/summary?${query}` : "/analytics/summary";
  return apiGet<AnalyticsSummary>(path);
}
