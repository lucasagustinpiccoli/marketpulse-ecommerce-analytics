-- MarketPulse — SQL Analysis
-- Fictional e-commerce marketplace, synthetic data (see data/generate_data.py).
-- Run against data/marketpulse.db (SQLite). Each query is self-contained;
-- run them individually with `sqlite3 data/marketpulse.db < sql/analysis.sql`
-- or copy one block at a time into a SQLite client.

-- ============================================================
-- 1. Monthly revenue by region (core KPI, the "what happened" view)
-- ============================================================
SELECT
    strftime('%Y-%m', order_date) AS month,
    region,
    SUM(revenue)                   AS gross_revenue,
    COUNT(*)                       AS order_count,
    ROUND(AVG(revenue), 2)         AS avg_order_value
FROM orders
WHERE was_cancelled = 0
GROUP BY month, region
ORDER BY month, region;

-- ============================================================
-- 2. Month-over-month growth per category (window function: LAG)
--    Surfaces trend direction without a self-join.
-- ============================================================
WITH monthly_category_revenue AS (
    SELECT
        strftime('%Y-%m', order_date) AS month,
        category,
        SUM(revenue) AS revenue
    FROM orders
    WHERE was_cancelled = 0
    GROUP BY month, category
)
SELECT
    month,
    category,
    revenue,
    LAG(revenue) OVER (PARTITION BY category ORDER BY month)              AS prev_month_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (PARTITION BY category ORDER BY month))
        / LAG(revenue) OVER (PARTITION BY category ORDER BY month),
    2) AS mom_growth_pct
FROM monthly_category_revenue
ORDER BY category, month;

-- ============================================================
-- 3. Seller leaderboard per region (window function: RANK, partitioned)
--    Same shape as the "20+ sales executives" forecasting/ranking work.
-- ============================================================
WITH seller_revenue AS (
    SELECT
        o.seller_id,
        s.seller_name,
        s.region,
        s.tier,
        SUM(o.revenue) AS total_revenue,
        COUNT(*)       AS total_orders
    FROM orders o
    JOIN sellers s ON s.seller_id = o.seller_id
    WHERE o.was_cancelled = 0
    GROUP BY o.seller_id
)
SELECT
    region,
    seller_name,
    tier,
    total_revenue,
    total_orders,
    RANK() OVER (PARTITION BY region ORDER BY total_revenue DESC) AS rank_in_region
FROM seller_revenue
ORDER BY region, rank_in_region
LIMIT 40;

-- ============================================================
-- 4. Root-cause / anomaly detection (CTE + window function: rolling
--    mean + stddev, the SQL equivalent of a z-score alert)
--    Weekly grain (same cadence as a WBR) keeps the signal stable enough
--    per region x category cell to flag a real demand collapse instead of
--    chasing single-day noise. This is the query that would feed an
--    automated anomaly-detection dashboard (same pattern as a Looker
--    Studio / BigQuery alerting view).
-- ============================================================
WITH weekly_category_region AS (
    SELECT
        strftime('%Y-%W', order_date) AS iso_week,
        MIN(order_date)               AS week_start,
        region,
        category,
        COUNT(*)                      AS weekly_orders
    FROM orders
    GROUP BY iso_week, region, category
),
rolling_stats AS (
    SELECT
        iso_week,
        week_start,
        region,
        category,
        weekly_orders,
        AVG(weekly_orders) OVER (
            PARTITION BY region, category
            ORDER BY iso_week
            ROWS BETWEEN 8 PRECEDING AND 1 PRECEDING
        ) AS rolling_avg_8wk,
        -- SQLite has no native STDDEV; approximate via a population formula
        -- (sqrt of mean-of-squares minus square-of-mean) over the same window.
        SQRT(
            AVG(weekly_orders * weekly_orders) OVER (
                PARTITION BY region, category
                ORDER BY iso_week
                ROWS BETWEEN 8 PRECEDING AND 1 PRECEDING
            )
            - POWER(AVG(weekly_orders) OVER (
                PARTITION BY region, category
                ORDER BY iso_week
                ROWS BETWEEN 8 PRECEDING AND 1 PRECEDING
            ), 2)
        ) AS rolling_stddev_8wk,
        ROW_NUMBER() OVER (PARTITION BY region, category ORDER BY iso_week) AS week_number
    FROM weekly_category_region
)
SELECT
    week_start,
    region,
    category,
    weekly_orders,
    ROUND(rolling_avg_8wk, 1)    AS rolling_avg_8wk,
    ROUND(rolling_stddev_8wk, 1) AS rolling_stddev_8wk,
    ROUND((weekly_orders - rolling_avg_8wk) / rolling_stddev_8wk, 2) AS z_score
FROM rolling_stats
WHERE week_number > 8                          -- need a full 8-week history first
  AND rolling_stddev_8wk > 0
  AND (weekly_orders - rolling_avg_8wk) / rolling_stddev_8wk < -2.0   -- flag drops > 2 std devs
ORDER BY z_score ASC
LIMIT 20;

-- ============================================================
-- 5. Cancellation-rate flag by region + category (the "which lever moved" view)
--    Pairs with query 4: once an anomaly is flagged, this checks whether
--    cancellations moved too, which is what separates "demand dipped" from
--    "something broke downstream" - the root-cause analysis step.
-- ============================================================
SELECT
    region,
    category,
    strftime('%Y-%m', order_date) AS month,
    COUNT(*)                                  AS total_orders,
    SUM(was_cancelled)                         AS cancelled_orders,
    ROUND(100.0 * SUM(was_cancelled) / COUNT(*), 2) AS cancellation_rate_pct
FROM orders
GROUP BY region, category, month
HAVING cancellation_rate_pct > 10
ORDER BY cancellation_rate_pct DESC;
