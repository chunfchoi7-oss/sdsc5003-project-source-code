-- Reporting queries: monthly and category expenses

-- Monthly expense totals (expense categories only)
SELECT
    TO_CHAR(t.tx_date, 'YYYY-MM') AS month,
    SUM(t.amount) AS total_expense
FROM transactions t
JOIN categories c ON t.category_id = c.category_id
WHERE c.type = 'expense'
GROUP BY month
ORDER BY month;

-- Category expense totals (expense categories only)
SELECT
    c.name AS category,
    SUM(t.amount) AS total_expense
FROM transactions t
JOIN categories c ON t.category_id = c.category_id
WHERE c.type = 'expense'
GROUP BY c.name
ORDER BY total_expense DESC;

