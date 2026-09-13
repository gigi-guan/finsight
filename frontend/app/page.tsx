import Link from "next/link";

import { getAccounts } from "@/lib/api/accounts";
import { getAnalyticsSummary } from "@/lib/api/analytics";
import { ApiError } from "@/lib/api/client";
import { amountTone, formatSignedUsd, formatUsd } from "@/lib/format";
import type { Account } from "@/types/account";
import type { AnalyticsSummary } from "@/types/analytics";

import styles from "./page.module.css";

export const metadata = {
  title: "Dashboard · FinSight",
  description: "Personal financial intelligence dashboard",
};

function currentMonthLabel(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${now.getFullYear()}-${month}`;
}

function monthOptions(selected: string): string[] {
  const options: string[] = [];
  const [yearStr, monthStr] = selected.split("-");
  let year = Number(yearStr);
  let month = Number(monthStr);

  // Build 12 months ending at the selected/current month.
  for (let i = 0; i < 12; i += 1) {
    options.push(`${year}-${String(month).padStart(2, "0")}`);
    month -= 1;
    if (month === 0) {
      month = 12;
      year -= 1;
    }
  }
  return options;
}

function barWidthPercent(amount: string, maxAmount: string): string {
  const value = Number(amount);
  const max = Number(maxAmount);
  if (!max || Number.isNaN(value) || Number.isNaN(max)) {
    return "0%";
  }
  return `${Math.max(2, Math.round((value / max) * 100))}%`;
}

type HomeProps = {
  searchParams: Promise<{ month?: string; account_id?: string }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  const month = params.month?.trim() || currentMonthLabel();
  const accountIdRaw = params.account_id?.trim();
  const accountId =
    accountIdRaw && /^\d+$/.test(accountIdRaw) ? Number(accountIdRaw) : undefined;

  let accounts: Account[] = [];
  let summary: AnalyticsSummary | null = null;
  let errorMessage: string | null = null;

  try {
    accounts = await getAccounts();
    summary = await getAnalyticsSummary({ month, accountId });
  } catch (error) {
    if (error instanceof ApiError) {
      errorMessage = error.message;
    } else if (error instanceof Error) {
      errorMessage = error.message;
    } else {
      errorMessage = "Unable to load dashboard analytics.";
    }
  }

  const months = monthOptions(month);
  const maxCategory = summary?.spending_by_category[0]?.amount ?? "0";
  const maxMerchant = summary?.top_merchants[0]?.amount ?? "0";
  const netTone = summary ? amountTone(summary.net_cash_flow) : "zero";
  const changeTone = summary
    ? amountTone(summary.previous_month.spending_change_amount)
    : "zero";

  return (
    <main className={styles.page}>
      <p className={styles.nav}>
        <Link href="/accounts">Accounts</Link>
        <Link href="/transactions">Transactions</Link>
        <Link href="/recurring">Recurring</Link>
      </p>

      <header className={styles.header}>
        <p className={styles.brand}>FinSight</p>
        <h1 className={styles.title}>Dashboard</h1>
        <p className={styles.subtitle}>
          Monthly cash-flow summary computed by the API from PostgreSQL.
        </p>
      </header>

      <form className={styles.filters} method="get">
        <div className={styles.field}>
          <label htmlFor="month">Month</label>
          <select id="month" name="month" defaultValue={month}>
            {months.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
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
          Could not load analytics.
          <br />
          {errorMessage}
        </div>
      ) : summary ? (
        <>
          <section className={styles.cards} aria-label="Summary">
            <article className={styles.card}>
              <p className={styles.cardLabel}>Income</p>
              <p className={`${styles.cardValue} ${styles.positive}`}>
                {formatUsd(summary.total_income)}
              </p>
            </article>
            <article className={styles.card}>
              <p className={styles.cardLabel}>Spending</p>
              <p className={`${styles.cardValue} ${styles.negative}`}>
                {formatUsd(summary.total_spending)}
              </p>
            </article>
            <article className={styles.card}>
              <p className={styles.cardLabel}>Net cash flow</p>
              <p
                className={`${styles.cardValue} ${
                  netTone === "positive"
                    ? styles.positive
                    : netTone === "negative"
                      ? styles.negative
                      : ""
                }`}
              >
                {formatSignedUsd(summary.net_cash_flow)}
              </p>
            </article>
            <article className={styles.card}>
              <p className={styles.cardLabel}>Transactions</p>
              <p className={styles.cardValue}>{summary.transaction_count}</p>
            </article>
          </section>

          <section className={styles.panel} aria-labelledby="mom-heading">
            <h2 id="mom-heading" className={styles.panelTitle}>
              Month-over-month spending · {summary.month}
            </h2>
            <p className={styles.momLine}>
              Previous month spending:{" "}
              <strong>
                {formatUsd(summary.previous_month.total_spending)}
              </strong>
            </p>
            <p className={styles.momLine}>
              Change:{" "}
              <strong
                className={
                  changeTone === "positive"
                    ? styles.negative
                    : changeTone === "negative"
                      ? styles.positive
                      : ""
                }
              >
                {formatSignedUsd(summary.previous_month.spending_change_amount)}
              </strong>
              {summary.previous_month.spending_change_percent === null ? (
                <span className={styles.muted}>
                  {" "}
                  (percent change unavailable — previous spending was $0)
                </span>
              ) : (
                <span>
                  {" "}
                  ({summary.previous_month.spending_change_percent}%)
                </span>
              )}
            </p>
          </section>

          <div className={styles.columns}>
            <section
              className={styles.panel}
              aria-labelledby="category-heading"
            >
              <h2 id="category-heading" className={styles.panelTitle}>
                Spending by category
              </h2>
              {summary.spending_by_category.length === 0 ? (
                <p className={styles.empty}>No expenses this month.</p>
              ) : (
                <ul className={styles.barList}>
                  {summary.spending_by_category.map((item) => (
                    <li key={item.category} className={styles.barItem}>
                      <div className={styles.barMeta}>
                        <span>{item.category}</span>
                        <span>
                          {formatUsd(item.amount)} · {item.percent_of_spending}%
                        </span>
                      </div>
                      <div className={styles.barTrack}>
                        <div
                          className={styles.barFill}
                          style={{
                            width: barWidthPercent(item.amount, maxCategory),
                          }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section
              className={styles.panel}
              aria-labelledby="merchant-heading"
            >
              <h2 id="merchant-heading" className={styles.panelTitle}>
                Top merchants
              </h2>
              {summary.top_merchants.length === 0 ? (
                <p className={styles.empty}>No expenses this month.</p>
              ) : (
                <ul className={styles.barList}>
                  {summary.top_merchants.map((item) => (
                    <li key={item.merchant} className={styles.barItem}>
                      <div className={styles.barMeta}>
                        <span>
                          {item.merchant}{" "}
                          <span className={styles.muted}>
                            ({item.transaction_count})
                          </span>
                        </span>
                        <span>{formatUsd(item.amount)}</span>
                      </div>
                      <div className={styles.barTrack}>
                        <div
                          className={styles.barFill}
                          style={{
                            width: barWidthPercent(item.amount, maxMerchant),
                          }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      ) : null}
    </main>
  );
}
