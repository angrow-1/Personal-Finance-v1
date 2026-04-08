import os
from dotenv import load_dotenv

load_dotenv()

PLAID_CLIENT_ID = os.environ["PLAID_CLIENT_ID"]
PLAID_SECRET = os.environ["PLAID_SECRET"]
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Map friendly account names to their Plaid access tokens.
# Tokens are populated by running setup_accounts.py once per account.
ACCESS_TOKENS: dict[str, str] = {
    "Bank 1": os.environ["PLAID_ACCESS_TOKEN_BANK1"],
    "Bank 2": os.environ["PLAID_ACCESS_TOKEN_BANK2"],
    "PayPal": os.environ["PLAID_ACCESS_TOKEN_PAYPAL"],
}

PLAID_HOST_MAP = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}
PLAID_HOST = PLAID_HOST_MAP[PLAID_ENV]
