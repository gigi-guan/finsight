/**
 * Transaction as returned by GET /transactions (includes account_name).
 * amount is a string because JSON serializes Decimal that way.
 */
export type CategorySource = "user" | "csv" | "rules" | "model" | "unknown";

export type Transaction = {
  id: number;
  account_id: number;
  account_name: string;
  date: string; // ISO date YYYY-MM-DD
  merchant: string;
  description: string;
  amount: string;
  category: string;
  category_source: CategorySource;
  category_confidence: string | null;
  created_at: string;
};

/** Payload for POST /transactions. */
export type TransactionCreate = {
  account_id: number;
  date: string; // YYYY-MM-DD
  merchant: string;
  description: string;
  /** Signed decimal string: income positive, expense negative. */
  amount: string;
  /** Optional; blank becomes uncategorized on the server. */
  category?: string;
};

export type TransactionImportError = {
  row: number;
  field: string | null;
  message: string;
};

export type TransactionImportResult = {
  total_rows: number;
  imported: number;
  rejected: number;
  duplicates: number;
  errors: TransactionImportError[];
};

/** Mirrors backend canonical taxonomy (for form selects). */
export const TRANSACTION_CATEGORIES = [
  "income",
  "housing",
  "groceries",
  "dining",
  "transportation",
  "travel",
  "shopping",
  "entertainment",
  "utilities",
  "healthcare",
  "subscriptions",
  "other",
  "uncategorized",
] as const;

export type TransactionCategory = (typeof TRANSACTION_CATEGORIES)[number];
