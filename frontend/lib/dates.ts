/** Local calendar YYYY-MM-DD (avoids UTC shift from toISOString). */
export function todayIsoDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/** Local calendar YYYY-MM. */
export function currentMonthLabel(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${now.getFullYear()}-${month}`;
}

function shiftMonth(
  year: number,
  month: number,
  delta: number,
): { year: number; month: number } {
  const index = year * 12 + (month - 1) + delta;
  return {
    year: Math.floor(index / 12),
    month: (index % 12) + 1,
  };
}

/**
 * Month selector options: the last 12 months ending at *current* local month,
 * always including `selected` so choosing a past month does not remove the
 * path back to the present.
 */
export function monthOptions(selected: string, current: string = currentMonthLabel()): string[] {
  const [yearStr, monthStr] = current.split("-");
  let year = Number(yearStr);
  let month = Number(monthStr);
  const options = new Set<string>();

  for (let i = 0; i < 12; i += 1) {
    options.add(`${year}-${String(month).padStart(2, "0")}`);
    const prev = shiftMonth(year, month, -1);
    year = prev.year;
    month = prev.month;
  }
  if (/^\d{4}-\d{2}$/.test(selected)) {
    options.add(selected);
  }
  return Array.from(options).sort().reverse();
}
