import PageShell from "@/components/page-shell";

import styles from "./transactions.module.css";

export default function TransactionsLoading() {
  return (
    <PageShell
      title="Transactions"
      subtitle="Review and correct categories — user edits become trusted training labels."
    >
      <p className={styles.status} role="status">
        Loading transactions…
      </p>
    </PageShell>
  );
}
