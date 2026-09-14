"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { createAccount } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import {
  ACCOUNT_TYPES,
  type AccountCreate,
  type AccountType,
} from "@/types/account";

import styles from "./create-account-form.module.css";

type FormFields = {
  name: string;
  institution: string;
  account_type: AccountType | "";
  current_balance: string;
};

type FieldErrors = Partial<Record<keyof FormFields, string>>;

const INITIAL_FIELDS: FormFields = {
  name: "",
  institution: "",
  account_type: "",
  current_balance: "",
};

/** Up to 12 digits before decimal, optional 1–2 digits after. */
const DECIMAL_PATTERN = /^-?\d{1,12}(\.\d{1,2})?$/;

function validate(fields: FormFields): FieldErrors {
  const errors: FieldErrors = {};

  if (!fields.name.trim()) {
    errors.name = "Account name is required.";
  }
  if (!fields.institution.trim()) {
    errors.institution = "Institution is required.";
  }
  if (!fields.account_type) {
    errors.account_type = "Account type is required.";
  }
  const balance = fields.current_balance.trim();
  if (!balance) {
    errors.current_balance = "Snapshot balance is required.";
  } else if (!DECIMAL_PATTERN.test(balance)) {
    errors.current_balance =
      "Enter a valid decimal amount (e.g. 1250.50), max 2 decimal places.";
  }

  return errors;
}

export default function CreateAccountForm() {
  const router = useRouter();
  const [fields, setFields] = useState<FormFields>(INITIAL_FIELDS);
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

    const payload: AccountCreate = {
      name: fields.name.trim(),
      institution: fields.institution.trim(),
      account_type: fields.account_type as AccountType,
      current_balance: fields.current_balance.trim(),
    };

    setIsSubmitting(true);
    try {
      const created = await createAccount(payload);
      setFields(INITIAL_FIELDS);
      setFieldErrors({});
      setSuccessMessage(`Created “${created.name}”.`);
      // Re-run the Server Component so the list includes the new row.
      router.refresh();
    } catch (error) {
      if (error instanceof ApiError) {
        setApiError(error.message);
      } else if (error instanceof Error) {
        setApiError(error.message);
      } else {
        setApiError("Unable to create account.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className={styles.section} aria-labelledby="create-account-heading">
      <h2 id="create-account-heading" className={styles.heading}>
        Add account
      </h2>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <div className={styles.field}>
          <label htmlFor="account-name">Account name</label>
          <input
            id="account-name"
            name="name"
            type="text"
            autoComplete="off"
            value={fields.name}
            onChange={(event) => updateField("name", event.target.value)}
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.name)}
            aria-describedby={fieldErrors.name ? "account-name-error" : undefined}
          />
          {fieldErrors.name ? (
            <p id="account-name-error" className={styles.fieldError} role="alert">
              {fieldErrors.name}
            </p>
          ) : null}
        </div>

        <div className={styles.field}>
          <label htmlFor="account-institution">Institution</label>
          <input
            id="account-institution"
            name="institution"
            type="text"
            autoComplete="organization"
            value={fields.institution}
            onChange={(event) => updateField("institution", event.target.value)}
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.institution)}
            aria-describedby={
              fieldErrors.institution ? "account-institution-error" : undefined
            }
          />
          {fieldErrors.institution ? (
            <p
              id="account-institution-error"
              className={styles.fieldError}
              role="alert"
            >
              {fieldErrors.institution}
            </p>
          ) : null}
        </div>

        <div className={styles.field}>
          <label htmlFor="account-type">Account type</label>
          <select
            id="account-type"
            name="account_type"
            value={fields.account_type}
            onChange={(event) =>
              updateField("account_type", event.target.value as AccountType | "")
            }
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.account_type)}
            aria-describedby={
              fieldErrors.account_type ? "account-type-error" : undefined
            }
          >
            <option value="">Select a type</option>
            {ACCOUNT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
          {fieldErrors.account_type ? (
            <p id="account-type-error" className={styles.fieldError} role="alert">
              {fieldErrors.account_type}
            </p>
          ) : null}
        </div>

        <div className={styles.field}>
          <label htmlFor="account-balance">Snapshot balance (USD)</label>
          <input
            id="account-balance"
            name="current_balance"
            type="text"
            inputMode="decimal"
            placeholder="0.00"
            autoComplete="off"
            value={fields.current_balance}
            onChange={(event) =>
              updateField("current_balance", event.target.value)
            }
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.current_balance)}
            aria-describedby={
              fieldErrors.current_balance ? "account-balance-error" : undefined
            }
          />
          {fieldErrors.current_balance ? (
            <p
              id="account-balance-error"
              className={styles.fieldError}
              role="alert"
            >
              {fieldErrors.current_balance}
            </p>
          ) : null}
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
          {isSubmitting ? "Creating…" : "Create account"}
        </button>
      </form>
    </section>
  );
}
