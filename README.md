# Smart Expense Tracker

A full-stack expense tracking and budget analysis system built with Flask and PostgreSQL (Track 1: Database Application Development).

## Features

- ✅ User authentication with JWT
- ✅ Transaction management
- ✅ Budget setting and monitoring
- ✅ Monthly/category reports with Chart.js visualization
- ✅ Expense prediction using linear regression
- 🤖 **Intelligent category classification** (TF-IDF + Naive Bayes)
- 📧 **Email budget alerts** (Flask-Mail)

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database**
   ```bash
   createdb expense_db
   psql -U postgres -d expense_db -f schema.sql
   ```

3. **Configure environment variables (optional)**
   ```bash
   export JWT_SECRET_KEY="your-secret-key"
   export MAIL_SERVER="smtp.gmail.com"
   export MAIL_PORT="587"
   export MAIL_USERNAME="your-email@gmail.com"
   export MAIL_PASSWORD="your-app-password"
   ```

4. **Run application**
   ```bash
   python app.py
   # or
   flask --app app run --debug --host=0.0.0.0 --port=5050
   ```

## Configuration

### Database (db.py)

Default connection parameters (can be overridden via environment variables):

| Variable | Default |
|----------|---------|
| POSTGRES_DB | expense_db |
| POSTGRES_USER | postgres |
| POSTGRES_PASSWORD | 123456 |
| POSTGRES_HOST | localhost |
| POSTGRES_PORT | 5432 |

### Email (for budget alerts)

| Variable | Default | Description |
|----------|---------|-------------|
| MAIL_SERVER | smtp.gmail.com | SMTP server |
| MAIL_PORT | 587 | SMTP port (TLS) |
| MAIL_USE_TLS | true | Use TLS |
| MAIL_USERNAME | (empty) | Sender email |
| MAIL_PASSWORD | (empty) | App password |

**Gmail setup:**
1. Enable 2-factor authentication
2. Generate app password: https://myaccount.google.com/apppasswords
3. Use app password as `MAIL_PASSWORD`

## API Endpoints

### Authentication

**POST /register** - Register user
```bash
curl -X POST http://127.0.0.1:5050/register \
     -H "Content-Type: application/json" \
     -d '{"username":"ronnie","email":"r@ex.com","password":"1234"}'
```

**POST /login** - Login and get JWT token
```bash
curl -X POST http://127.0.0.1:5050/login \
     -H "Content-Type: application/json" \
     -d '{"username":"ronnie","password":"1234"}'
```

### Transactions

**POST /transactions** - Create transaction (with auto-category detection)
```bash
curl -X POST http://127.0.0.1:5050/transactions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <TOKEN>" \
     -d '{"amount":50.0,"note":"Lunch at restaurant"}'
```

**GET /transactions** - List transactions
```bash
curl "http://127.0.0.1:5050/transactions" \
     -H "Authorization: Bearer <TOKEN>"
```

### Budget

**POST /budget** - Set budget
```bash
curl -X POST http://127.0.0.1:5050/budget \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <TOKEN>" \
     -d '{"category_id":1,"limit_amount":500,"month_year":"2025-12"}'
```

**GET /budget/status** - Get budget utilization
```bash
curl "http://127.0.0.1:5050/budget/status?month=2025-12" \
     -H "Authorization: Bearer <TOKEN>"
```

### Reports & Prediction

**GET /report/monthly** - Monthly expense statistics
```bash
curl "http://127.0.0.1:5050/report/monthly" \
     -H "Authorization: Bearer <TOKEN>"
```

**GET /report/category** - Category-wise expense statistics
```bash
curl "http://127.0.0.1:5050/report/category" \
     -H "Authorization: Bearer <TOKEN>"
```

**GET /predict** - Predict next month expense
```bash
curl "http://127.0.0.1:5050/predict" \
     -H "Authorization: Bearer <TOKEN>"
```

**GET /report** - Web UI dashboard
Visit: `http://127.0.0.1:5050/report`

## Intelligent Classification

The system automatically categorizes transactions based on transaction notes using TF-IDF + Naive Bayes:

- **Food**: "restaurant", "lunch", "dinner", "coffee", etc.
- **Transport**: "taxi", "uber", "bus", "train", "gas", etc.
- **Entertainment**: "movie", "cinema", "game", "concert", etc.
- **Others**: "shopping", "pharmacy", "utility", etc.

If `category_id` is not provided, the system will predict it from the `note` field.

## Email Budget Alerts

When budget usage exceeds 90%, the system automatically sends an email alert to the user's registered email address. Alerts are triggered:
- Automatically after creating a new transaction
- Manually via `POST /budget/check-alerts`

## Project Structure

```
smart_expense_tracker/
├── app.py              # Flask application
├── db.py               # Database connection
├── nlp_classifier.py   # Category classification
├── email_helper.py     # Email notifications
├── schema.sql          # Database schema
├── requirements.txt    # Dependencies
└── templates/
    └── report.html     # Web dashboard
```

## Testing

See `test_features.sh` for automated testing examples.

## License

MIT
