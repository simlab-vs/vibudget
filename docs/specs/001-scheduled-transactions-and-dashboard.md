# Spec 001 — Scheduled transactions and dashboard

**Status:** approved for Phase 0 — the open questions below are decided
**Owners:** backend team, frontend team
**Depends on:** the schema in `backend/vibudget/migrations/001_initial.sql`

Two features, specified together because the dashboard's "upcoming" panel reads
what the scheduling feature produces. They can still be built in parallel; see
[Splitting the work](#splitting-the-work).

- [Feature 1 — Scheduled transactions](#feature-1--scheduled-transactions)
- [Feature 2 — Dashboard](#feature-2--dashboard)
- [Splitting the work](#splitting-the-work)
- [Phase 2 — detecting recurrence](#phase-2--detecting-recurrence-not-now)
- [Open questions](#open-questions)

Conventions from [AGENTS.md](../../AGENTS.md) hold throughout: amounts are
signed integer milliunits, outflows negative; the SQL migration is the source of
truth the pydantic schemas mirror; each entity gets `XCreate`, `XUpdate` and `X`.

---

## Feature 1 — Scheduled transactions

### Goal

A user records a rule once — "rent, Checking, €1,200 out, monthly on the 1st" —
and from then on ViBudget presents each due instance for a single click of
**Approve**, which writes a real transaction. Nothing is entered on the user's
behalf without that click.

### Non-goals for this phase

- **Auto-entry.** Every occurrence needs explicit approval. A future
  `auto_approve` column can lift this without changing the API shape.
- **Detecting recurrence from history.** Deliberately deferred; see
  [Phase 2](#phase-2--detecting-recurrence-not-now).
- **A scheduler process.** No cron, no worker, no Celery. Occurrences are
  materialised lazily on read (below), so the Compose stack keeps its three
  services.
- **Editing a split schedule in the browser.** Same limitation the register
  already has for split transactions: the API supports it, the UI does not.

### Data model

New migration: `backend/vibudget/migrations/002_schedules.sql`.

#### `schedule` — the rule

| Column        | Type              | Notes                                                        |
| ------------- | ----------------- | ------------------------------------------------------------ |
| `id`          | uuid pk           | `gen_random_uuid()`                                           |
| `account_id`  | uuid NOT NULL     | → `account` `ON DELETE CASCADE`                               |
| `payee_id`    | uuid NULL         | → `payee` `ON DELETE RESTRICT`                                |
| `amount`      | bigint NOT NULL   | Signed milliunits; the template amount                        |
| `memo`        | text NULL         |                                                               |
| `frequency`   | `schedule_frequency` NOT NULL | enum `daily \| weekly \| monthly \| yearly`       |
| `interval`    | int NOT NULL      | `DEFAULT 1`, `CHECK (interval BETWEEN 1 AND 366)` — every N   |
| `anchor_date` | date NOT NULL     | The first occurrence; the rule's day-of-month / weekday        |
| `next_due`    | date NOT NULL     | Next date not yet materialised into an occurrence              |
| `ends_on`     | date NULL         | Inclusive last date; NULL means open-ended                    |
| `paused`      | boolean NOT NULL  | `DEFAULT false`                                                |
| `created_at`  | timestamptz       | + `touch_updated_at` trigger, as every other table            |
| `updated_at`  | timestamptz       |                                                                |

Constraints: `CHECK (ends_on IS NULL OR ends_on >= anchor_date)`.
Index: `schedule_next_due_idx ON schedule (next_due) WHERE NOT paused`.

`schedule` has **no name column**. A schedule is identified in the UI by its
payee and amount, the way a transaction is. This keeps the uniqueness question
out of the feature entirely — two identical schedules are the user's business.

#### `schedule_split` — the categories the template writes

Mirrors `transaction_split` exactly: `id`, `schedule_id` (→ `schedule`
`ON DELETE CASCADE`), `category_id` (→ `category` `ON DELETE RESTRICT`),
`amount`, `memo`. At least one row per schedule; amounts sum to
`schedule.amount`, enforced in the repository the same way transaction splits
are.

#### `scheduled_occurrence` — one due instance

| Column           | Type                 | Notes                                          |
| ---------------- | -------------------- | ---------------------------------------------- |
| `id`             | uuid pk              |                                                |
| `schedule_id`    | uuid NOT NULL        | → `schedule` `ON DELETE CASCADE`                |
| `due_date`       | date NOT NULL        |                                                |
| `status`         | `occurrence_status` NOT NULL | enum `pending \| approved \| skipped`, default `pending` |
| `transaction_id` | uuid NULL            | → `transaction` `ON DELETE SET NULL`            |
| `created_at`     | timestamptz          | + trigger                                       |
| `updated_at`     | timestamptz          |                                                 |

```sql
CREATE UNIQUE INDEX scheduled_occurrence_slot_key
    ON scheduled_occurrence (schedule_id, due_date);
CREATE INDEX scheduled_occurrence_pending_idx
    ON scheduled_occurrence (due_date) WHERE status = 'pending';
CREATE UNIQUE INDEX scheduled_occurrence_transaction_key
    ON scheduled_occurrence (transaction_id) WHERE transaction_id IS NOT NULL;
```

The first unique index is what makes materialisation idempotent — see below.
The second makes "which occurrence approved this transaction" a well-defined
question for the register badge below, rather than "the first one found".

### Materialisation

There is no background job. `list_occurrences` runs, inside one database
transaction, before it reads:

1. For every schedule where `NOT paused` and `next_due <= horizon`, generate the
   dates from `next_due` up to `min(horizon, ends_on)` using the recurrence rule.
2. `INSERT … ON CONFLICT (schedule_id, due_date) DO NOTHING`.
3. Advance `schedule.next_due` past the last date generated.

`horizon` = `today + VIBUDGET_SCHEDULE_HORIZON_DAYS` (new setting in
`config.py`, default `30`), or the request's `until`, whichever is earlier.
Generation is capped at 500 rows per schedule per call, so a schedule anchored
in 1970 cannot blow up a request.

**This means a GET writes.** That is a deliberate trade for keeping the stack at
three services. It is safe because the unique index makes the insert idempotent
and concurrent callers converge on the same rows. If we later add a worker, it
calls the same repository function and the GET stops needing to.

### Recurrence maths

Lives in a new pure module `backend/vibudget/recurrence.py`, with no database
and no I/O, so it can be unit-tested exhaustively:

```python
def occurrences_from(
    anchor: date, frequency: Frequency, interval: int, start: date, until: date
) -> Iterator[date]: ...
```

The rules, in full:

| Frequency | Step                    | Edge case                                                   |
| --------- | ----------------------- | ----------------------------------------------------------- |
| `daily`   | `+ interval` days       | none                                                         |
| `weekly`  | `+ interval` weeks      | keeps the anchor's weekday                                    |
| `monthly` | `+ interval` months     | day-of-month clamped to the month's length                    |
| `yearly`  | `+ interval` years      | 29 Feb → 28 Feb in a non-leap year                            |

**Clamping is computed from the anchor, never from the previous occurrence.**
A schedule anchored on the 31st goes 31 Jan → 28 Feb → 31 Mar, *not*
31 Jan → 28 Feb → 28 Mar. Getting this wrong silently walks every long-lived
schedule backwards through the calendar, so it gets its own test.

| Anchor  | Feb (non-leap) | Mar | Apr |
| ------- | -------------- | --- | --- |
| the 31st | 28 | 31 | 30 |
| the 30th | 28 | 30 | 30 |
| the 15th | 15 | 15 | 15 |

### API

```
GET    /api/schedules                                 list (include_paused=false)
POST   /api/schedules                                 create                  201
GET    /api/schedules/{schedule_id}                   read
PATCH  /api/schedules/{schedule_id}                   partial update
DELETE /api/schedules/{schedule_id}                                           204

GET    /api/schedules/occurrences                     the approval queue
POST   /api/schedules/occurrences/{occurrence_id}/approve                     201
POST   /api/schedules/occurrences/{occurrence_id}/skip
```

> **Route ordering gotcha:** declare `/schedules/occurrences` *before*
> `/schedules/{schedule_id}` in the router, or FastAPI tries to parse
> `occurrences` as a UUID and answers 422.

Mounted from `api/__init__.py` alongside the existing four routers.

#### `GET /api/schedules/occurrences`

Query: `until` (date, defaults to the horizon), `status` (defaults to
`pending`), `schedule_id`. Materialises, then returns occurrences ordered by
`due_date` ascending, each **denormalised with everything a row needs to render**
— the frontend must not have to fetch the schedule per row:

```jsonc
{
  "id": "…",
  "schedule_id": "…",
  "due_date": "2026-09-01",
  "status": "pending",
  "transaction_id": null,
  "account_id": "…",
  "payee_id": "…",
  "amount": -1200000,
  "memo": "Rent",
  "splits": [{ "category_id": "…", "amount": -1200000, "memo": null }],
  "overdue": true          // due_date < today
}
```

#### `POST …/{occurrence_id}/approve`

Body is `OccurrenceApproval`, every field optional — it overrides the template
for this one occurrence, which is how a variable bill (utilities, groceries)
gets approved at its real amount:

```jsonc
{ "date": "2026-09-02", "amount": -1215500, "payee_id": "…", "memo": "…",
  "cleared": "cleared", "splits": [ … ] }
```

`date` defaults to `due_date`, everything else to the schedule's template.
Sending `splits` requires sending `amount`, and the two must agree — the same
validator rule `TransactionUpdate` already uses.

In one database transaction: insert the `transaction` and its splits, set the
occurrence to `approved` with its `transaction_id`. Returns the created
`Transaction`, `201`. Approving an occurrence that is not `pending` is `409
conflict`.

#### `POST …/{occurrence_id}/skip`

Sets `skipped`, writes nothing else. Returns the occurrence. Not `pending` →
`409`. Skipping is not undoable in this phase.

#### Rules that are easy to get wrong

- **Editing a schedule never touches history.** Approved occurrences and the
  transactions they produced are copies; changing `amount` does not rewrite them.
- **A `PATCH` touching `frequency`, `interval`, `anchor_date` or `ends_on`
  deletes that schedule's *pending* occurrences and recomputes `next_due` from
  the new rule.** `approved` and `skipped` rows survive. Otherwise a corrected
  rule leaves stale proposals in the queue.
- **Pausing leaves pending occurrences in place** — they are already due; the
  user still owes them a decision. Pausing only stops new ones being generated.
- **Deleting a schedule cascades to its occurrences** but leaves the
  transactions already approved from it, which are ordinary transactions now.
- **Deleting an approved occurrence's transaction** nulls `transaction_id` and
  leaves the occurrence `approved`. It does not return to the queue.
- `DELETE /api/schedules/{id}` is unconditional. There is no "in use" guard,
  because approved transactions no longer reference the schedule.

#### Errors

Nothing new. Integrity stays the database's job and surfaces through
`api/errors.py` as it does today: unknown account/payee/category on write →
`422 invalid_reference`; approving a non-pending occurrence → `409 conflict`;
unknown id → `404 not_found`. Splits not summing to the amount is a pydantic
`422`, matching transactions.

### Screen — `/scheduled`

New route, added to the nav in `src/layouts/Base.astro` between Transactions and
Payees. Same conventions as the existing screens: static page, browser-side
fetch, in-place editing, the API's refusal shown in the banner under the title.

Three sections, top to bottom:

1. **Due now** — `due_date <= today`, overdue ones flagged. Each row: date,
   payee, category, an **editable amount field** pre-filled from the template,
   and `Approve` / `Skip`. Approving re-renders the row as confirmed and drops
   it from the queue. This section is the feature; it should be usable with one
   click per row and no navigation.
2. **Upcoming** — `today < due_date <= horizon`, read-only, grouped by week,
   with a running total so the user can see what is coming.
3. **Schedules** — the rules themselves: create, edit in place, pause, delete.
   Frequency and interval render as a single readable phrase ("every 2 weeks",
   "monthly on the 15th"); a small `describe(schedule)` helper in
   `src/lib/format.ts` owns that wording so the dashboard reuses it.

`src/lib/types.ts` gains `Schedule`, `ScheduleCreate`, `ScheduleUpdate`,
`ScheduledOccurrence`, `OccurrenceApproval`, `Frequency`, `OccurrenceStatus`;
`src/lib/api.ts` gains `api.schedules` with `list/get/create/update/remove` plus
`occurrences/approve/skip`.

### Marking scheduled transactions in the register

Decided in [Open questions](#open-questions): a transaction written by
approving an occurrence is marked as such in the existing register, not just
reachable through `/scheduled`.

- `Transaction` (the read shape, in `schemas/transaction.py` and its mirror in
  `types.ts`) gains `scheduled_occurrence_id: UUID | None`. `TransactionCreate`
  and `TransactionUpdate` are untouched — the field is read-only and never
  arrives in a write; a transaction cannot be attached to a schedule after the
  fact.
- `repositories/transactions.py` sources it with a `LEFT JOIN scheduled_occurrence
  ON scheduled_occurrence.transaction_id = transaction.id` in both
  `list_transactions` and `get_transaction`, added to `SELECT`, not to the
  writes. The unique index above is what makes this join return at most one row.
- The register (`src/pages/transactions.astro`) renders a small badge next to a
  marked row's payee, linking to `/scheduled`. No filter is added for it in
  this phase — it is a badge, not a new query parameter.

---

## Feature 2 — Dashboard

### Goal

One screen answering "where do I stand", built only from data that already
exists. Note what the data model **cannot** answer: there is no budgeted amount
anywhere in the schema, so there is no "left to spend" and no budget-vs-actual.
The dashboard reports activity. Do not let a panel imply otherwise.

### API — one endpoint, one round trip

```
GET /api/dashboard?month=YYYY-MM&months=6
```

`month` defaults to the current month, `months` to `6` (range 1–24).

A single composed endpoint rather than four, for the same reason an account
reads back with its `balance`: the frontend has no state library and no client
router, and four parallel fetches with four partial failures is a lot of
machinery for one screen. It lives in a new
`backend/vibudget/repositories/dashboard.py` as four read-only queries behind
one `Dashboard` schema.

```jsonc
{
  "month": "2026-08",
  "net_worth": { "on_budget": 4210500, "off_budget": 150000, "total": 4360500 },
  "accounts": [
    { "id": "…", "name": "Checking", "type": "cash",
      "on_budget": true, "closed": false, "balance": 2100000 }
  ],
  "cashflow": [
    { "month": "2026-03", "inflow": 3200000, "outflow": -2870000, "net": 330000 }
  ],
  "spending": [
    { "group_id": "…", "group_name": "Everyday", "amount": -845000,
      "previous_amount": -910000,
      "categories": [
        { "id": "…", "name": "Groceries", "amount": -520000, "previous_amount": -498000 }
      ] }
  ],
  "upcoming": {
    "due_count": 3, "due_total": -1450000,
    "next_7_days": [ /* ScheduledOccurrence, same shape as the queue */ ]
  },
  "uncleared_count": 7
}
```

### Panel semantics — be exact, these are easy to compute differently

**`net_worth` / `accounts`** — an account's balance is the sum of its
transactions, as `GET /api/accounts` already computes it. **Closed accounts are
included**: a closed account with a residual balance is still money. `on_budget`
and `off_budget` split on `account.on_budget`; `total` is their sum.

**`cashflow`** — `months` buckets ending with `month`, oldest first, **including
months with no transactions** (zero rows, so the chart has no gaps).
On-budget accounts only.

```sql
inflow  = COALESCE(SUM(amount) FILTER (WHERE amount > 0), 0)
outflow = COALESCE(SUM(amount) FILTER (WHERE amount < 0), 0)
net     = inflow + outflow
```

**`spending`** — over `transaction_split`, not `transaction`, so a split
transaction lands in each of its categories. On-budget accounts only, outflows
only (`split.amount < 0`). Grouped by sub-category and rolled up to its group.
`previous_amount` is the same figure for the preceding calendar month, for the
comparison. **Amounts stay signed and negative** — every other amount in this
codebase is signed, and flipping the sign for one panel is how a currency bug
gets in. The frontend renders the magnitude.

Categories with no activity in either month are omitted. A group whose
sub-categories all drop out drops out too. Hidden categories are included if
they have activity — hiding is a UI preference, not a filter on history.

**`upcoming`** — from `scheduled_occurrence` where `status = 'pending'`.
`due_count` and `due_total` cover everything due today or earlier (what is
waiting on the user), `next_7_days` looks forward. It calls the same
materialisation function `GET /api/schedules/occurrences` calls, so the two
screens never disagree.

**`uncleared_count`** — transactions with `cleared = 'uncleared'`, on-budget
accounts, no date bound.

### Screen — `/dashboard`

New route, first in the nav. Panels in reading order: net worth and accounts,
cashflow, spending by category, upcoming and unapproved.

A month picker in the header, matching the budget screen's. The upcoming panel
links to `/scheduled`; each account links to
`/transactions?account_id=…`, each category to
`/transactions?category_id=…&since=…&until=…`, reusing the URL filters the
register already honours. `uncleared_count` links to the register.

Charts: cashflow is the only panel that wants one. Inline SVG built from the
response — **no charting library**; the repo's "nothing beyond Astro" rule
holds. If it turns out to need one, that is a change to this spec, not a
judgement call during the build.

---

## Splitting the work

### Phase 0 — the contract, together (blocks everything)

Both teams agree the payload shapes above, then land, in one PR:

- `backend/vibudget/schemas/schedule.py` and `dashboard.py` — pydantic only,
  no SQL, no endpoints.
- The matching interfaces in `frontend/src/lib/types.ts`.

Nothing else starts until this merges. It is the only file both teams edit.

### Then, in parallel

| Backend                                                | Frontend                                          |
| ------------------------------------------------------ | ------------------------------------------------- |
| `002_schedules.sql` + migration test                    | `/scheduled` markup, styles, nav entry            |
| `recurrence.py` + its unit tests (no DB — start here)   | `api.schedules` in `api.ts`                       |
| `repositories/schedules.py`                             | Due-now rows: amount override, Approve / Skip      |
| `api/schedules.py`, mounted                             | Upcoming and Schedules sections                    |
| `repositories/dashboard.py` — the four queries          | `/dashboard` panels and the cashflow SVG           |
| `api/dashboard.py`                                      | `describe(schedule)` in `format.ts`               |
| Endpoint tests against a real database                  | Empty, loading and error states for every panel    |
| `scheduled_occurrence_id` join in `repositories/transactions.py` | Register badge for a marked transaction   |

### Ownership of shared files

| File                              | Owner    | Rule                                              |
| --------------------------------- | -------- | ------------------------------------------------- |
| `schemas/*.py`, migrations        | backend  | frontend never edits                               |
| `src/lib/types.ts`                | **both** | changed only in a PR that also changes the schema  |
| `src/lib/api.ts`, `src/pages/*`   | frontend | backend never edits                                |
| `AGENTS.md`, `compose*.yaml`, this spec | **both** | needs a reviewer from each team                |

### Definition of done

- `cd backend && .venv/bin/python -m pytest` green, including endpoint tests
  against a real PostgreSQL, and the clamping table above covered case by case.
- `.venv/bin/ruff check .` clean.
- `cd frontend && npm run check && npm run build` clean.
- `docker compose up --build` gives working `/scheduled` and `/dashboard` screens
  against a database seeded with at least one daily, weekly, monthly and
  month-end schedule.
- README updated: the routes table, the endpoints table, and the "Not built yet"
  list.

### Suggested order of merge

1. Phase 0 contract.
2. `recurrence.py` — pure, testable, unblocks nothing but derisks the most.
3. Migration + schedule CRUD, with the frontend's Schedules section behind it.
4. Occurrences + approve/skip, with the Due-now section.
5. Dashboard, last — its `upcoming` panel needs occurrences to exist.

---

## Phase 2 — detecting recurrence (not now)

Recorded so this phase does not design itself into a corner, **not to be built
yet**.

Detection would scan `transaction` for repeating `(payee_id, account_id)` groups
with a stable amount and a stable interval, and propose a schedule. The design
constraint on *this* phase is only that it reuses what is built here: a detected
pattern becomes a `schedule` row like any other, and its proposals flow through
the same `scheduled_occurrence` queue and the same Approve / Skip endpoints. The
frontend's Due-now section should not care where a row came from.

The additions it would need, when the time comes: a `source` enum on `schedule`
(`manual | detected`), a `confidence` numeric, and a way to dismiss a bad guess
permanently. Nothing above needs to change to accommodate them.

---

## Open questions

Decided by both teams on 2026-08-31; Phase 0 is unblocked.

1. **Should approving from the dashboard be possible**, or does the dashboard's
   upcoming panel only link to `/scheduled`? **Decided: link-only**, as
   originally specified. The dashboard stays a read-only, composed screen;
   approve/skip lives only in `/scheduled`.
2. **Should the register mark transactions that came from a schedule?**
   **Decided: yes.** See
   [Marking scheduled transactions in the register](#marking-scheduled-transactions-in-the-register)
   under Feature 1 — `Transaction.scheduled_occurrence_id`, a `LEFT JOIN` in
   the transactions repository, and a badge in the register linking to
   `/scheduled`.
3. **Overdue horizon.** An occurrence from six months ago that was never
   approved or skipped stays in Due-now forever. **Decided: no auto-skip.**
   The queue is unbounded by design; the user stays in control of every
   occurrence. Revisit only if this proves a real problem in use.
4. **Timezone.** `due_date` is compared against the server's `CURRENT_DATE`,
   while `format.ts::today()` uses the viewer's timezone. **Decided: keep the
   server's `CURRENT_DATE`** as the source of truth for due/overdue; no `today`
   field is added to the API. The few hours of disagreement around midnight for
   a traveling user is an accepted trade for not threading a clock through
   every affected response.
5. **Currency.** `formatMilliunits` hardcodes USD. **Decided: out of scope**
   for this spec, exactly as proposed. It gets its own spec if and when it is
   tackled — not folded into scheduling and the dashboard.
