import enum

class AccountType(str, enum.Enum):
    checking = "checking"
    savings = "savings"
    credit = "credit"
    cash = "cash"
    investment = "investment"
    
class CategoryType(str, enum.Enum):
    expense = "expense"
    income = "income"
    transfer = "transfer"
    
class BudgetPeriod(str, enum.Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    annually = "annually"