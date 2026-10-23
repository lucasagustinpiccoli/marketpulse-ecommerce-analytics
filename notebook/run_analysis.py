"""
MarketPulse — exploratory analysis + anomaly investigation.

This is the script version of notebook/analysis.ipynb, kept separate so the
charts can be regenerated from the command line without a notebook kernel:

    python notebook/run_analysis.py

Produces PNGs in notebook/figures/ and prints the same summary stats that
back the README's "Key findings" section.
"""
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
DB_PATH = HERE.parent / "data" / "marketpulse.db"
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(exist_ok=True)

plt.rcParams["figure.dpi"] = 140
plt.rcParams["font.size"] = 10
ACCENT = "#2563eb"
MUTED = "#94a3b8"
ALERT = "#dc2626"

# ------------------------------------------------------------------
# Load
# ------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
orders = pd.read_sql_query(
    "SELECT * FROM orders WHERE was_cancelled = 0", conn, parse_dates=["order_date"]
)
all_orders = pd.read_sql_query(
    "SELECT * FROM orders", conn, parse_dates=["order_date"]
)
sellers = pd.read_sql_query("SELECT * FROM sellers", conn)
conn.close()

orders["month"] = orders["order_date"].dt.to_period("M").astype(str)
orders["week_start"] = orders["order_date"].dt.to_period("W").dt.start_time

# ------------------------------------------------------------------
# 1. Revenue trend by region
# ------------------------------------------------------------------
monthly_region = (
    orders.groupby(["month", "region"])["revenue"].sum().reset_index()
)
pivot = monthly_region.pivot(index="month", columns="region", values="revenue")

fig, ax = plt.subplots(figsize=(10, 5))
pivot.plot(ax=ax, marker="o", linewidth=1.8)
ax.set_title("MarketPulse — Monthly Revenue by Region (synthetic data)")
ax.set_ylabel("Revenue (synthetic currency units)")
ax.set_xlabel("Month")
ax.tick_params(axis="x", rotation=60)
ax.legend(title="Region", frameon=False)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig1_revenue_trend.png")
plt.close(fig)

total_rev = orders["revenue"].sum()
print(f"Total gross revenue (completed orders, synthetic units): {total_rev:,.0f}")

# ------------------------------------------------------------------
# 2. Category mix (share of revenue)
# ------------------------------------------------------------------
cat_rev = orders.groupby("category")["revenue"].sum().sort_values(ascending=False)
cat_share = (cat_rev / cat_rev.sum() * 100).round(1)

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(cat_share.index[::-1], cat_share.values[::-1], color=ACCENT)
ax.set_title("MarketPulse — Revenue Share by Category")
ax.set_xlabel("% of total revenue")
for bar, val in zip(bars, cat_share.values[::-1]):
    ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2, f"{val}%", va="center")
fig.tight_layout()
fig.savefig(FIG_DIR / "fig2_category_mix.png")
plt.close(fig)

print("\nRevenue share by category:")
print(cat_share.to_string())

# ------------------------------------------------------------------
# 3. Seller leaderboard (top 10 overall)
# ------------------------------------------------------------------
seller_rev = (
    orders.groupby("seller_id")["revenue"].sum().reset_index()
    .merge(sellers[["seller_id", "seller_name", "region", "tier"]], on="seller_id")
    .sort_values("revenue", ascending=False)
    .head(10)
)

