"""
Synthetic data generator for the MarketPulse case study.

MarketPulse is a fictional e-commerce marketplace. Every seller, order, and
number in this dataset is randomly generated with a fixed seed - none of it
comes from a real company or a real employer. It exists to demonstrate a
SQL + Python analytics workflow end to end, including a deliberately
injected anomaly for the root-cause-analysis section of the notebook.

Run:
    python generate_data.py
Produces:
    marketpulse.db   (SQLite database with sellers, categories, orders)
"""
import sqlite3
import random
from datetime import date, timedelta

random.seed(42)

DB_PATH = "marketpulse.db"

REGIONS = ["Argentina", "Chile", "Mexico", "Colombia"]
CATEGORIES = [
    ("Electronics", 1.00),
    ("Home & Kitchen", 0.75),
    ("Fashion", 0.55),
    ("Sports & Outdoors", 0.60),
    ("Beauty & Personal Care", 0.45),
    ("Grocery", 0.30),
]
SELLER_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]

START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 9, 27)  # a Sunday - keeps every week in the dataset complete (7 full days)
N_SELLERS = 42

# A deliberate, known-cause anomaly for the case study's root-cause section:
# Fashion sellers in Mexico see a conversion collapse for 5 weeks after a
# (fictional) logistics-partner outage. This is the "find the needle" the
# SQL + notebook sections are built to surface.
ANOMALY_CATEGORY = "Fashion"
ANOMALY_REGION = "Mexico"
ANOMALY_START = date(2026, 4, 6)
ANOMALY_END = date(2026, 5, 10)


def build_sellers(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE sellers (
            seller_id INTEGER PRIMARY KEY,
            seller_name TEXT,
            region TEXT,
            category TEXT,
            tier TEXT,
            joined_date TEXT
        )
    """)
    rows = []
    for sid in range(1, N_SELLERS + 1):
        region = random.choice(REGIONS)
        category = random.choices(
            [c for c, _ in CATEGORIES],
            weights=[w for _, w in CATEGORIES],
        )[0]
        tier = random.choices(SELLER_TIERS, weights=[0.40, 0.30, 0.20, 0.10])[0]
        joined = START_DATE - timedelta(days=random.randint(0, 900))
        rows.append((sid, f"Seller-{sid:03d}", region, category, tier, joined.isoformat()))
    cur.executemany("INSERT INTO sellers VALUES (?,?,?,?,?,?)", rows)
    conn.commit()
    return {r[0]: r for r in rows}


def daily_seasonality(d: date) -> float:
    # Weekly pattern: weekends lower (marketplace skews weekday B2C buying),
    # plus a mild end-of-month payday bump, plus a slow YoY growth trend.
    weekday_factor = {0: 1.05, 1: 1.05, 2: 1.0, 3: 1.0, 4: 1.1, 5: 0.75, 6: 0.7}[d.weekday()]
    payday_factor = 1.25 if d.day in (1, 2, 15, 16) else 1.0
    days_since_start = (d - START_DATE).days
    growth_factor = 1.0 + (days_since_start / 365) * 0.18  # ~18%/yr organic growth
    # November-December seasonal demand bump (Cyber Monday / holiday season)
    season_factor = 1.0
    if d.month == 11 or (d.month == 12 and d.day <= 24):
        season_factor = 1.45
    return weekday_factor * payday_factor * growth_factor * season_factor


def build_orders(conn, sellers):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            order_date TEXT,
            seller_id INTEGER,
            region TEXT,
            category TEXT,
            units INTEGER,
            revenue REAL,
            was_cancelled INTEGER,
            FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        )
    """)
    seller_ids = list(sellers.keys())
    base_price = {
        "Electronics": 180, "Home & Kitchen": 60, "Fashion": 35,
        "Sports & Outdoors": 70, "Beauty & Personal Care": 25, "Grocery": 18,
    }

    order_id = 1
    rows = []
    d = START_DATE
    while d <= END_DATE:
        seasonal_mult = daily_seasonality(d)
        base_orders_today = int(230 * seasonal_mult)
        in_anomaly_window = ANOMALY_START <= d <= ANOMALY_END

        for _ in range(base_orders_today):
            seller_id = random.choice(seller_ids)
            _, _, region, category, tier, _ = sellers[seller_id]

            # Inject the anomaly: Fashion sellers in Mexico lose ~65% of their
            # order volume during the outage window (simulated carrier failure).
            if in_anomaly_window and region == ANOMALY_REGION and category == ANOMALY_CATEGORY:
                if random.random() < 0.65:
                    continue  # the order never completes - lost demand

            tier_mult = {"Bronze": 0.8, "Silver": 1.0, "Gold": 1.25, "Platinum": 1.5}[tier]
            units = max(1, int(random.gauss(2.2, 1.1)))
            unit_price = base_price[category] * random.uniform(0.85, 1.2) * tier_mult
            revenue = round(units * unit_price, 2)

            # Slightly elevated cancellation rate inside the anomaly window too
            cancel_prob = 0.06
            if in_anomaly_window and region == ANOMALY_REGION and category == ANOMALY_CATEGORY:
                cancel_prob = 0.22
            was_cancelled = 1 if random.random() < cancel_prob else 0

            rows.append((order_id, d.isoformat(), seller_id, region, category,
                         units, revenue, was_cancelled))
            order_id += 1

        d += timedelta(days=1)

    cur.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    print(f"Generated {len(rows):,} orders across {N_SELLERS} sellers "
          f"from {START_DATE} to {END_DATE}.")


def main():
    conn = sqlite3.connect(DB_PATH)
    sellers = build_sellers(conn)
    build_orders(conn, sellers)
    conn.close()
    print(f"Wrote {DB_PATH}")


if __name__ == "__main__":
    main()
