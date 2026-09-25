import json
from groq import Groq
from django.conf import settings


def get_groq_client():
    if not settings.GROQ_API_KEY:
        raise ValueError("Groq API key is missing.")

    return Groq(api_key=settings.GROQ_API_KEY)


def ask_financial_analyst(question, financial_context):
    client = get_groq_client()

    prompt = f"""
You are an AI financial analyst for a restaurant business.

Answer the user's financial question using ONLY the financial
data provided below.

Do not invent numbers or transactions.

If the data does not contain enough information, clearly say so.

User question:
{question}

Financial data:
{financial_context}

Return ONLY valid JSON in this format:

{{
    "answer": "clear and concise answer",
    "evidence": [
        "specific fact or transaction from the provided data"
    ]
}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a financial analyst. "
                    "Use only the supplied financial data. "
                    "Return valid JSON only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    result = json.loads(
        response.choices[0].message.content
    )

    return {
        "answer": result.get(
            "answer",
            "Unable to generate an answer."
        ),
        "evidence": result.get(
            "evidence",
            []
        ),
    }