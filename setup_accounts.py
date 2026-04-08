"""
One-time Plaid account linking script.

Run this script once per account (Bank 1, Bank 2, PayPal) to obtain
a Plaid access token, then add that token to your .env file.

Usage:
    python setup_accounts.py
"""

import webbrowser
import requests
from config import PLAID_CLIENT_ID, PLAID_SECRET, PLAID_HOST, PLAID_ENV

_PRODUCTS = ["transactions"]
_COUNTRY_CODES = ["US"]


def _post(endpoint: str, payload: dict) -> dict:
    url = f"{PLAID_HOST}{endpoint}"
    payload = {**payload, "client_id": PLAID_CLIENT_ID, "secret": PLAID_SECRET}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def create_link_token(user_id: str = "local-user") -> str:
    data = _post("/link/token/create", {
        "user": {"client_user_id": user_id},
        "client_name": "Personal Finance Analyzer",
        "products": _PRODUCTS,
        "country_codes": _COUNTRY_CODES,
        "language": "en",
    })
    return data["link_token"]


def exchange_public_token(public_token: str) -> str:
    data = _post("/item/public_token/exchange", {"public_token": public_token})
    return data["access_token"]


def main():
    print("=" * 60)
    print("Plaid Account Linking — Personal Finance Analyzer")
    print("=" * 60)
    print(f"Environment: {PLAID_ENV}\n")

    accounts = ["Bank 1", "Bank 2", "PayPal"]
    env_keys = {
        "Bank 1": "PLAID_ACCESS_TOKEN_BANK1",
        "Bank 2": "PLAID_ACCESS_TOKEN_BANK2",
        "PayPal": "PLAID_ACCESS_TOKEN_PAYPAL",
    }

    results: dict[str, str] = {}

    for account_name in accounts:
        print(f"\n--- Linking: {account_name} ---")
        input(f"Press ENTER to generate a link token for {account_name}...")

        link_token = create_link_token()
        print(f"\nLink token created: {link_token[:30]}...")

        if PLAID_ENV == "sandbox":
            # In sandbox, use Plaid's hosted Link UI
            link_url = f"https://cdn.plaid.com/link/v2/stable/link.html?isWebview=true&token={link_token}"
            print(f"\nOpen this URL in your browser to connect {account_name}:")
            print(f"\n  {link_url}\n")
            print("In sandbox mode, use these test credentials:")
            print("  Institution: Select any test institution (e.g. 'Plaid Test')")
            print("  Username: user_good")
            print("  Password: pass_good\n")
        else:
            link_url = f"https://cdn.plaid.com/link/v2/stable/link.html?isWebview=true&token={link_token}"
            print(f"\nOpen this URL in your browser to connect {account_name}:")
            print(f"\n  {link_url}\n")

        try:
            webbrowser.open(link_url)
        except Exception:
            pass  # headless environment

        public_token = input(
            "After completing the Plaid Link flow, paste the public_token here: "
        ).strip()

        if not public_token:
            print(f"Skipping {account_name} — no token provided.")
            continue

        access_token = exchange_public_token(public_token)
        results[account_name] = access_token
        print(f"\n✓ Access token obtained for {account_name}.")

    print("\n" + "=" * 60)
    print("Add the following lines to your .env file:")
    print("=" * 60)
    for account_name, token in results.items():
        key = env_keys[account_name]
        print(f"{key}={token}")

    if len(results) < len(accounts):
        missing = [a for a in accounts if a not in results]
        print(f"\nNote: Skipped accounts: {', '.join(missing)}")
        print("Re-run this script to link them later.")

    print("\nSetup complete. Run 'python main.py' to generate your first report.")


if __name__ == "__main__":
    main()
