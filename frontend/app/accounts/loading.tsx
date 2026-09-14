import PageShell from "@/components/page-shell";

import styles from "./accounts.module.css";

export default function AccountsLoading() {
  return (
    <PageShell
      title="Accounts"
      subtitle="Create an account and record a snapshot balance (not a live ledger)."
    >
      <p className={styles.status} role="status">
        Loading accounts…
      </p>
    </PageShell>
  );
}
