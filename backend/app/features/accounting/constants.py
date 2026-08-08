"""System-controlled Chart of Accounts constants."""

ACCOUNT_CASH_CODE = "1000"
ACCOUNT_LOANS_RECEIVABLE_CODE = "1100"
ACCOUNT_CUSTOMER_CREDIT_CODE = "2000"
ACCOUNT_INTEREST_INCOME_CODE = "4000"

SYSTEM_ACCOUNTS = [
    {
        "code": ACCOUNT_CASH_CODE,
        "name": "Cash",
        "account_type": "asset",
        "normal_balance": "debit",
        "description": "Primary cash account for disbursements and receipts",
    },
    {
        "code": ACCOUNT_LOANS_RECEIVABLE_CODE,
        "name": "Loans Receivable",
        "account_type": "asset",
        "normal_balance": "debit",
        "description": "Outstanding loan principal owed by borrowers",
    },
    {
        "code": ACCOUNT_CUSTOMER_CREDIT_CODE,
        "name": "Customer Credit",
        "account_type": "liability",
        "normal_balance": "credit",
        "description": "Unapplied credit balances held for borrowers",
    },
    {
        "code": ACCOUNT_INTEREST_INCOME_CODE,
        "name": "Interest Income",
        "account_type": "income",
        "normal_balance": "credit",
        "description": "Earned interest income on loans",
    },
]
