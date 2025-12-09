-- Smart Expense Tracker table definitions
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type VARCHAR(10) CHECK (type IN ('income', 'expense'))
);

CREATE TABLE IF NOT EXISTS transactions (
    tx_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    category_id INT REFERENCES categories(category_id),
    amount DECIMAL(10, 2) NOT NULL,
    note TEXT,
    tx_date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS budgets (
    budget_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    category_id INT REFERENCES categories(category_id),
    limit_amount DECIMAL(10, 2),
    month_year VARCHAR(7)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_user_category_month
    ON budgets (user_id, category_id, month_year);

-- Email notification settings (optional, for future enhancements)
CREATE TABLE IF NOT EXISTS email_settings (
    user_id INT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    email_enabled BOOLEAN DEFAULT true,
    alert_threshold DECIMAL(5, 2) DEFAULT 90.00,
    last_alert_sent TIMESTAMP
);

-- Seed default expense categories in English
INSERT INTO categories (category_id, name, type)
VALUES
  (1, 'Food', 'expense'),
  (2, 'Transport', 'expense'),
  (3, 'Entertainment', 'expense'),
  (4, 'Others', 'expense')
ON CONFLICT (category_id) DO NOTHING;

-- Verify that categories are inserted in the correct order
SELECT * FROM categories ORDER BY category_id;