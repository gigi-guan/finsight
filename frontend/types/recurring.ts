export type RecurringFrequency = "weekly" | "biweekly" | "monthly";
export type AmountVariability = "low" | "medium" | "high";

/** Recurring series from GET /analytics/recurring (heuristic, not ML). */
export type RecurringSeries = {
  merchant: string;
  normalized_merchant: string;
  account_id: number;
  category: string;
  frequency: RecurringFrequency;
  transaction_count: number;
  average_amount: string;
  amount_variability: AmountVariability;
  last_date: string;
  expected_next_date: string;
  /** Heuristic 0–1 score — not a calibrated probability. */
  confidence: string;
};
