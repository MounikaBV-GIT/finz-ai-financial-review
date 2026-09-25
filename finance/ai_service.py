import json
from groq import Groq
from django.conf import settings


def get_groq_client():
    if not settings.GROQ_API_KEY:
        raise ValueError("Groq API key is missing.")

    return Groq(api_key=settings.GROQ_API_KEY)


def test_groq_connection():
    client = get_groq_client()

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": "Reply with only: Groq connection successful"
            }
        ],
        temperature=0,
        max_tokens=100,
    )

    return response.choices[0].message.content


def categorize_transaction_ai(description, counterparty):
    client = get_groq_client()

    categories = [
        "Revenue",
        "Cost of Goods Sold",
        "Payroll",
        "Operating Expenses",
        "Equipment / Capital Expenditure",
        "Loan Repayment",
        "Owner Distribution",
        "Taxes / Fees",
        "Other / Needs Review",
    ]

    prompt = f"""
    You are a financial transaction categorization assistant
    for a restaurant business.

    Categorize the transaction using only one category from
    this list:
    {categories}

    Transaction description: {description}
    Counterparty: {counterparty}

    Return ONLY valid JSON in this format:
    {{
        "category": "one category from the list",
        "confidence": 0.0,
        "reason": "short explanation"
    }}

    Confidence must be a number between 0 and 1.
    If the transaction is ambiguous, use
    "Other / Needs Review" and a low confidence score.
    Do not invent missing transaction details.
    """

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You categorize financial transactions. "
                    "Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        max_tokens=250,
        response_format={"type": "json_object"},
    )

    result = json.loads(
        response.choices[0].message.content
    )

    category = result.get("category")
    confidence = result.get("confidence")
    reason = result.get("reason", "")

    # Validate the AI response
    if category not in categories:
        category = "Other / Needs Review"
        confidence = 0.0
        reason = "AI returned an invalid category."

    try:
        confidence = float(confidence)

        if not 0 <= confidence <= 1:
            confidence = 0.0
            category = "Other / Needs Review"
            reason = "AI returned an invalid confidence score."

    except (TypeError, ValueError):
        confidence = 0.0
        category = "Other / Needs Review"
        reason = "AI returned an invalid confidence score."

    # Flag uncertain predictions for human review
    needs_review = (
        confidence < 0.75
        or category == "Other / Needs Review"
    )

    return {
        "category": category,
        "confidence": confidence,
        "reason": reason,
        "needs_review": needs_review,
    }