import PageShell from "@/components/page-shell";
import { getAccounts } from "@/lib/api/accounts";
import { getErrorMessage } from "@/lib/errors";
import { formatUsd } from "@/lib/format";
import type { Account } from "@/types/account";

import CreateAccountForm from "./create-account-form";
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
    errorMessage = getErrorMessage(error, "Unable to load accounts.");
  }

  return (
    <PageShell
      title="Accounts"
      subtitle="Create an account and record a snapshot balance (not a live ledger)."
    >
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
                <th scope="col">Snapshot balance</th>
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
    </PageShell>
  );
}
