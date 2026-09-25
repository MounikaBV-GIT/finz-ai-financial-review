
import pandas as pd

from django.shortcuts import render,get_object_or_404, redirect
from .models import Transaction

from django.views.decorators.http import require_POST
from django.contrib import messages
from collections import defaultdict
from decimal import Decimal
from django.db.models import Sum , Q
from django.db.models.functions import TruncMonth
from calendar import month_name
from django.conf import settings
from django.http import HttpResponse
from .ai_service import test_groq_connection
import logging
from .ai_service import categorize_transaction_ai
from .analyst_service import ask_financial_analyst

def test_groq_config(request):
    if settings.GROQ_API_KEY:
        return HttpResponse("Groq API key is loaded!")
    return HttpResponse("Groq API key is missing!")


CATEGORIES = [
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


def categorize_transaction(description, counterparty):
    text = f"{description} {counterparty}".lower()

    # Revenue
    if any(word in text for word in [
        "sales", "customer payment", "catering",
        "payout", "deposit"
    ]):
        return "Revenue", 0.90

    # Payroll
    elif any(word in text for word in [
        "payroll", "salary", "wages"
    ]):
        return "Payroll", 0.95

    # Cost of Goods Sold
    elif any(word in text for word in [
        "food inventory", "beverage inventory",
        "food purchase", "ingredient"
    ]):
        return "Cost of Goods Sold", 0.92

    # Equipment / Capital Expenditure
    elif any(word in text for word in [
        "equipment purchase", "new oven",
        "capital expenditure"
    ]):
        return "Equipment / Capital Expenditure", 0.90

    # Loan Repayment
    elif any(word in text for word in [
        "loan repayment", "loan payment",
        "loan principal"
    ]):
        return "Loan Repayment", 0.90

    # Owner Distribution
    elif any(word in text for word in [
        "owner distribution", "owner draw"
    ]):
        return "Owner Distribution", 0.90

    # Taxes / Fees
    elif any(word in text for word in [
        "sales tax", "tax payment", "tax remittance"
    ]):
        return "Taxes / Fees", 0.90

    # Operating Expenses
    elif any(word in text for word in [
        "rent", "insurance", "utilities",
        "electric", "water", "internet",
        "phone", "subscription", "software",
        "bookkeeping", "accounting",
        "packaging", "disposable", "commission",
        "delivery platform", "repair", "maintenance",
        "marketing", "advertising", "cleaning"
    ]):
        return "Operating Expenses", 0.85

    # Uncertain transactions
    return "Other / Needs Review", 0.30

def upload_transactions(request):
    context = {}

    if request.method == "POST":
        file = request.FILES.get("file")

        if file:
            try:
                df = pd.read_excel(file)
                df = df.fillna("")

                saved_count = 0

                for _, row in df.iterrows():

                    transaction_id = str(
                        row["Transaction ID"]
                    ).strip()

                    # Skip existing transactions
                    if Transaction.objects.filter(
                        transaction_id=transaction_id
                    ).exists():
                        continue

                    Transaction.objects.create(
                        transaction_id=transaction_id,
                        date=pd.to_datetime(
                            row["Date"]
                        ).date(),
                        description=str(row["Description"]),
                        counterparty=str(row["Counterparty"]),
                        amount=float(
                            str(row["Amount"]).replace("$", "").replace(",", "")
                        ),
                        method=str(row["Method"])
                    )

                    saved_count += 1

                context["message"] = (
                    f"{saved_count} transactions saved successfully!"
                )

            except Exception as e:
                context["error"] = str(e)

    # Fetch transactions from database
    transactions = Transaction.objects.all().order_by("date")

    context["transactions"] = transactions
    context["total"] = transactions.count()
    # Pass categories to HTML template
    context["categories"] = CATEGORIES

    return render(
        request,
        "finance/upload.html",
        context
    )



@require_POST
def update_category(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    category = request.POST.get("category")

    if category not in CATEGORIES:
        return redirect("upload_transactions")

    transaction.category = category
    transaction.needs_review = (
        category == "Other / Needs Review"
    )

    transaction.confidence = None
    transaction.ai_reason = ""

    transaction.save(
        update_fields=[
            "category",
            "confidence",
            "ai_reason",
            "needs_review"
        ]
    )

    return redirect("upload_transactions")



@require_POST
def auto_categorize(request):
    transactions = Transaction.objects.filter(category="")

    updated_count = 0

    for transaction in transactions:
        category, confidence = categorize_transaction(
            transaction.description,
            transaction.counterparty
        )

        transaction.category = category
        transaction.confidence = confidence
        transaction.needs_review = (
            category == "Other / Needs Review"
            or confidence < 0.70
        )

        transaction.save(update_fields=[
            "category",
            "confidence",
            "needs_review"
        ])

        updated_count += 1

    messages.success(
        request,
        f"{updated_count} transactions categorized."
    )

    return redirect("upload_transactions")



def profit_loss(request):
    transactions = Transaction.objects.all().order_by("date")

    monthly_data = defaultdict(lambda: {
        "revenue": Decimal("0.00"),
        "cogs": Decimal("0.00"),
        "operating_expenses": Decimal("0.00"),
        "taxes_fees": Decimal("0.00"),
        "review": Decimal("0.00"),
    })

    for transaction in transactions:

        month_key = (
            transaction.date.year,
            transaction.date.month
        )

        amount = transaction.amount
        category = transaction.category

        if category == "Revenue" and amount > 0:
            monthly_data[month_key]["revenue"] += amount

        elif category == "Cost of Goods Sold":
            monthly_data[month_key]["cogs"] += abs(amount)

        elif category in ["Operating Expenses", "Payroll"]:
            monthly_data[month_key]["operating_expenses"] += abs(amount)

        elif category == "Taxes / Fees":
            monthly_data[month_key]["taxes_fees"] += abs(amount)

        elif category in ["", "Other / Needs Review"]:
            monthly_data[month_key]["review"] += abs(amount)


    report = []

    sorted_months = sorted(monthly_data.items())

    for index, ((year, month), data) in enumerate(sorted_months):

        gross_profit = (
            data["revenue"] - data["cogs"]
        )

        net_operating_profit = (
            gross_profit
            - data["operating_expenses"]
        )

        net_profit = (
            net_operating_profit
            - data["taxes_fees"]
        )

        # -----------------------------
        # Month-over-month variance
        # -----------------------------

        if index > 0:

            previous_data = sorted_months[index - 1][1]

            previous_gross_profit = (
                previous_data["revenue"]
                - previous_data["cogs"]
            )

            previous_operating_profit = (
                previous_gross_profit
                - previous_data["operating_expenses"]
            )

            previous_net_profit = (
                previous_operating_profit
                - previous_data["taxes_fees"]
            )

            revenue_variance = (
                data["revenue"]
                - previous_data["revenue"]
            )

            expense_variance = (
                (
                    data["cogs"]
                    + data["operating_expenses"]
                    + data["taxes_fees"]
                )
                -
                (
                    previous_data["cogs"]
                    + previous_data["operating_expenses"]
                    + previous_data["taxes_fees"]
                )
            )

            net_profit_variance = (
                net_profit - previous_net_profit
            )

            # -----------------------------
            # Find main category drivers
            # -----------------------------

            category_changes = []

            categories = [
                "Cost of Goods Sold",
                "Operating Expenses",
                "Payroll",
                "Taxes / Fees",
            ]

            for category in categories:

                current_total = Decimal("0.00")
                previous_total = Decimal("0.00")

                for transaction in transactions:

                    if transaction.category != category:
                        continue

                    if (
                        transaction.date.year == year
                        and transaction.date.month == month
                    ):
                        current_total += abs(
                            transaction.amount
                        )

                    previous_year, previous_month = (
                        sorted_months[index - 1][0]
                    )

                    if (
                        transaction.date.year == previous_year
                        and transaction.date.month == previous_month
                    ):
                        previous_total += abs(
                            transaction.amount
                        )

                change = current_total - previous_total

                if change != 0:
                    category_changes.append({
                        "category": category,
                        "change": change,
                    })

            category_changes.sort(
                key=lambda x: abs(x["change"]),
                reverse=True
            )

            drivers = category_changes[:3]

        else:

            revenue_variance = None
            expense_variance = None
            net_profit_variance = None
            drivers = []


        report.append({

            "month": f"{month_name[month]} {year}",

            "revenue": data["revenue"],
            "cogs": data["cogs"],
            "operating_expenses": data["operating_expenses"],
            "taxes_fees": data["taxes_fees"],
            "review": data["review"],

            "gross_profit": gross_profit,
            "net_operating_profit": net_operating_profit,
            "net_profit": net_profit,

            "revenue_variance": revenue_variance,
            "expense_variance": expense_variance,
            "net_profit_variance": net_profit_variance,

            "drivers": drivers,
        })


    return render(
        request,
        "finance/profit_loss.html",
        {
            "report": report
        }
    )


def dashboard(request):
    transactions = Transaction.objects.all()

    # Total Revenue
    total_revenue = transactions.filter(
        category="Revenue",
        amount__gt=0
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Cost of Goods Sold
    cogs = transactions.filter(
        category="Cost of Goods Sold"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Operating Expenses, including Payroll
    operating_expenses = transactions.filter(
        category__in=["Operating Expenses", "Payroll"]
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Taxes and Fees
    taxes_fees = transactions.filter(
        category="Taxes / Fees"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    total_expenses = (
        abs(cogs)
        + abs(operating_expenses)
        + abs(taxes_fees)
    )

    net_profit = total_revenue - total_expenses

    # Transactions Needing Review
    review_count = transactions.filter(
        Q(category="") |
        Q(category="Other / Needs Review") |
        Q(needs_review=True)
    ).distinct().count()

    # Monthly Revenue and Expenses
    monthly_data = defaultdict(lambda: {
        "revenue": Decimal("0.00"),
        "expenses": Decimal("0.00"),
    })

    for transaction in transactions.order_by("date"):
        month_key = (
            transaction.date.year,
            transaction.date.month
        )

        amount = transaction.amount
        category = transaction.category

        if category == "Revenue" and amount > 0:
            monthly_data[month_key]["revenue"] += amount

        elif category in [
            "Cost of Goods Sold",
            "Operating Expenses",
            "Payroll",
            "Taxes / Fees"
        ]:
            monthly_data[month_key]["expenses"] += abs(amount)

    # Prepare chart data in chronological order
    monthly_labels = []
    monthly_revenue = []
    monthly_expenses = []

    for (year, month), data in sorted(monthly_data.items()):
        monthly_labels.append(
            f"{month_name[month]} {year}"
        )

        monthly_revenue.append(float(data["revenue"]))
        monthly_expenses.append(float(data["expenses"]))

    context = {
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "review_count": review_count,

        # Chart data
        "monthly_labels": monthly_labels,
        "monthly_revenue": monthly_revenue,
        "monthly_expenses": monthly_expenses,
    }

    return render(
        request,
        "finance/dashboard.html",
        context
    )




logger = logging.getLogger(__name__)



def test_ai_categorization(request):
    try:
        result = categorize_transaction_ai(
            description="Rent",
            counterparty="Landlord"
        )

        return HttpResponse(
            f"Category: {result['category']}<br>"
            f"Confidence: {result['confidence']}<br>"
            f"Reason: {result['reason']}<br>"
            f"Needs Review: {result['needs_review']}"
        )

    except Exception:
        logger.exception("AI categorization test failed")

        return HttpResponse(
            "AI categorization failed. Check the Django terminal "
            "for the error details.",
            status=500
        )
@require_POST
def ai_auto_categorize(request):
    transactions = Transaction.objects.filter(category="")[:5]

    if not transactions.exists():
        messages.info(request, "No uncategorized transactions found.")
        return redirect("/")

    success_count = 0
    review_count = 0
    error_count = 0

    for transaction in transactions:
        try:
            result = categorize_transaction_ai(
                transaction.description,
                transaction.counterparty
            )

            transaction.category = result["category"]
            transaction.confidence = result["confidence"]
            transaction.ai_reason = result["reason"]
            transaction.needs_review = result["needs_review"]

            transaction.save(
                update_fields=[
                    "category",
                    "confidence",
                    "ai_reason",
                    "needs_review"
                ]
            )

            success_count += 1

            if result["needs_review"]:
                review_count += 1

        except Exception as e:
            error_count += 1
            print(
                f"AI categorization failed for "
                f"{transaction.transaction_id}: {e}"
            )

    messages.success(
        request,
        f"AI categorized {success_count} transactions. "
        f"{review_count} need review. "
        f"{error_count} failed."
    )

    return redirect("/")
def financial_analyst(request):

    answer = None
    evidence = []
    question = ""

    if request.method == "POST":

        question = request.POST.get("question", "").strip()

        if question:

            transactions = Transaction.objects.all()

            # -----------------------------
            # Category totals
            # -----------------------------

            category_totals = {}

            for transaction in transactions:

                category = (
                    transaction.category
                    or "Uncategorized"
                )

                if category not in category_totals:
                    category_totals[category] = Decimal("0.00")

                category_totals[category] += abs(
                    transaction.amount
                )

            # -----------------------------
            # Monthly financial summary
            # -----------------------------

            monthly_data = defaultdict(lambda: {
                "revenue": Decimal("0.00"),
                "expenses": Decimal("0.00"),
                "net_profit": Decimal("0.00"),
            })

            for transaction in transactions:

                month_key = (
                    transaction.date.year,
                    transaction.date.month
                )

                if (
                    transaction.category == "Revenue"
                    and transaction.amount > 0
                ):
                    monthly_data[month_key]["revenue"] += (
                        transaction.amount
                    )

                elif transaction.category in [
                    "Cost of Goods Sold",
                    "Operating Expenses",
                    "Payroll",
                    "Taxes / Fees",
                ]:
                    monthly_data[month_key]["expenses"] += abs(
                        transaction.amount
                    )

            for month_key, data in monthly_data.items():

                data["net_profit"] = (
                    data["revenue"]
                    - data["expenses"]
                )

            # -----------------------------
            # Find relevant transactions
            # -----------------------------

            question_words = question.lower().split()

            relevant_transactions = []

            for transaction in transactions:

                searchable_text = (
                    f"{transaction.transaction_id} "
                    f"{transaction.description} "
                    f"{transaction.counterparty} "
                    f"{transaction.category}"
                ).lower()

                if any(
                    word in searchable_text
                    for word in question_words
                    if len(word) > 3
                ):
                    relevant_transactions.append(transaction)

            relevant_transactions = (
                relevant_transactions[:15]
            )

            # -----------------------------
            # Build AI context
            # -----------------------------

            financial_context = {
                "category_totals": {
                    key: float(value)
                    for key, value in category_totals.items()
                },

                "monthly_summary": {
                    f"{month_name[month]} {year}": {
                        "revenue": float(data["revenue"]),
                        "expenses": float(data["expenses"]),
                        "net_profit": float(data["net_profit"]),
                    }
                    for (year, month), data
                    in sorted(monthly_data.items())
                },

                "relevant_transactions": [
                    {
                        "transaction_id": t.transaction_id,
                        "date": str(t.date),
                        "description": t.description,
                        "counterparty": t.counterparty,
                        "amount": float(t.amount),
                        "category": t.category,
                    }
                    for t in relevant_transactions
                ],
            }

            try:

                result = ask_financial_analyst(
                    question,
                    financial_context
                )

                answer = result["answer"]
                evidence = result["evidence"]

            except Exception as e:

                answer = (
                    f"Unable to get AI analysis: {str(e)}"
                )

    return render(
        request,
        "finance/financial_analyst.html",
        {
            "question": question,
            "answer": answer,
            "evidence": evidence,
        }
    )