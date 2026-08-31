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

export interface AccountCreate {
  name: string;
  type: AccountType;
  on_budget?: boolean;
  note?: string | null;
}

export interface AccountUpdate {
  name?: string;
  type?: AccountType;
  on_budget?: boolean;
  closed?: boolean;
  note?: string | null;
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

export interface CategoryCreate {
  name: string;
  parent_id?: UUID | null;
  note?: string | null;
}

export interface CategoryUpdate {
  name?: string;
  parent_id?: UUID | null;
  hidden?: boolean;
  note?: string | null;
}

export interface Payee {
  id: UUID;
  name: string;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface PayeeCreate {
  name: string;
}

export interface PayeeUpdate {
  name?: string;
}

export interface Split {
  id: UUID;
  category_id: UUID;
  amount: number;
  memo: string | null;
}

export interface SplitCreate {
  category_id: UUID;
  amount: number;
  memo?: string | null;
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
  /** Set when this transaction was written by approving a scheduled occurrence. Read-only. */
  scheduled_occurrence_id: UUID | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface TransactionCreate {
  account_id: UUID;
  date: IsoDate;
  amount: number;
  payee_id?: UUID | null;
  memo?: string | null;
  cleared?: ClearedStatus;
  splits: SplitCreate[];
}

/** Sending `splits` requires sending `amount` too, so the two can be checked. */
export interface TransactionUpdate {
  account_id?: UUID;
  date?: IsoDate;
  amount?: number;
  payee_id?: UUID | null;
  memo?: string | null;
  cleared?: ClearedStatus;
  splits?: SplitCreate[];
}

export type TransactionQuery = {
  account_id?: UUID;
  payee_id?: UUID;
  category_id?: UUID;
  since?: IsoDate;
  until?: IsoDate;
  limit?: number;
  offset?: number;
};

export type Frequency = "daily" | "weekly" | "monthly" | "yearly";
export type OccurrenceStatus = "pending" | "approved" | "skipped";

export interface Schedule {
  id: UUID;
  account_id: UUID;
  payee_id: UUID | null;
  amount: number;
  memo: string | null;
  frequency: Frequency;
  interval: number;
  anchor_date: IsoDate;
  next_due: IsoDate;
  ends_on: IsoDate | null;
  paused: boolean;
  splits: Split[];
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export interface ScheduleCreate {
  account_id: UUID;
  amount: number;
  frequency: Frequency;
  anchor_date: IsoDate;
  payee_id?: UUID | null;
  memo?: string | null;
  interval?: number;
  ends_on?: IsoDate | null;
  paused?: boolean;
  splits: SplitCreate[];
}

/** Sending `splits` requires sending `amount` too, so the two can be checked. */
export interface ScheduleUpdate {
  account_id?: UUID;
  payee_id?: UUID | null;
  amount?: number;
  memo?: string | null;
  frequency?: Frequency;
  interval?: number;
  anchor_date?: IsoDate;
  ends_on?: IsoDate | null;
  paused?: boolean;
  splits?: SplitCreate[];
}

/** A split as the occurrence queue denormalises it: no row id of its own. */
export interface OccurrenceSplit {
  category_id: UUID;
  amount: number;
  memo: string | null;
}

export interface ScheduledOccurrence {
  id: UUID;
  schedule_id: UUID;
  due_date: IsoDate;
  status: OccurrenceStatus;
  transaction_id: UUID | null;
  account_id: UUID;
  payee_id: UUID | null;
  amount: number;
  memo: string | null;
  splits: OccurrenceSplit[];
  /** due_date < today, as the server counts today. */
  overdue: boolean;
}

/**
 * Overrides the schedule's template for one occurrence; every field optional.
 * `date` defaults to the due date. Sending `splits` requires sending `amount` too.
 */
export interface OccurrenceApproval {
  date?: IsoDate;
  amount?: number;
  payee_id?: UUID | null;
  memo?: string | null;
  cleared?: ClearedStatus;
  splits?: SplitCreate[];
}

export type OccurrenceQuery = {
  until?: IsoDate;
  status?: OccurrenceStatus;
  schedule_id?: UUID;
};

export interface NetWorth {
  on_budget: number;
  off_budget: number;
  total: number;
}

/** An account as the dashboard reports it: `Account` minus the note. */
export interface DashboardAccount {
  id: UUID;
  name: string;
  type: AccountType;
  on_budget: boolean;
  closed: boolean;
  balance: number;
}

export interface CashflowMonth {
  /** "YYYY-MM". */
  month: string;
  inflow: number;
  outflow: number;
  net: number;
}

/** Spending amounts stay signed and negative; render the magnitude. */
export interface SpendingCategory {
  id: UUID;
  name: string;
  amount: number;
  previous_amount: number;
}

export interface SpendingGroup {
  group_id: UUID;
  group_name: string;
  amount: number;
  previous_amount: number;
  categories: SpendingCategory[];
}

export interface UpcomingSummary {
  due_count: number;
  due_total: number;
  next_7_days: ScheduledOccurrence[];
}

export interface Dashboard {
  /** "YYYY-MM". */
  month: string;
  net_worth: NetWorth;
  accounts: DashboardAccount[];
  cashflow: CashflowMonth[];
  spending: SpendingGroup[];
  upcoming: UpcomingSummary;
  uncleared_count: number;
}

export function formatMilliunits(amount: number, currency = "USD", locale = "en-US"): string {
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(
    amount / MILLIUNITS_PER_UNIT,
  );
}

export function toMilliunits(amount: number): number {
  return Math.round(amount * MILLIUNITS_PER_UNIT);
}