fig, ax = plt.subplots(figsize=(9, 5))
colors = {"Platinum": "#7c3aed", "Gold": "#d97706", "Silver": "#64748b", "Bronze": "#92400e"}
bar_colors = [colors[t] for t in seller_rev["tier"]]
ax.barh(seller_rev["seller_name"][::-1], seller_rev["revenue"][::-1], color=bar_colors[::-1])
ax.set_title("MarketPulse — Top 10 Sellers by Revenue (all regions)")
ax.set_xlabel("Revenue (synthetic currency units)")
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
ax.legend(handles, colors.keys(), title="Tier", frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig(FIG_DIR / "fig3_seller_leaderboard.png")
plt.close(fig)

print("\nTop seller:", seller_rev.iloc[0]["seller_name"],
      f"({seller_rev.iloc[0]['region']}, {seller_rev.iloc[0]['tier']})",
      f"- {seller_rev.iloc[0]['revenue']:,.0f}")

# ------------------------------------------------------------------
# 4. Anomaly investigation — weekly orders, Mexico / Fashion vs its own
#    trailing 8-week average, with the flagged drop window highlighted.
# ------------------------------------------------------------------
segment = orders[(orders["region"] == "Mexico") & (orders["category"] == "Fashion")]
weekly = segment.groupby("week_start").size().rename("orders").reset_index()
weekly = weekly.sort_values("week_start")
weekly["rolling_avg_8wk"] = weekly["orders"].rolling(8, min_periods=4).mean()

ANOMALY_START = pd.Timestamp("2026-04-06")
ANOMALY_END = pd.Timestamp("2026-05-10")

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(weekly["week_start"], weekly["orders"], color=ACCENT, linewidth=1.8, label="Weekly orders")
ax.plot(weekly["week_start"], weekly["rolling_avg_8wk"], color=MUTED, linestyle="--",
        linewidth=1.4, label="Trailing 8-week average")
ax.axvspan(ANOMALY_START, ANOMALY_END, color=ALERT, alpha=0.15,
           label="Flagged window (z-score < -2)")
ax.set_title("MarketPulse — Mexico / Fashion: Weekly Orders vs. Trailing Average")
ax.set_ylabel("Orders per week")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig4_anomaly_mexico_fashion.png")
plt.close(fig)

drop_week_orders = weekly[weekly["week_start"] == "2026-04-06"]["orders"].values
baseline = weekly[weekly["week_start"] < ANOMALY_START]["orders"].tail(8).mean()
print(f"\nMexico/Fashion — 8-week baseline before incident: {baseline:.1f} orders/week")
if len(drop_week_orders):
    drop_pct = 100 * (1 - drop_week_orders[0] / baseline)
    print(f"Mexico/Fashion — orders in flagged week: {drop_week_orders[0]} "
          f"({drop_pct:.0f}% below baseline)")

# ------------------------------------------------------------------
# 5. Cancellation rate — confirms this is an operational incident, not
#    just a seasonal demand dip (the signal that separates it from the
#    Dec-29 holiday-reversion cluster the SQL detector also flags).
# ------------------------------------------------------------------
all_orders["month"] = all_orders["order_date"].dt.to_period("M").astype(str)
cancel_mx_fashion = (
    all_orders[(all_orders["region"] == "Mexico") & (all_orders["category"] == "Fashion")]
    .groupby("month")
    .agg(total=("order_id", "count"), cancelled=("was_cancelled", "sum"))
)
cancel_mx_fashion["cancel_rate_pct"] = (
    100 * cancel_mx_fashion["cancelled"] / cancel_mx_fashion["total"]
).round(1)

fig, ax = plt.subplots(figsize=(10, 4.5))
colors_bar = [ALERT if m == "2026-04" else MUTED for m in cancel_mx_fashion.index]
ax.bar(cancel_mx_fashion.index, cancel_mx_fashion["cancel_rate_pct"], color=colors_bar)
ax.axhline(6, color="black", linestyle=":", linewidth=1, label="Baseline cancellation rate (~6%)")
ax.set_title("MarketPulse — Mexico / Fashion: Monthly Cancellation Rate")
ax.set_ylabel("Cancellation rate (%)")
ax.tick_params(axis="x", rotation=60)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig5_cancellation_rate.png")
plt.close(fig)

print("\nMexico/Fashion monthly cancellation rate (%):")
print(cancel_mx_fashion["cancel_rate_pct"].to_string())

print("\nDone. Figures written to", FIG_DIR)
