import type { RecurringSeries } from "@/types/recurring";
import { apiGet } from "@/lib/api/client";

export function getRecurringSeries(accountId?: number): Promise<RecurringSeries[]> {
  const query =
    accountId !== undefined ? `?account_id=${encodeURIComponent(accountId)}` : "";
  return apiGet<RecurringSeries[]>(`/analytics/recurring${query}`);
}
