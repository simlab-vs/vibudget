-- Demo budget for one person in Zurich, from September 2024 to August 2026.
-- This is data only: it neither creates nor alters application schema objects.
-- It is safe to rerun: an existing budget is left untouched.

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM account)
      OR EXISTS (SELECT 1 FROM payee)
      OR EXISTS (SELECT 1 FROM transaction)
    THEN 'false'
    ELSE 'true'
END AS should_seed \gset

\if :should_seed
BEGIN;

INSERT INTO account (name, type, on_budget, note) VALUES
    ('Everyday Checking', 'cash', true, 'Primary account for salary and day-to-day spending.'),
    ('Emergency Savings', 'cash', true, 'Cash reserve.'),
    ('Visa Cash Back', 'credit', true, 'Credit card paid from Everyday Checking.'),
    ('Student Loan', 'credit', false, 'Off-budget education debt.');

INSERT INTO category (name) VALUES
    ('Income'),
    ('Housing'),
    ('Food'),
    ('Transport'),
    ('Health & wellbeing'),
    ('Financial obligations'),
    ('Lifestyle'),
    ('Savings'),
    ('Irregular expenses');

WITH children (parent_name, child_name) AS (
    VALUES
        ('Income', 'Salary'), ('Income', 'Interest & refunds'),
        ('Housing', 'Rent'), ('Housing', 'Electricity'), ('Housing', 'Internet & mobile'),
        ('Housing', 'Household supplies'),
        ('Food', 'Groceries'), ('Food', 'Dining out'), ('Food', 'Coffee & snacks'),
        ('Transport', 'Public transport'), ('Transport', 'Rideshare & taxi'), ('Transport', 'Bike maintenance'),
        ('Health & wellbeing', 'Health insurance'), ('Health & wellbeing', 'Gym'),
        ('Health & wellbeing', 'Pharmacy & medical'),
        ('Financial obligations', 'Taxes'), ('Financial obligations', 'Student loan'),
        ('Financial obligations', 'Credit card payment'), ('Financial obligations', 'Household insurance'),
        ('Lifestyle', 'Streaming & software'), ('Lifestyle', 'Hobbies'), ('Lifestyle', 'Clothing'),
        ('Lifestyle', 'Gifts & social'), ('Lifestyle', 'Travel'),
        ('Savings', 'Emergency fund'), ('Savings', 'Travel fund'),
        ('Irregular expenses', 'Home repair'), ('Irregular expenses', 'Electronics'),
        ('Irregular expenses', 'Professional fees')
)
INSERT INTO category (name, parent_id)
SELECT children.child_name, parent.id
FROM children
JOIN category AS parent ON parent.name = children.parent_name AND parent.parent_id IS NULL;

INSERT INTO payee (name) VALUES
    ('Acme Design Studio'), ('Helvetia Health'), ('SBB Mobile'), ('Sunrise Internet'),
    ('EWZ Electricity'), ('City Property Management'), ('EduLoan Services'),
    ('Netflix'), ('Spotify'), ('Proton'), ('Activ Fitness'), ('Coop'), ('Migros'),
    ('Local Bakery'), ('Office Lunch'), ('Corner Café'), ('Uber'), ('Velo Workshop'),
    ('Amica Insurance'), ('Swiss Tax Office'), ('Galaxus'), ('IKEA'), ('Bookshop'),
    ('Cinema'), ('Friends'), ('Swiss Airlines'), ('Hotel Alpenblick'), ('Apple App Store'),
    ('Visa Payment'), ('Savings Transfer'), ('Pharmacy'), ('Dentist'), ('Landlord Repair'),
    ('Tax Refund'), ('Bank Interest');

CREATE OR REPLACE FUNCTION pg_temp.add_transaction(
    p_account text,
    p_payee text,
    p_category text,
    p_date date,
    p_amount bigint,
    p_memo text DEFAULT NULL,
    p_cleared cleared_status DEFAULT 'cleared'
) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    v_transaction_id uuid;
    v_account_id uuid;
    v_payee_id uuid;
    v_category_id uuid;
