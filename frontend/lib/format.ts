const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

/** Format a numeric or decimal-string balance as USD (e.g. "$1,250.50"). */
export function formatUsd(value: string | number): string {
  const amount = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(amount)) {
    return "—";
  }
  return usdFormatter.format(amount);
}

/**
 * Format a signed transaction amount.
 * Expenses stay clearly negative (e.g. "-$45.20"); income is "+$3,000.00".
 */
export function formatSignedUsd(value: string | number): string {
  const amount = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(amount)) {
    return "—";
  }
  const formatted = usdFormatter.format(Math.abs(amount));
  if (amount > 0) {
    return `+${formatted}`;
  }
  if (amount < 0) {
    return `-${formatted}`;
  }
  return formatted;
}

export function amountTone(value: string | number): "positive" | "negative" | "zero" {
  const amount = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(amount) || amount === 0) {
    return "zero";
  }
  return amount > 0 ? "positive" : "negative";
}
