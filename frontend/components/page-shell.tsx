import type { ReactNode } from "react";

import styles from "./page-shell.module.css";

type PageShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export default function PageShell({ title, subtitle, children }: PageShellProps) {
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.subtitle}>{subtitle}</p>
      </header>
      {children}
    </main>
  );
}
