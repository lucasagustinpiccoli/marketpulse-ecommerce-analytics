"""
MarketPulse — AI insight agent.

Takes the exact summary statistics the notebook computes (baseline order
volume, the drop, the cancellation-rate delta) and asks Claude to draft the
written incident summary a business stakeholder would actually read -
turning "here are six numbers" into "here's what happened and what to do
about it," the same way a real anomaly-detection dashboard pairs an alert
with a plain-language explanation instead of a bare chart.

This mirrors the real AI-augmented-analytics workflow (agent-orchestrated
automation via Claude Code) used elsewhere in this author's work, applied
here to a synthetic case instead of real client/employer data.

Setup:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-...

Run (uses this case study's real numbers by default):
    python ai_agent/insight_agent.py
    python ai_agent/insight_agent.py --model claude-sonnet-5-5

--------------------------------------------------------------------------
Sample output (hand-written example, NOT a live API call - included so the
shape of the output is visible without requiring a key to read this file):

    INCIDENT SUMMARY — Mexico / Fashion, week of 2026-04-06

    Weekly order volume for Fashion sellers in Mexico fell to 20 orders,
    75.3% below the trailing 8-week baseline of 80.9 orders/week, and stayed
    depressed for roughly five weeks. Critically, this was not a simple
    demand dip: the segment's cancellation rate roughly doubled over the
    same window (6.1% baseline to 12.3%), meaning orders were still being
    placed but increasingly failing to complete. That combination - volume
    down, cancellations up, isolated to one region x category - points to
    a fulfillment-side failure (most likely a carrier or logistics-partner
    issue) rather than a pricing or demand problem.

    Recommended action: route this alert directly to the Mexico fulfillment
    team with the cancellation-rate chart attached, and check carrier SLA
    logs for the same window before investigating demand-side causes.
--------------------------------------------------------------------------
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DB_PATH = HERE.parent / "data" / "marketpulse.db"

SYSTEM_PROMPT = (
    "You are a business intelligence analyst writing a short incident "
    "summary for a commercial operations stakeholder who has not seen the "
    "underlying data. Be concrete, cite the actual numbers you're given, "
    "state the most likely root cause and your confidence in it, and end "
    "with one specific recommended action. Keep it under 180 words. No "
    "preamble, no 'I hope this helps' - write only the summary itself."
)


def compute_stats() -> dict:
    """Recompute the exact numbers the notebook's section 4-5 report, so the
    agent is grounded in real output from this dataset, not invented data."""
    conn = sqlite3.connect(DB_PATH)
    orders = pd.read_sql_query(
        "SELECT * FROM orders WHERE was_cancelled = 0", conn, parse_dates=["order_date"]
    )
    all_orders = pd.read_sql_query("SELECT * FROM orders", conn, parse_dates=["order_date"])
    conn.close()

    orders["week_start"] = orders["order_date"].dt.to_period("W").dt.start_time
    segment = orders[(orders["region"] == "Mexico") & (orders["category"] == "Fashion")]
    weekly = segment.groupby("week_start").size().rename("orders").reset_index()
    weekly = weekly.sort_values("week_start")

    anomaly_start = pd.Timestamp("2026-04-06")
    baseline = weekly[weekly["week_start"] < anomaly_start]["orders"].tail(8).mean()
    drop_row = weekly[weekly["week_start"] == anomaly_start]
    drop_orders = int(drop_row["orders"].values[0]) if len(drop_row) else None
    drop_pct = round(100 * (1 - drop_orders / baseline), 1) if drop_orders else None

    all_orders["month"] = all_orders["order_date"].dt.to_period("M").astype(str)
    cancel = (
        all_orders[(all_orders["region"] == "Mexico") & (all_orders["category"] == "Fashion")]
        .groupby("month")
        .agg(total=("order_id", "count"), cancelled=("was_cancelled", "sum"))
    )
    cancel["rate"] = 100 * cancel["cancelled"] / cancel["total"]
    baseline_cancel_rate = round(cancel.loc[cancel.index < "2026-04", "rate"].mean(), 1)
    incident_cancel_rate = round(cancel.loc["2026-04", "rate"], 1) if "2026-04" in cancel.index else None

    return {
        "segment": "Mexico / Fashion",
        "incident_week": "2026-04-06",
        "baseline_orders_per_week": round(baseline, 1),
        "incident_week_orders": drop_orders,
        "drop_pct": drop_pct,
        "baseline_cancellation_rate_pct": baseline_cancel_rate,
        "incident_cancellation_rate_pct": incident_cancel_rate,
    }


def build_user_prompt(stats: dict) -> str:
    return (
        "Here is the anomaly-detection output for one segment of a "
        "marketplace business:\n\n"
        f"- Segment: {stats['segment']}\n"
        f"- Flagged week: {stats['incident_week']}\n"
        f"- Trailing 8-week baseline order volume: {stats['baseline_orders_per_week']} orders/week\n"
        f"- Orders in the flagged week: {stats['incident_week_orders']} "
        f"({stats['drop_pct']}% below baseline)\n"
        f"- Baseline cancellation rate for this segment: {stats['baseline_cancellation_rate_pct']}%\n"
        f"- Cancellation rate during the flagged month: {stats['incident_cancellation_rate_pct']}%\n\n"
        "Write the incident summary."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("---")[0])
    parser.add_argument("--model", default="claude-sonnet-5-5")
    parser.add_argument("--max-tokens", type=int, default=400)
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Export it first:\n"
              "    export ANTHROPIC_API_KEY=sk-...\n"
              "See this file's module docstring for a sample of the expected output.",
              file=sys.stderr)
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("Missing dependency. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    stats = compute_stats()
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=args.model,
        max_tokens=args.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(stats)}],
    )
    print(response.content[0].text)


if __name__ == "__main__":
    main()
