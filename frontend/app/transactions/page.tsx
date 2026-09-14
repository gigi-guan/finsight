import Link from "next/link";

import PageShell from "@/components/page-shell";
import { getAccounts } from "@/lib/api/accounts";
import { getTransactions } from "@/lib/api/transactions";
import { getErrorMessage } from "@/lib/errors";
import { amountTone, formatSignedUsd } from "@/lib/format";
import type { Account } from "@/types/account";
import type { Transaction } from "@/types/transaction";

import CategoryEditor from "./category-editor";
import CreateTransactionForm from "./create-transaction-form";
import ImportCsvForm from "./import-csv-form";
import styles from "./transactions.module.css";

export const metadata = {
  title: "Transactions · FinSight",
  description: "Your financial transactions",
};

type ReviewFilter = "all" | "uncategorized" | "user" | "csv";

function parseReviewFilter(raw: string | undefined): ReviewFilter {
  if (raw === "uncategorized" || raw === "user" || raw === "csv") {
    return raw;
  }
  return "all";
}

function matchesReviewFilter(tx: Transaction, filter: ReviewFilter): boolean {
  if (filter === "all") {
    return true;
  }
  if (filter === "uncategorized") {
    return tx.category === "uncategorized";
  }
  return tx.category_source === filter;
}

type TransactionsPageProps = {
  searchParams: Promise<{ review?: string }>;
};

export default async function TransactionsPage({
  searchParams,
}: TransactionsPageProps) {
  const params = await searchParams;
  const reviewFilter = parseReviewFilter(params.review);

  let accounts: Account[] = [];
  let transactions: Transaction[] = [];
  let errorMessage: string | null = null;

  try {
    [accounts, transactions] = await Promise.all([
      getAccounts(),
      getTransactions(),
    ]);
  } catch (error) {
    errorMessage = getErrorMessage(error, "Unable to load transactions.");
  }

  const visible = transactions.filter((tx) =>
    matchesReviewFilter(tx, reviewFilter),
  );
  const uncategorizedCount = transactions.filter(
    (tx) => tx.category === "uncategorized",
  ).length;

  const filters: { id: ReviewFilter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "uncategorized", label: `Uncategorized (${uncategorizedCount})` },
    { id: "user", label: "User-labeled" },
    { id: "csv", label: "CSV-labeled" },
  ];

  return (
    <PageShell
      title="Transactions"
      subtitle="Review and correct categories — user edits become trusted training labels."
    >
      <CreateTransactionForm accounts={accounts} />
      <ImportCsvForm accounts={accounts} />

      <nav className={styles.reviewFilters} aria-label="Category review filters">
        {filters.map((filter) => {
          const href =
            filter.id === "all"
              ? "/transactions"
              : `/transactions?review=${filter.id}`;
          const active = reviewFilter === filter.id;
          return (
            <Link
              key={filter.id}
              href={href}
              className={active ? styles.reviewFilterActive : styles.reviewFilter}
            >
              {filter.label}
            </Link>
          );
        })}
      </nav>

      {errorMessage ? (
        <div className={styles.error} role="alert">
          Could not load transactions. Is the API running?
          <br />
          {errorMessage}
        </div>
      ) : visible.length === 0 ? (
        <p className={styles.status}>
          {transactions.length === 0
            ? "No transactions yet."
            : "No transactions match this review filter."}
        </p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Merchant</th>
                <th scope="col">Description</th>
                <th scope="col">Category</th>
                <th scope="col">Account</th>
                <th scope="col">Amount</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((tx) => {
                const tone = amountTone(tx.amount);
                const amountClass =
                  tone === "positive"
                    ? `${styles.amount} ${styles.amountPositive}`
                    : tone === "negative"
                      ? `${styles.amount} ${styles.amountNegative}`
                      : styles.amount;
                const rowClass =
                  tx.category === "uncategorized" ? styles.needsReview : undefined;

                return (
                  <tr key={tx.id} className={rowClass}>
                    <td>{tx.date}</td>
                    <td className={styles.merchant}>{tx.merchant}</td>
                    <td className={styles.description}>{tx.description}</td>
                    <td>
                      <CategoryEditor
                        transactionId={tx.id}
                        category={tx.category}
                        categorySource={tx.category_source}
                      />
                    </td>
                    <td>{tx.account_name}</td>
                    <td className={amountClass}>{formatSignedUsd(tx.amount)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </PageShell>
  );
}
