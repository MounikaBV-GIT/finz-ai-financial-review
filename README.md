# Finz - AI Financial Review Application

Finz is an AI-powered financial review application built for a restaurant business. It helps users upload financial transactions, categorize transactions using AI, review and correct classifications, analyze Profit & Loss results, understand monthly financial variances, and ask financial questions using an AI financial analyst.

## Live Application

https://finz-ai-financial-review-msif.onrender.com/

## Video Walkthrough

https://drive.google.com/file/d/1Ti7gI_W0qKs0VMC3TQxpRnPZ-IXmj7FO/view?usp=sharing

## Features

### 1. Financial Transaction Upload

- Upload financial transactions using Excel files.
- Supports `.xlsx` and `.xls` files.
- Transactions are stored in the Django database.
- Displays transaction ID, date, description, counterparty, amount, payment method, and category.

### 2. AI Transaction Categorization

The application uses the Groq API with the `openai/gpt-oss-120b` model to categorize financial transactions.

Supported categories include:

- Revenue
- Cost of Goods Sold
- Payroll
- Operating Expenses
- Equipment / Capital Expenditure
- Loan Repayment
- Owner Distribution
- Taxes / Fees
- Other / Needs Review

For AI-generated classifications, the application also stores:

- AI confidence score
- AI reasoning
- Review status

Transactions with ambiguous or low-confidence classifications can be flagged for review.

### 3. Manual Classification Correction

Users can manually change the category assigned to a transaction.

When a category is manually updated, the previous AI confidence and AI reasoning are cleared so that the transaction reflects the user's manual classification.

### 4. Financial Dashboard

The dashboard provides a high-level financial summary including:

- Total Revenue
- Total Expenses
- Net Profit
- Transactions requiring review

### 5. Profit & Loss Analysis

The Profit & Loss section provides monthly financial analysis including:

- Revenue
- Cost of Goods Sold
- Operating Expenses
- Taxes / Fees
- Gross Profit
- Net Operating Profit
- Net Profit

### 6. Monthly Variance Analysis

The application compares financial results between consecutive months.

The analysis includes:

- Revenue variance
- Expense variance
- Net profit variance
- Major categories contributing to changes

This helps identify the financial categories responsible for significant month-to-month changes.

### 7. AI Financial Analyst

The application provides a conversational financial analyst powered by the Groq API.

Users can ask questions about the financial data using natural language.

For example:

> What was the total revenue?

The AI analyst uses structured financial information from the application and provides:

- A concise answer
- Supporting evidence from the financial data

The analyst is instructed not to invent financial information that is not present in the provided data.

---

## Technology Stack

### Backend

- Python
- Django
- Django ORM

### Frontend

- HTML
- CSS
- Django Templates

### Database

- SQLite

### Data Processing

- Pandas
- OpenPyXL

### AI

- Groq API
- `openai/gpt-oss-120b`

### Deployment

- Render
- Gunicorn
- WhiteNoise

---

## Project Structure

```text
Finz_Project/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── ...
│
├── finance/
│   ├── migrations/
│   ├── templates/
│   │   └── finance/
│   ├── ai_service.py
│   ├── analyst_service.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
│
├── static/
│   └── css/
│
├── manage.py
├── requirements.txt
├── README.md
└── .gitignore