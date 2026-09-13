import type { Account, AccountCreate } from "@/types/account";
import { apiGet, apiPost } from "@/lib/api/client";

export function getAccounts(): Promise<Account[]> {
  return apiGet<Account[]>("/accounts");
}

export function createAccount(payload: AccountCreate): Promise<Account> {
  return apiPost<Account, AccountCreate>("/accounts", payload);
}
