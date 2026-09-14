"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { updateTransactionCategory } from "@/lib/api/transactions";
import { getErrorMessage } from "@/lib/errors";
import {
  TRANSACTION_CATEGORIES,
  type CategorySource,
} from "@/types/transaction";

import styles from "./category-editor.module.css";

type CategoryEditorProps = {
  transactionId: number;
  category: string;
  categorySource: CategorySource;
};

export default function CategoryEditor({
  transactionId,
  category,
  categorySource,
}: CategoryEditorProps) {
  const router = useRouter();
  const [value, setValue] = useState(category);
  const [source, setSource] = useState(categorySource);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleChange(nextCategory: string) {
    if (nextCategory === value || isSaving) {
      return;
    }
    const previous = value;
    setValue(nextCategory);
    setError(null);
    setIsSaving(true);
    try {
      const updated = await updateTransactionCategory(transactionId, nextCategory);
      setValue(updated.category);
      setSource(updated.category_source);
      router.refresh();
    } catch (err) {
      setValue(previous);
      setError(getErrorMessage(err, "Could not update category."));
    } finally {
      setIsSaving(false);
    }
  }

  const uncategorized = value === "uncategorized";

  return (
    <div className={styles.wrap}>
      <div className={styles.row}>
        <select
          className={uncategorized ? styles.selectNeedsReview : styles.select}
          aria-label={`Category for transaction ${transactionId}`}
          value={value}
          disabled={isSaving}
          onChange={(event) => {
            void handleChange(event.target.value);
          }}
        >
          {TRANSACTION_CATEGORIES.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <span
          className={
            uncategorized ? `${styles.source} ${styles.sourceNeedsReview}` : styles.source
          }
          title="Category provenance"
        >
          {source}
        </span>
      </div>
      {isSaving ? <p className={styles.status}>Saving…</p> : null}
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
