/**
 * Account as returned by GET /accounts (FastAPI AccountRead).
 * current_balance is a string because JSON serializes Decimal that way.
 */
export type Account = {
  id: number;
  name: string;
  account_type: string;
  institution: string;
  current_balance: string;
  created_at: string;
};

/** Controlled set of account types accepted by the create form. */
export const ACCOUNT_TYPES = [
  "checking",
  "savings",
  "credit",
  "investment",
  "other",
] as const;

export type AccountType = (typeof ACCOUNT_TYPES)[number];

/** Payload for POST /accounts (matches FastAPI AccountCreate). */
export type AccountCreate = {
  name: string;
  account_type: AccountType;
  institution: string;
  /** Decimal string, e.g. "1250.50" — never a JS number for money. */
  current_balance: string;
};