BEGIN
    SELECT id INTO v_account_id FROM account WHERE name = p_account;
    SELECT id INTO v_payee_id FROM payee WHERE name = p_payee;
    SELECT id INTO v_category_id FROM category WHERE name = p_category AND parent_id IS NOT NULL;

    INSERT INTO transaction (account_id, payee_id, date, amount, memo, cleared)
    VALUES (v_account_id, v_payee_id, p_date, p_amount, p_memo, p_cleared)
    RETURNING id INTO v_transaction_id;

    INSERT INTO transaction_split (transaction_id, category_id, amount, memo)
    VALUES (v_transaction_id, v_category_id, p_amount, p_memo);
END;
$$;

DO $$
DECLARE
    m date;
    d date;
    i integer;
    monthly_salary bigint;
    electricity bigint;
BEGIN
    -- Reliable monthly, quarterly and annual commitments.  Amounts are milliunits.
    FOR m IN SELECT generate_series(DATE '2024-09-01', DATE '2026-08-01', INTERVAL '1 month')::date LOOP
        monthly_salary := CASE WHEN m < DATE '2025-01-01' THEN 5050000
                               WHEN m < DATE '2026-01-01' THEN 5200000 ELSE 5350000 END;
        electricity := -(50000 + ((EXTRACT(MONTH FROM m)::integer * 9000) % 62000));

        PERFORM pg_temp.add_transaction('Everyday Checking', 'Acme Design Studio', 'Salary', m + 24, monthly_salary, 'Net monthly salary');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'City Property Management', 'Rent', m, CASE WHEN m < DATE '2025-09-01' THEN -1650000 ELSE -1725000 END, 'Monthly rent');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'Sunrise Internet', 'Internet & mobile', m + 4, -49900, 'Home internet');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'Sunrise Internet', 'Internet & mobile', m + 7, -27900, 'Mobile plan');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'EWZ Electricity', 'Electricity', m + 10, electricity, 'Monthly electricity bill');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'Helvetia Health', 'Health insurance', m + 14, CASE WHEN m < DATE '2025-01-01' THEN -358000 WHEN m < DATE '2026-01-01' THEN -371000 ELSE -389000 END, 'Basic health insurance premium');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'SBB Mobile', 'Public transport', m + 2, -86000, 'Monthly travelcard');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'Activ Fitness', 'Gym', m + 5, -59900, 'Monthly membership');
        PERFORM pg_temp.add_transaction('Visa Cash Back', 'Netflix', 'Streaming & software', m + 3, -15490, 'Subscription');
        PERFORM pg_temp.add_transaction('Visa Cash Back', 'Spotify', 'Streaming & software', m + 9, -11990, 'Subscription');
        PERFORM pg_temp.add_transaction('Visa Cash Back', 'Proton', 'Streaming & software', m + 16, -9900, 'Mail storage subscription');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'EduLoan Services', 'Student loan', m + 18, -285000, 'Student loan repayment');
        PERFORM pg_temp.add_transaction('Everyday Checking', 'Savings Transfer', 'Emergency fund', m + 25, -350000, 'Monthly reserve transfer');

        -- Groceries most Saturdays; coffee and a few lunches create natural variation.
        FOR d IN SELECT generate_series(m, (m + INTERVAL '1 month - 1 day')::date, INTERVAL '7 days')::date LOOP
            PERFORM pg_temp.add_transaction('Visa Cash Back', CASE WHEN EXTRACT(WEEK FROM d)::integer % 2 = 0 THEN 'Coop' ELSE 'Migros' END, 'Groceries', d + 1, -(68000 + ((EXTRACT(DAY FROM d)::integer * 7000) % 67000)), 'Weekly groceries');
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Corner Café', 'Coffee & snacks', LEAST(d + 3, (m + INTERVAL '1 month - 1 day')::date), -(5500 + ((EXTRACT(DAY FROM d)::integer * 900) % 4200)), NULL);
        END LOOP;
        FOR i IN 1..2 LOOP
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Office Lunch', 'Dining out', m + (5 + i * 8), -(21000 + ((EXTRACT(MONTH FROM m)::integer * i * 3000) % 19000)), NULL);
        END LOOP;

        -- Card settlement is intentionally recurrent, but not quite identical every month.
        PERFORM pg_temp.add_transaction('Everyday Checking', 'Visa Payment', 'Credit card payment', m + 20, -(720000 + ((EXTRACT(MONTH FROM m)::integer * 37000) % 260000)), 'Credit card statement payment');

        IF EXTRACT(MONTH FROM m)::integer IN (3, 6, 9, 12) THEN
            PERFORM pg_temp.add_transaction('Everyday Checking', 'Swiss Tax Office', 'Taxes', m + 11, -(1230000 + (EXTRACT(MONTH FROM m)::integer * 17000)), 'Quarterly cantonal tax instalment');
        END IF;
        IF EXTRACT(MONTH FROM m)::integer = 2 THEN
            PERFORM pg_temp.add_transaction('Everyday Checking', 'Amica Insurance', 'Household insurance', m + 1, -238000, 'Annual household and liability insurance');
        END IF;
        IF EXTRACT(MONTH FROM m)::integer = 10 THEN
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Apple App Store', 'Streaming & software', m + 6, -79000, 'Annual app subscription');
        END IF;
        IF EXTRACT(MONTH FROM m)::integer = 1 THEN
            PERFORM pg_temp.add_transaction('Emergency Savings', 'Bank Interest', 'Interest & refunds', m + 30, 18500, 'Annual savings interest');
        END IF;

        -- Purposefully irregular spending: a useful contrast for recurrence analysis.
        IF EXTRACT(MONTH FROM m)::integer IN (1, 4, 7, 10) THEN
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Bookshop', 'Hobbies', m + 12, -(29000 + EXTRACT(MONTH FROM m)::integer * 3000), 'Books and supplies');
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Cinema', 'Gifts & social', m + 21, -38500, 'Evening out');
        END IF;
        IF EXTRACT(MONTH FROM m)::integer IN (3, 8) THEN
            PERFORM pg_temp.add_transaction('Everyday Checking', 'Velo Workshop', 'Bike maintenance', m + 8, -(85000 + EXTRACT(MONTH FROM m)::integer * 11000), 'Seasonal bike service');
        END IF;
        IF EXTRACT(MONTH FROM m)::integer = 5 THEN
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Dentist', 'Pharmacy & medical', m + 19, -185000, 'Dental check-up');
        END IF;
        IF EXTRACT(MONTH FROM m)::integer = 11 THEN
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Galaxus', 'Electronics', m + 15, -429000, 'Headphones replacement');
        END IF;
        IF EXTRACT(MONTH FROM m)::integer = 12 THEN
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Friends', 'Gifts & social', m + 17, -215000, 'Holiday gifts');
        END IF;
        IF EXTRACT(MONTH FROM m)::integer = 7 THEN
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Swiss Airlines', 'Travel', m + 9, -385000, 'Summer trip flight');
            PERFORM pg_temp.add_transaction('Visa Cash Back', 'Hotel Alpenblick', 'Travel', m + 10, -612000, 'Summer trip accommodation');
        END IF;
    END LOOP;

    -- A handful of genuinely one-off events, including an inflow that is not salary.
    PERFORM pg_temp.add_transaction('Everyday Checking', 'Tax Refund', 'Interest & refunds', DATE '2025-04-22', 418000, '2024 tax refund');
    PERFORM pg_temp.add_transaction('Visa Cash Back', 'IKEA', 'Household supplies', DATE '2025-03-15', -286000, 'Desk chair');
    PERFORM pg_temp.add_transaction('Everyday Checking', 'Landlord Repair', 'Home repair', DATE '2025-06-03', -174000, 'Share of plumbing repair');
    PERFORM pg_temp.add_transaction('Visa Cash Back', 'Pharmacy', 'Pharmacy & medical', DATE '2026-02-18', -48200, 'Winter prescription');
END;
$$;

COMMIT;
\else
\echo 'Budget data already exists; demo seed skipped.'
\endif
