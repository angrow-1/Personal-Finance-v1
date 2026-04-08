"""
Plaid API wrapper.

Fetches transactions for each linked account (Bank 1, Bank 2, PayPal)
for a given date range and returns them as plain dicts.
"""

import requests
from config import PLAID_CLIENT_ID, PLAID_SECRET, PLAID_HOST, ACCESS_TOKENS


def _post(endpoint: str, payload: dict) -> dict:
    url = f"{PLAID_HOST}{endpoint}"
    payload = {**payload, "client_id": PLAID_CLIENT_ID, "secret": PLAID_SECRET}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def get_transactions(access_token: str, start_date: str, end_date: str) -> list[dict]:
    """
    Fetch all transactions for one account between start_date and end_date.

    Handles Plaid's pagination (offset-based) automatically.
    Returns a list of raw Plaid transaction dicts.

    Args:
        access_token: Plaid access token for the account.
        start_date: ISO date string "YYYY-MM-DD".
        end_date: ISO date string "YYYY-MM-DD".
    """
    all_transactions: list[dict] = []
    offset = 0
    count = 500  # max per request

    while True:
        data = _post("/transactions/get", {
            "access_token": access_token,
            "start_date": start_date,
            "end_date": end_date,
            "options": {"count": count, "offset": offset},
        })
        transactions = data.get("transactions", [])
        all_transactions.extend(transactions)
        total = data.get("total_transactions", 0)
        offset += len(transactions)
        if offset >= total or not transactions:
            break

    return all_transactions


def fetch_all_accounts(start_date: str, end_date: str) -> dict[str, list[dict]]:
    """
    Fetch transactions from all configured accounts.

    Returns:
        Dict mapping account name → list of raw Plaid transaction dicts.
        Example: {"Bank 1": [...], "Bank 2": [...], "PayPal": [...]}
    """
    result: dict[str, list[dict]] = {}
    for account_name, token in ACCESS_TOKENS.items():
        print(f"  Fetching transactions for {account_name}...")
        txns = get_transactions(token, start_date, end_date)
        result[account_name] = txns
        print(f"    → {len(txns)} transactions found")
    return result
