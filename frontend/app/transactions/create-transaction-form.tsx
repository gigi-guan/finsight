"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { createTransaction } from "@/lib/api/transactions";
import { ApiError } from "@/lib/api/client";
import type { Account } from "@/types/account";
import {
  TRANSACTION_CATEGORIES,
  type TransactionCreate,
} from "@/types/transaction";

import styles from "./create-transaction-form.module.css";

type FormFields = {
  account_id: string;
  date: string;
  merchant: string;
  description: string;
  amount: string;
  category: string;
};

type FieldErrors = Partial<Record<keyof FormFields, string>>;

/** Signed decimal: optional minus, up to 12 digits, optional .xx */
const DECIMAL_PATTERN = /^-?\d{1,12}(\.\d{1,2})?$/;

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function initialFields(accounts: Account[]): FormFields {
  return {
    account_id: accounts[0] ? String(accounts[0].id) : "",
    date: todayIsoDate(),
    merchant: "",
    description: "",
    amount: "",
    category: "",
  };
}

function validate(fields: FormFields): FieldErrors {
  const errors: FieldErrors = {};

  if (!fields.account_id) {
    errors.account_id = "Select an account.";
  }
  if (!fields.date) {
    errors.date = "Date is required.";
  }
  if (!fields.merchant.trim()) {
    errors.merchant = "Merchant is required.";
  }
  if (!fields.description.trim()) {
    errors.description = "Description is required.";
  }
  const amount = fields.amount.trim();
  if (!amount) {
    errors.amount = "Amount is required.";
  } else if (!DECIMAL_PATTERN.test(amount)) {
    errors.amount =
      "Enter a signed decimal (e.g. -45.20 for expense, 3000 for income).";
  }

  return errors;
}

type CreateTransactionFormProps = {
  accounts: Account[];
};

export default function CreateTransactionForm({
  accounts,
}: CreateTransactionFormProps) {
  const router = useRouter();
  const [fields, setFields] = useState<FormFields>(() => initialFields(accounts));
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateField<K extends keyof FormFields>(key: K, value: FormFields[K]) {
    setFields((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setApiError(null);
    setSuccessMessage(null);

    const errors = validate(fields);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    const payload: TransactionCreate = {
      account_id: Number(fields.account_id),
      date: fields.date,
      merchant: fields.merchant.trim(),
      description: fields.description.trim(),
      amount: fields.amount.trim(),
      category: fields.category.trim(),
    };

    setIsSubmitting(true);
    try {
      const created = await createTransaction(payload);
      setFields(initialFields(accounts));
      setFieldErrors({});
      setSuccessMessage(`Added “${created.merchant}”.`);
      router.refresh();
    } catch (error) {
      if (error instanceof ApiError) {
        setApiError(error.message);
      } else if (error instanceof Error) {
        setApiError(error.message);
      } else {
        setApiError("Unable to create transaction.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (accounts.length === 0) {
    return (
      <section className={styles.section}>
        <h2 className={styles.heading}>Add transaction</h2>
        <p className={styles.hint}>
          Create an account first before adding transactions.
        </p>
      </section>
    );
  }

  return (
    <section
      className={styles.section}
      aria-labelledby="create-transaction-heading"
    >
      <h2 id="create-transaction-heading" className={styles.heading}>
        Add transaction
      </h2>
      <p className={styles.hint}>
        Use a negative amount for expenses (e.g. -45.20) and a positive amount
        for income (e.g. 3000.00).
      </p>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <div className={styles.field}>
          <label htmlFor="tx-account">Account</label>
          <select
            id="tx-account"
            name="account_id"
            value={fields.account_id}
            onChange={(event) => updateField("account_id", event.target.value)}
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.account_id)}
          >
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name} ({account.institution})
              </option>
            ))}
          </select>
          {fieldErrors.account_id ? (
            <p className={styles.fieldError} role="alert">
              {fieldErrors.account_id}
            </p>
          ) : null}
        </div>

        <div className={styles.field}>
          <label htmlFor="tx-date">Date</label>
          <input
            id="tx-date"
            name="date"
            type="date"
            value={fields.date}
            onChange={(event) => updateField("date", event.target.value)}
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.date)}
          />
          {fieldErrors.date ? (
            <p className={styles.fieldError} role="alert">
              {fieldErrors.date}
            </p>
          ) : null}
        </div>

        <div className={styles.field}>
          <label htmlFor="tx-merchant">Merchant</label>
          <input
            id="tx-merchant"
            name="merchant"
            type="text"
            value={fields.merchant}
            onChange={(event) => updateField("merchant", event.target.value)}
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.merchant)}
          />
          {fieldErrors.merchant ? (
            <p className={styles.fieldError} role="alert">
              {fieldErrors.merchant}
            </p>
          ) : null}
        </div>

        <div className={styles.field}>
          <label htmlFor="tx-description">Description</label>
          <input
            id="tx-description"
            name="description"
            type="text"
            value={fields.description}
            onChange={(event) => updateField("description", event.target.value)}
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.description)}
          />
          {fieldErrors.description ? (
            <p className={styles.fieldError} role="alert">
              {fieldErrors.description}
            </p>
          ) : null}
        </div>

        <div className={styles.field}>
          <label htmlFor="tx-amount">Amount (USD)</label>
          <input
            id="tx-amount"
            name="amount"
            type="text"
            inputMode="decimal"
            placeholder="-45.20"
            value={fields.amount}
            onChange={(event) => updateField("amount", event.target.value)}
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.amount)}
          />
          {fieldErrors.amount ? (
            <p className={styles.fieldError} role="alert">
              {fieldErrors.amount}
            </p>
          ) : null}
        </div>

        <div className={styles.field}>
          <label htmlFor="tx-category">Category (optional)</label>
          <select
            id="tx-category"
            name="category"
            value={fields.category}
            onChange={(event) => updateField("category", event.target.value)}
            disabled={isSubmitting}
          >
            <option value="">Uncategorized</option>
            {TRANSACTION_CATEGORIES.filter((c) => c !== "uncategorized").map(
              (category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ),
            )}
          </select>
        </div>

        {apiError ? (
          <p className={styles.apiError} role="alert">
            {apiError}
          </p>
        ) : null}

        {successMessage ? (
          <p className={styles.success} role="status">
            {successMessage}
          </p>
        ) : null}

        <button className={styles.submit} type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating…" : "Create transaction"}
        </button>
      </form>
    </section>
  );
}
