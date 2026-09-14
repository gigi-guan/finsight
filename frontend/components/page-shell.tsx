import Link from "next/link";
import type { ReactNode } from "react";

import styles from "./page-shell.module.css";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/accounts", label: "Accounts" },
  { href: "/transactions", label: "Transactions" },
  { href: "/recurring", label: "Recurring" },
] as const;

type PageShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export default function PageShell({ title, subtitle, children }: PageShellProps) {
  return (
    <main className={styles.page}>
      <nav className={styles.nav} aria-label="Primary">
        {NAV_LINKS.map((link, index) => (
          <span key={link.href} className={styles.navItem}>
            {index > 0 ? <span className={styles.sep}>·</span> : null}
            <Link href={link.href}>{link.label}</Link>
          </span>
        ))}
      </nav>

      <header className={styles.header}>
        <p className={styles.brand}>FinSight</p>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.subtitle}>{subtitle}</p>
      </header>

      {children}
    </main>
  );
}
