"""
Claude-powered transaction categorizer.

Sends batches of transactions to Claude and receives back clean,
user-friendly category labels.
"""

import json
import anthropic
from config import ANTHROPIC_API_KEY

CATEGORIES = [
    "Groceries",
    "Dining & Restaurants",
    "Transport",
    "Utilities & Bills",
    "Subscriptions & Streaming",
    "Shopping & Retail",
    "Healthcare",
    "Entertainment",
    "Travel",
    "Personal Care",
    "Income / Transfer",
    "Other",
]

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_SYSTEM_PROMPT = (
    "You are a personal finance categorizer. "
    "Given a list of bank/PayPal transactions, assign each one exactly one category "
    f"from this list: {CATEGORIES}. "
    "Respond ONLY with a valid JSON object mapping the transaction's string id to its category. "
    'Example: {"0": "Groceries", "1": "Dining & Restaurants"}'
)

_BATCH_SIZE = 50


def categorize_transactions(transactions: list[dict]) -> list[dict]:
    """
    Categorize a list of raw Plaid transactions using Claude.

    Each transaction dict must have at least: name, amount.
    Returns the same list with a "category_label" key added to each item.
    """
    enriched = list(transactions)  # shallow copy

    for batch_start in range(0, len(enriched), _BATCH_SIZE):
        batch = enriched[batch_start: batch_start + _BATCH_SIZE]
        payload = [
            {"id": str(i), "name": t.get("name", ""), "amount": t.get("amount", 0)}
            for i, t in enumerate(batch)
        ]

        message = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Categorize these transactions:\n{json.dumps(payload)}",
                }
            ],
        )

        raw = message.content[0].text.strip()
        # Strip markdown code fences if Claude wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        assignments: dict[str, str] = json.loads(raw)

        for i, txn in enumerate(batch):
            label = assignments.get(str(i), "Other")
            if label not in CATEGORIES:
                label = "Other"
            txn["category_label"] = label

    return enriched
