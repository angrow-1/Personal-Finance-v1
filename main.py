"""
Personal Finance Analyzer — main entry point.

Fetches last month's transactions from all linked accounts,
categorizes them with Claude, saves a monthly summary, and
generates a PDF report.

Usage:
    python main.py                  # analyze previous calendar month
    python main.py --year 2025 --month 3   # analyze a specific month
"""

import argparse
import calendar
from datetime import date, timedelta

from plaid_client import fetch_all_accounts
from categorizer import categorize_transactions
from data_store import save_month, load_history
from report_generator import generate_report


def _previous_month(today: date) -> tuple[int, int]:
    first_of_this_month = today.replace(day=1)
    last_month = first_of_this_month - timedelta(days=1)
    return last_month.year, last_month.month


def _month_date_range(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def run(year: int | None = None, month: int | None = None) -> str:
    today = date.today()

    if year is None or month is None:
        year, month = _previous_month(today)

    month_label = f"{calendar.month_name[month]} {year}"
    start_date, end_date = _month_date_range(year, month)

    print(f"\n Personal Finance Analyzer")
    print(f"  Report period : {month_label}  ({start_date.isoformat()} → {end_date.isoformat()})")
    print(f"  Run date      : {today.isoformat()}\n")

    # Step 1 — Fetch transactions
    print("[1/4] Fetching transactions from Plaid...")
    transactions_by_account = fetch_all_accounts(start_date, end_date)
    total_txns = sum(len(v) for v in transactions_by_account.values())
    print(f"      Total transactions: {total_txns}\n")

    # Step 2 — Categorize with Claude
    print("[2/4] Categorizing transactions with Claude AI...")
    all_txns: list[dict] = []
    for txns in transactions_by_account.values():
        all_txns.extend(txns)

    enriched = categorize_transactions(all_txns)

    # Map enriched transactions back to their accounts by transaction id
    enriched_by_id = {t["transaction_id"]: t for t in enriched}
    for acct, txns in transactions_by_account.items():
        transactions_by_account[acct] = [
            enriched_by_id.get(t["transaction_id"], t) for t in txns
        ]
    print("      Categorization complete.\n")

    # Step 3 — Persist monthly summary
    print("[3/4] Saving monthly summary...")
    from collections import defaultdict
    by_category: dict[str, float] = defaultdict(float)
    by_account: dict[str, float] = {}
    total_spend = 0.0

    for acct, txns in transactions_by_account.items():
        acct_spend = sum(t.get("amount", 0) for t in txns if t.get("amount", 0) > 0)
        by_account[acct] = acct_spend
        for t in txns:
            if t.get("amount", 0) > 0:
                by_category[t.get("category_label", "Other")] += t["amount"]
        total_spend += acct_spend

    save_month(year, month, {
        "total": total_spend,
        "by_category": dict(by_category),
        "by_account": by_account,
    })
    history = load_history()
    print(f"      Summary saved ({len(history)} month(s) in history).\n")

    # Step 4 — Generate PDF
    print("[4/4] Generating PDF report...")
    pdf_path = generate_report(year, month, transactions_by_account, history)
    print(f"      Report saved to: {pdf_path}\n")

    print(f" Done!  Open {pdf_path} to view your report.\n")
    return pdf_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a monthly personal finance report.")
    parser.add_argument("--year", type=int, default=None, help="Report year (default: last month)")
    parser.add_argument("--month", type=int, default=None, help="Report month 1-12 (default: last month)")
    args = parser.parse_args()
    run(year=args.year, month=args.month)
