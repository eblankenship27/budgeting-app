from faker import Faker
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Account,
    AccountType,
    Budget,
    BudgetPeriod,
    Category,
    CategoryType,
    Transaction,
    User,
)

fake = Faker()

DEV_USER_EMAIL = "fluffy2578@gmail.com"

account_types = [
    "checking",
    "savings",
    "investment",
]

def main() -> None:
    
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.email == DEV_USER_EMAIL)).scalar_one_or_none()
        if user is not None:
            db.delete(user)
            db.flush()
        
        user = User(email=DEV_USER_EMAIL, username="devuser")
        db.add(user)
        db.flush()
        
        accounts = []
        for account_type in account_types:
            account = Account(
                user=user,
                name=account_type,
                type=AccountType(account_type),
                currency="USD",
                current_balance=fake.pydecimal(left_digits=4, right_digits=2, positive=True),
            )
            accounts.append(account)
            db.add(account)
            
        categories = [
            Category(
                user=user,
                name="Groceries",
                type=CategoryType.expense,
            ),
            Category(
                user=user,
                name="Rent",
                type=CategoryType.expense,
            ),
            Category(
                user=user,
                name="Dining",
                type=CategoryType.expense,
            ),
            Category(
                user=user,
                name="Personal",
                type=CategoryType.expense,
            ),
            Category(
                user=user,
                name="Salary",
                type=CategoryType.income
            ),
            Category(
                user=user,
                name="Interest",
                type=CategoryType.income,
            )
        ]
        
        transactions = []
        
        for _i in range(100):
            amount = fake.pydecimal(left_digits=4, right_digits=2, positive=True)
            category = fake.random_element(categories)
            transaction = Transaction(
                user=user,
                account=fake.random_element(accounts),
                category=category,
                amount= -amount if category.type == CategoryType.expense else amount,
                transaction_date=fake.date_between(start_date="-6M", end_date="today"),
                description=fake.sentence(nb_words=4),
                merchant=fake.company(),
                is_pending=fake.boolean(10)
            )
            transactions.append(transaction)
            db.add(transaction)
            
        budgets = []
        
        for cat in categories:
            db.add(cat)
            if cat.type == CategoryType.expense:
                budget = Budget(
                    user=user,
                    category=cat,
                    amount=fake.pydecimal(left_digits=4, right_digits=2, positive=True),
                    period=BudgetPeriod.monthly,
                    start_date=fake.date_between(start_date="-6M", end_date="today")
                )
                budgets.append(budget)
                db.add(budget)
        
        
        db.commit() # with closes session but does not autocommit

        print("Seeded database:")
        print("  users:        1")
        print(f"  accounts:     {len(accounts)}")
        print(f"  categories:   {len(categories)}")
        print(f"  transactions: {len(transactions)}")
        print(f"  budgets:      {len(budgets)}")
    
if __name__ == "__main__":
    main()