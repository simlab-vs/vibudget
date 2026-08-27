import type { IsoDate } from "@/lib/types";

/** Today in the viewer's own timezone, as the API's calendar dates are naive. */
export function today(): IsoDate {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

export function currentMonth(): string {
  return today().slice(0, 7);
}

/** The inclusive date bounds of a "YYYY-MM" month, for the since/until filters. */
export function monthBounds(month: string): { since: IsoDate; until: IsoDate } {
  const [year, index] = month.split("-").map(Number);
  const lastDay = new Date(Date.UTC(year, index, 0)).getUTCDate();
  return { since: `${month}-01`, until: `${month}-${String(lastDay).padStart(2, "0")}` };
}

export function formatDate(date: IsoDate, locale = "en-US"): string {
  return new Date(`${date}T00:00:00`).toLocaleDateString(locale, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatMonth(month: string, locale = "en-US"): string {
  return new Date(`${month}-01T00:00:00`).toLocaleDateString(locale, {
    month: "long",
    year: "numeric",
  });
}

/** Colour class for a signed amount; zero stays neutral. */
export function amountTone(amount: number): string {
  if (amount === 0) return "";
  return amount < 0 ? "negative" : "positive";
}
