import enum


class AccountType(enum.StrEnum):
    checking = "checking"
    savings = "savings"
    credit = "credit"
    cash = "cash"
    investment = "investment"


class CategoryType(enum.StrEnum):
    expense = "expense"
    income = "income"
    transfer = "transfer"


class BudgetPeriod(enum.StrEnum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    annually = "annually"
