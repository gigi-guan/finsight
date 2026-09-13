import styles from "./accounts.module.css";

export default function AccountsLoading() {
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.brand}>FinSight</p>
        <h1 className={styles.title}>Accounts</h1>
      </header>
      <p className={styles.status} role="status">
        Loading accounts…
      </p>
    </main>
  );
}
