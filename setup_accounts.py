"""
One-time Plaid account linking script.

Run this script once per account (Bank 1, Bank 2, PayPal) to obtain
a Plaid access token, then add that token to your .env file.

In SANDBOX mode this script automatically generates test access tokens —
no browser or real bank credentials are needed.

In PRODUCTION mode it prints a Plaid Link URL for you to complete in a browser.

Usage:
    python setup_accounts.py
"""

import plaid
from plaid.api import plaid_api
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

from config import PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV

_ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "development": plaid.Environment.Development,
    "production": plaid.Environment.Production,
}

# Plaid sandbox institution IDs for testing
_SANDBOX_INSTITUTIONS = {
    "Bank 1": "ins_109508",   # First Platypus Bank
    "Bank 2": "ins_109511",   # Tartan Bank
    "PayPal": "ins_132243",   # PayPal (sandbox)
}

_ENV_KEYS = {
    "Bank 1": "PLAID_ACCESS_TOKEN_BANK1",
    "Bank 2": "PLAID_ACCESS_TOKEN_BANK2",
    "PayPal": "PLAID_ACCESS_TOKEN_PAYPAL",
}


def _build_client() -> plaid_api.PlaidApi:
    configuration = plaid.Configuration(
        host=_ENV_MAP.get(PLAID_ENV, plaid.Environment.Sandbox),
        api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET},
    )
    return plaid_api.PlaidApi(plaid.ApiClient(configuration))


def _sandbox_get_token(client: plaid_api.PlaidApi, account_name: str) -> str:
    """
    In sandbox mode: automatically create and exchange a public token
    without needing a browser or real credentials.
    """
    institution_id = _SANDBOX_INSTITUTIONS[account_name]

    # Create a sandbox public token for the test institution
    create_response = client.sandbox_public_token_create(
        SandboxPublicTokenCreateRequest(
            institution_id=institution_id,
            initial_products=[Products("transactions")],
        )
    )
    public_token = create_response["public_token"]

    # Exchange the public token for a permanent access token
    exchange_response = client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    return exchange_response["access_token"]


def _production_get_token(client: plaid_api.PlaidApi, account_name: str) -> str:
    """
    In production mode: create a Link token and walk the user through
    pasting back the public_token after completing the Plaid Link flow.
    """
    link_response = client.link_token_create(
        LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id="local-user"),
            client_name="Personal Finance Analyzer",
            products=[Products("transactions")],
            country_codes=[CountryCode("US")],
            language="en",
        )
    )
    link_token = link_response["link_token"]
    link_url = (
        f"https://cdn.plaid.com/link/v2/stable/link.html"
        f"?isWebview=true&token={link_token}"
    )

    print(f"\nOpen this URL in your browser to connect {account_name}:")
    print(f"\n  {link_url}\n")
    print("Complete the Plaid Link flow (log in to your bank).")

    public_token = input("Paste the public_token here: ").strip()
    if not public_token:
        raise ValueError(f"No public_token provided for {account_name}.")

    exchange_response = client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    return exchange_response["access_token"]


def main() -> None:
    print("=" * 60)
    print("Plaid Account Linking — Personal Finance Analyzer")
    print("=" * 60)
    print(f"Environment : {PLAID_ENV}")
    if PLAID_ENV == "sandbox":
        print("Mode        : SANDBOX (automatic — no browser needed)\n")
    else:
        print("Mode        : PRODUCTION (browser required)\n")

    client = _build_client()
    accounts = ["Bank 1", "Bank 2", "PayPal"]
    results: dict[str, str] = {}

    for account_name in accounts:
        print(f"Linking: {account_name}...")
        try:
            if PLAID_ENV == "sandbox":
                token = _sandbox_get_token(client, account_name)
            else:
                token = _production_get_token(client, account_name)
            results[account_name] = token
            print(f"  ✓ Token obtained for {account_name}\n")
        except Exception as exc:
            print(f"  ✗ Failed to link {account_name}: {exc}\n")

    print("=" * 60)
    print("Add the following lines to your .env file:")
    print("=" * 60)
    for account_name, token in results.items():
        print(f"{_ENV_KEYS[account_name]}={token}")

    if results:
        print("\nSetup complete. Run 'python main.py' to generate your first report.")
    else:
        print("\nNo accounts were linked. Check your PLAID_CLIENT_ID and PLAID_SECRET.")


if __name__ == "__main__":
    main()
