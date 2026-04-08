"""
Plaid API wrapper using the official plaid-python SDK.

Fetches transactions for each linked account (Bank 1, Bank 2, PayPal)
for a given date range and returns them as plain dicts.
"""

import datetime
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

from config import PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV, ACCESS_TOKENS

_ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}


def _build_client() -> plaid_api.PlaidApi:
    configuration = plaid.Configuration(
        host=_ENV_MAP.get(PLAID_ENV, plaid.Environment.Sandbox),
        api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET},
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


_client = _build_client()


def get_transactions(
    access_token: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> list[dict]:
    """
    Fetch all settled transactions for one account between start_date and end_date.

    Handles Plaid's offset-based pagination automatically.
    Returns a list of transaction dicts (converted from SDK model objects).

    Args:
        access_token: Plaid access token for the account.
        start_date: First day of the period (datetime.date).
        end_date: Last day of the period (datetime.date).
    """
    all_transactions: list[dict] = []

    # Initial request
    request = TransactionsGetRequest(
        access_token=access_token,
        start_date=start_date,
        end_date=end_date,
        options=TransactionsGetRequestOptions(count=500, offset=0),
    )
    response = _client.transactions_get(request)
    total = response["total_transactions"]
    all_transactions.extend(response["transactions"])

    # Paginate until all transactions are fetched
    while len(all_transactions) < total:
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(
                count=500,
                offset=len(all_transactions),
            ),
        )
        response = _client.transactions_get(request)
        all_transactions.extend(response["transactions"])

    # Convert SDK model objects to plain dicts and filter out pending
    result = []
    for txn in all_transactions:
        t = txn.to_dict() if hasattr(txn, "to_dict") else dict(txn)
        if t.get("pending"):
            continue
        # Ensure amount is a plain float (Plaid: positive = debit/spend)
        t["amount"] = float(t.get("amount", 0))
        t["date"] = str(t.get("date", ""))
        result.append(t)

    return result


def fetch_all_accounts(
    start_date: datetime.date,
    end_date: datetime.date,
) -> dict[str, list[dict]]:
    """
    Fetch transactions from all configured accounts.

    Args:
        start_date: First day of the period.
        end_date: Last day of the period.

    Returns:
        Dict mapping account name → list of transaction dicts.
        Example: {"Bank 1": [...], "Bank 2": [...], "PayPal": [...]}
    """
    result: dict[str, list[dict]] = {}
    for account_name, token in ACCESS_TOKENS.items():
        print(f"  Fetching transactions for {account_name}...")
        txns = get_transactions(token, start_date, end_date)
        result[account_name] = txns
        print(f"    → {len(txns)} transactions found")
    return result
