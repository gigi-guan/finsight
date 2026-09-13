/** Analytics summary from GET /analytics/summary. Money fields are decimal strings. */
export type PreviousMonthComparison = {
  total_spending: string;
  spending_change_amount: string;
  spending_change_percent: string | null;
};

export type CategorySpending = {
  category: string;
  amount: string;
  percent_of_spending: string;
};

export type MerchantSpending = {
  merchant: string;
  amount: string;
  transaction_count: number;
};

export type AnalyticsSummary = {
  month: string;
  total_income: string;
  total_spending: string;
  net_cash_flow: string;
  transaction_count: number;
  previous_month: PreviousMonthComparison;
  spending_by_category: CategorySpending[];
  top_merchants: MerchantSpending[];
};

export type AnalyticsSummaryParams = {
  month?: string;
  accountId?: number;
};
