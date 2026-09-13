import Link from "next/link";

import { getAccounts } from "@/lib/api/accounts";
import CreateAccountForm from "./create-account-form";
import { ApiError } from "@/lib/api/client";
import { formatUsd } from "@/lib/format";
import type { Account } from "@/types/account";

import styles from "./accounts.module.css";

export const metadata = {
  title: "Accounts · FinSight",
  description: "Your linked financial accounts",
};

export default async function AccountsPage() {
  let accounts: Account[] = [];
  let errorMessage: string | null = null;

  try {
    accounts = await getAccounts();
  } catch (error) {
    if (error instanceof ApiError) {
      errorMessage = error.message;
    } else if (error instanceof Error) {
      errorMessage = error.message;
    } else {
      errorMessage = "Unable to load accounts.";
    }
  }

  return (
    <main className={styles.page}>
      <p className={styles.nav}>
        <Link href="/">Dashboard</Link>
        {" · "}
        <Link href="/transactions">Transactions</Link>
        {" · "}
        <Link href="/recurring">Recurring</Link>
      </p>

      <header className={styles.header}>
        <p className={styles.brand}>FinSight</p>
        <h1 className={styles.title}>Accounts</h1>
        <p className={styles.subtitle}>
          Create an account and see balances from the FinSight API.
        </p>
      </header>

      <CreateAccountForm />

      {errorMessage ? (
        <div className={styles.error} role="alert">
          Could not load accounts. Is the API running at{" "}
          <code>
            {process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"}
          </code>
          ?
          <br />
          {errorMessage}
        </div>
      ) : accounts.length === 0 ? (
        <p className={styles.status}>No accounts yet.</p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Institution</th>
                <th scope="col">Type</th>
                <th scope="col">Balance</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <tr key={account.id}>
                  <td>{account.name}</td>
                  <td>{account.institution}</td>
                  <td className={styles.type}>{account.account_type}</td>
                  <td className={styles.balance}>
                    {formatUsd(account.current_balance)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
