import styles from "./transactions.module.css";

export default function TransactionsLoading() {
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.brand}>FinSight</p>
        <h1 className={styles.title}>Transactions</h1>
      </header>
      <p className={styles.status} role="status">
        Loading transactions…
      </p>
    </main>
  );
}
