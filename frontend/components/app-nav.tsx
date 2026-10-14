"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./app-nav.module.css";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/accounts", label: "Accounts" },
  { href: "/transactions", label: "Transactions" },
  { href: "/recurring", label: "Recurring" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppNav() {
  const pathname = usePathname();

  return (
    <aside className={styles.rail}>
      <div className={styles.brand}>
        <p className={styles.mark}>FinSight</p>
        <p className={styles.tag}>Private ledger</p>
      </div>
      <nav className={styles.nav} aria-label="Primary">
        {LINKS.map((link) => {
          const active = isActive(pathname, link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={active ? styles.active : styles.link}
              aria-current={active ? "page" : undefined}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
      <p className={styles.foot}>Single-user portfolio · Not a bank</p>
    </aside>
  );
}
