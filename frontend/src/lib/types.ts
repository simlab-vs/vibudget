/**
 * Mirrors the pydantic schemas in backend/vibudget/schemas.
 *
 * Amounts are signed integer milliunits (1 unit = 1000 milliunits):
 * outflows negative, inflows positive.
 */

export const MILLIUNITS_PER_UNIT = 1000;

export type UUID = string;
/** ISO-8601 calendar date, e.g. "2026-08-26". */
export type IsoDate = string;
/** ISO-8601 timestamp with offset. */
export type IsoDateTime = string;

export type AccountType = "cash" | "credit";
export type ClearedStatus = "uncleared" | "cleared" | "reconciled";

export interface Account {
  id: UUID;
  name: string;
  type: AccountType;
  on_budget: boolean;
  closed: boolean;
  note: string | null;
  balance: number;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface Category {
  id: UUID;
  parent_id: UUID | null;
  name: string;
  hidden: boolean;
  note: string | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface CategoryGroup extends Category {
  children: Category[];
}

export interface Payee {
  id: UUID;
  name: string;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface Split {
  id: UUID;
  category_id: UUID;
  amount: number;
  memo: string | null;
}

export interface Transaction {
  id: UUID;
  account_id: UUID;
  payee_id: UUID | null;
  date: IsoDate;
  amount: number;
  memo: string | null;
  cleared: ClearedStatus;
  splits: Split[];
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export function formatMilliunits(amount: number, currency = "USD", locale = "en-US"): string {
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(
    amount / MILLIUNITS_PER_UNIT,
  );
}
