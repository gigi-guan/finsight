"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { importTransactionsCsv } from "@/lib/api/transactions";
import { getErrorMessage } from "@/lib/errors";
import type { Account } from "@/types/account";
import type { TransactionImportResult } from "@/types/transaction";

import styles from "./import-csv-form.module.css";

type ImportCsvFormProps = {
  accounts: Account[];
};

export default function ImportCsvForm({ accounts }: ImportCsvFormProps) {
  const router = useRouter();
  const [accountId, setAccountId] = useState(
    accounts[0] ? String(accounts[0].id) : "",
  );
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<TransactionImportResult | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setApiError(null);
    setResult(null);
    setFieldError(null);

    if (!accountId) {
      setFieldError("Select an account.");
      return;
    }
    if (!file) {
      setFieldError("Choose a CSV file.");
      return;
    }

    setIsUploading(true);
    try {
      const summary = await importTransactionsCsv(Number(accountId), file);
      setResult(summary);
      setFile(null);
      if (summary.imported > 0) {
        router.refresh();
      }
    } catch (error) {
      setApiError(getErrorMessage(error, "Unable to import CSV."));
    } finally {
      setIsUploading(false);
    }
  }

  if (accounts.length === 0) {
    return (
      <section className={styles.section}>
        <h2 className={styles.heading}>Import CSV</h2>
        <p className={styles.hint}>
          Create an account first before importing transactions.
        </p>
      </section>
    );
  }

  return (
    <section className={styles.section} aria-labelledby="import-csv-heading">
      <h2 id="import-csv-heading" className={styles.heading}>
        Import CSV
      </h2>
      <p className={styles.hint}>
        Required columns: <code>date</code>, <code>merchant</code>,{" "}
        <code>amount</code>. Optional: <code>description</code>,{" "}
        <code>category</code>. Dates must be <code>YYYY-MM-DD</code>.{" "}
        <a href="/transaction-import-template.csv" download>
          Download template
        </a>
        .
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label htmlFor="import-account">Account</label>
          <select
            id="import-account"
            value={accountId}
            onChange={(event) => setAccountId(event.target.value)}
            disabled={isUploading}
          >
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name} ({account.institution})
              </option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label htmlFor="import-file">CSV file</label>
          <input
            id="import-file"
            key={result ? `file-${result.imported}-${result.total_rows}` : "file"}
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            disabled={isUploading}
          />
        </div>

        {fieldError ? (
          <p className={styles.fieldError} role="alert">
            {fieldError}
          </p>
        ) : null}

        {apiError ? (
          <p className={styles.apiError} role="alert">
            {apiError}
          </p>
        ) : null}

        {result ? (
          <div className={styles.summary} role="status">
            <p>
              Imported <strong>{result.imported}</strong> of{" "}
              <strong>{result.total_rows}</strong> rows. Rejected{" "}
              <strong>{result.rejected}</strong>, duplicates{" "}
              <strong>{result.duplicates}</strong>.
            </p>
            {result.errors.length > 0 ? (
              <ul className={styles.errorList}>
                {result.errors.map((err) => (
                  <li key={`${err.row}-${err.field}-${err.message}`}>
                    Row {err.row}
                    {err.field ? ` (${err.field})` : ""}: {err.message}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        <button className={styles.submit} type="submit" disabled={isUploading}>
          {isUploading ? "Uploading…" : "Import CSV"}
        </button>
      </form>
    </section>
  );
}
