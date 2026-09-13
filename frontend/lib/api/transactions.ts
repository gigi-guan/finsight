import type {
  Transaction,
  TransactionCreate,
  TransactionImportResult,
} from "@/types/transaction";
import { apiGet, apiPatch, apiPost, apiPostFormData } from "@/lib/api/client";

export function getTransactions(accountId?: number): Promise<Transaction[]> {
  const query =
    accountId !== undefined ? `?account_id=${encodeURIComponent(accountId)}` : "";
  return apiGet<Transaction[]>(`/transactions${query}`);
}

export function createTransaction(
  payload: TransactionCreate,
): Promise<Transaction> {
  return apiPost<Transaction, TransactionCreate>("/transactions", payload);
}

export function updateTransactionCategory(
  transactionId: number,
  category: string,
): Promise<Transaction> {
  return apiPatch<Transaction, { category: string }>(
    `/transactions/${transactionId}/category`,
    { category },
  );
}

export function importTransactionsCsv(
  accountId: number,
  file: File,
): Promise<TransactionImportResult> {
  const formData = new FormData();
  formData.append("account_id", String(accountId));
  formData.append("file", file);
  return apiPostFormData<TransactionImportResult>(
    "/transactions/import",
    formData,
  );
}
