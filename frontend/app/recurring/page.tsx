import Link from "next/link";

import { getAccounts } from "@/lib/api/accounts";
import { getRecurringSeries } from "@/lib/api/recurring";
import { ApiError } from "@/lib/api/client";
import { amountTone, formatSignedUsd, formatUsd } from "@/lib/format";
import type { Account } from "@/types/account";
import type { RecurringSeries } from "@/types/recurring";

import styles from "./recurring.module.css";

export const metadata = {
  title: "Recurring · FinSight",
  description: "Likely recurring payments and income",
};

function variabilityLabel(value: RecurringSeries["amount_variability"]): string {
  if (value === "low") {
    return "Fixed";
  }
  if (value === "medium") {
    return "Somewhat variable";
  }
  return "Variable";
}

type RecurringPageProps = {
  searchParams: Promise<{ account_id?: string }>;
};

export default async function RecurringPage({ searchParams }: RecurringPageProps) {
  const params = await searchParams;
  const accountIdRaw = params.account_id?.trim();
  const accountId =
    accountIdRaw && /^\d+$/.test(accountIdRaw) ? Number(accountIdRaw) : undefined;

  let accounts: Account[] = [];
  let series: RecurringSeries[] = [];
  let errorMessage: string | null = null;

  try {
    [accounts, series] = await Promise.all([
      getAccounts(),
      getRecurringSeries(accountId),
    ]);
  } catch (error) {
    if (error instanceof ApiError) {
      errorMessage = error.message;
    } else if (error instanceof Error) {
      errorMessage = error.message;
    } else {
      errorMessage = "Unable to load recurring series.";
    }
  }

  const accountName = new Map(accounts.map((a) => [a.id, a.name]));
  const expenses = series.filter((s) => Number(s.average_amount) < 0);
  const income = series.filter((s) => Number(s.average_amount) > 0);

  return (
    <main className={styles.page}>
      <p className={styles.nav}>
        <Link href="/">Dashboard</Link>
        <Link href="/accounts">Accounts</Link>
        <Link href="/transactions">Transactions</Link>
      </p>

      <header className={styles.header}>
        <p className={styles.brand}>FinSight</p>
        <h1 className={styles.title}>Recurring</h1>
        <p className={styles.subtitle}>
          Deterministic detection from payment history. Confidence is a heuristic
          score, not an ML probability.
        </p>
      </header>

      <form className={styles.filters} method="get">
        <div className={styles.field}>
          <label htmlFor="account_id">Account</label>
          <select
            id="account_id"
            name="account_id"
            defaultValue={accountId ? String(accountId) : ""}
          >
            <option value="">All accounts</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </select>
        </div>
        <button className={styles.apply} type="submit">
          Apply
        </button>
      </form>

      {errorMessage ? (
        <div className={styles.error} role="alert">
          {errorMessage}
        </div>
      ) : series.length === 0 ? (
        <p className={styles.status}>
          No recurring series detected yet. Recurring detection needs at least
          three regularly spaced transactions per merchant.
        </p>
      ) : (
        <>
          <SeriesSection
            title="Recurring expenses"
            items={expenses}
            accountName={accountName}
          />
          <SeriesSection
            title="Recurring income"
            items={income}
            accountName={accountName}
          />
        </>
      )}
    </main>
  );
}

function SeriesSection({
  title,
  items,
  accountName,
}: {
  title: string;
  items: RecurringSeries[];
  accountName: Map<number, string>;
}) {
  if (items.length === 0) {
    return null;
  }
  return (
    <section className={styles.panel} aria-label={title}>
      <h2 className={styles.panelTitle}>{title}</h2>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Merchant</th>
              <th scope="col">Account</th>
              <th scope="col">Frequency</th>
              <th scope="col">Typical amount</th>
              <th scope="col">Amount pattern</th>
              <th scope="col">Last</th>
              <th scope="col">Expected next</th>
              <th scope="col">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const tone = amountTone(item.average_amount);
              const amountClass =
                tone === "positive"
                  ? `${styles.amount} ${styles.positive}`
                  : tone === "negative"
                    ? `${styles.amount} ${styles.negative}`
                    : styles.amount;
              return (
                <tr key={`${item.account_id}-${item.normalized_merchant}`}>
                  <td>
                    <div className={styles.merchant}>{item.merchant}</div>
                    <div className={styles.meta}>{item.category}</div>
                  </td>
                  <td>{accountName.get(item.account_id) ?? item.account_id}</td>
                  <td>{item.frequency}</td>
                  <td className={amountClass}>
                    {tone === "zero"
                      ? formatUsd(item.average_amount)
                      : formatSignedUsd(item.average_amount)}
                  </td>
                  <td>{variabilityLabel(item.amount_variability)}</td>
                  <td>{item.last_date}</td>
                  <td>{item.expected_next_date}</td>
                  <td>{item.confidence}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
