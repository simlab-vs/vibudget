import type { Frequency, IsoDate } from "@/lib/types";

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

function ordinal(day: number): string {
  if (day % 100 >= 11 && day % 100 <= 13) return `${day}th`;
  const suffixes: Record<number, string> = { 1: "st", 2: "nd", 3: "rd" };
  return `${day}${suffixes[day % 10] ?? "th"}`;
}

/**
 * A schedule's recurrence as one readable phrase: "daily", "every 2 weeks on
 * Friday", "monthly on the 15th". The scheduled screen and the dashboard both
 * use this, so the wording never diverges between them.
 */
export function describe(
  schedule: { frequency: Frequency; interval: number; anchor_date: IsoDate },
  locale = "en-US",
): string {
  const anchor = new Date(`${schedule.anchor_date}T00:00:00`);
  const every = schedule.interval;
  switch (schedule.frequency) {
    case "daily":
      return every === 1 ? "daily" : `every ${every} days`;
    case "weekly": {
      const weekday = anchor.toLocaleDateString(locale, { weekday: "long" });
      return every === 1 ? `weekly on ${weekday}` : `every ${every} weeks on ${weekday}`;
    }
    case "monthly": {
      const day = ordinal(anchor.getDate());
      return every === 1 ? `monthly on the ${day}` : `every ${every} months on the ${day}`;
    }
    case "yearly": {
      const day = anchor.toLocaleDateString(locale, { month: "short", day: "numeric" });
      return every === 1 ? `yearly on ${day}` : `every ${every} years on ${day}`;
    }
  }
}

/** The Monday of the week holding `date`, for grouping upcoming occurrences. */
export function weekStart(date: IsoDate): IsoDate {
  const day = new Date(`${date}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
  return day.toISOString().slice(0, 10);
}
