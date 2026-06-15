# Data Models

## Users

- userId
- email
- createdAt

## Accounts

- accountId
- userId
- type (enum)
- current balance
- currency (enum)
- is active
- createdAt

## Transactions

- transactionId
- userId
- accountId
- categoryId
- transaction date
- amount
- merchant
- description
- notes
- externalId (plaid if i do it)

## Categories

- category Id
- userId
- name
- type (enum)
- parentId (self foreign key)
- color
- description (removed)
- createdAt
- archived

## Budgets

- budgetId
- userId
- categoryId
- amount
- period (enum)
- createdAt
- startAt
