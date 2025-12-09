"""Smart Expense Tracker Flask application entry point."""

import os
from datetime import datetime
from decimal import Decimal
from typing import Any

import numpy as np
from flask import Flask, jsonify, render_template, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import db_time, get_connection
from email_helper import get_user_email, init_mail, send_budget_alert
from nlp_classifier import predict_category

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")
jwt = JWTManager(app)

# Initialize Flask-Mail
init_mail(app)


def _to_float(value: Decimal | float | None) -> float | None:
    """Convert Decimal to float for JSON payloads."""

    if value is None:
        return None
    return float(value) if isinstance(value, Decimal) else value


def _json_body() -> dict[str, Any]:
    """Safely read JSON body."""

    return request.get_json(silent=True) or {}


@app.route("/")
def index():
    return "Expense Tracker API running ✅"


@app.route("/test_db")
def test_db():
    """Verify database connectivity and return current time."""

    try:
        current_time = db_time()
        return jsonify({"status": "ok", "db_time": current_time})
    except Exception as exc:  # pragma: no cover - runtime only
        app.logger.exception("Database test failed")
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/register", methods=["POST"])
def register():
    """Register a new user with hashed password."""

    data = _json_body()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required"}), 400

    conn = None
    try:
        conn = get_connection()
        password_hash = generate_password_hash(password)
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING user_id;
                """,
                (username, email, password_hash),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Failed to create user")
            user_id = row[0]
        return jsonify({"status": "ok", "user_id": user_id}), 201
    except Exception as exc:
        app.logger.exception("User registration failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/login", methods=["POST"])
def login():
    """Authenticate user and issue JWT token."""

    data = _json_body()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required"}), 400

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, password_hash FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
        if not row or not check_password_hash(row[1], password):
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401
        # identity must be a string for JWT "sub" claim
        token = create_access_token(identity=str(row[0]))
        return jsonify({"status": "ok", "token": token})
    except Exception as exc:
        app.logger.exception("User login failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/transactions", methods=["POST"])
@jwt_required()
def create_transaction():
    """Create a new transaction for the authenticated user with optional auto-category detection."""

    current_user_id = int(get_jwt_identity())
    data = _json_body()
    required_fields = ("amount",)

    missing = [field for field in required_fields if field not in data]
    if missing:
        return (
            jsonify(
                {"status": "error", "message": f"Missing fields: {', '.join(missing)}"}
            ),
            400,
        )

    # Optional guard if body still sends user_id
    body_user_id = data.get("user_id")
    if body_user_id and body_user_id != current_user_id:
        return jsonify({"status": "error", "message": "User mismatch"}), 403

    # Auto-detect category if not provided
    category_id = data.get("category_id")
    note = data.get("note", "")
    auto_detected = False

    if not category_id and note:
        predicted = predict_category(note, data.get("amount"))
        if predicted:
            category_id = predicted
            auto_detected = True
        else:
            # Default to "Others" if prediction fails
            category_id = 4
            auto_detected = True
    elif not category_id:
        return jsonify({"status": "error", "message": "category_id required when note is empty"}), 400

    conn = None
    try:
        conn = get_connection()
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (user_id, category_id, amount, note)
                VALUES (%s, %s, %s, %s)
                RETURNING tx_id;
                """,
                (
                    current_user_id,
                    category_id,
                    data["amount"],
                    note,
                ),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Failed to create transaction")
            tx_id = row[0]

        # Check budget alerts after transaction creation
        _check_and_send_budget_alerts(current_user_id)

        response = {"status": "ok", "tx_id": tx_id}
        if auto_detected:
            response["auto_category"] = category_id
        return jsonify(response), 201
    except Exception as exc:
        app.logger.exception("Create transaction failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/transactions", methods=["GET"])
@jwt_required()
def list_transactions():
    """List transactions for the authenticated user."""

    current_user_id = int(get_jwt_identity())
    requested_user_id = request.args.get("user_id", type=int) or current_user_id
    if requested_user_id != current_user_id:
        return jsonify({"status": "error", "message": "User mismatch"}), 403

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tx_id, category_id, amount, note, tx_date
                FROM transactions
                WHERE user_id = %s
                ORDER BY tx_date DESC;
                """,
                (current_user_id,),
            )
            rows = cur.fetchall()

        result = [
            {
                "tx_id": row[0],
                "category_id": row[1],
                "amount": _to_float(row[2]),
                "note": row[3],
                "tx_date": row[4].isoformat() if row[4] else None,
            }
            for row in rows
        ]
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("List transactions failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/budget", methods=["POST"])
@jwt_required()
def create_budget():
    """Create or update a monthly budget for a category."""

    current_user_id = int(get_jwt_identity())
    data = _json_body()
    required_fields = ("category_id", "limit_amount", "month_year")
    missing = [field for field in required_fields if field not in data]
    if missing:
        return (
            jsonify(
                {"status": "error", "message": f"Missing fields: {', '.join(missing)}"}
            ),
            400,
        )

    conn = None
    try:
        conn = get_connection()
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO budgets (user_id, category_id, limit_amount, month_year)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, category_id, month_year)
                DO UPDATE SET limit_amount = EXCLUDED.limit_amount
                RETURNING budget_id;
                """,
                (
                    current_user_id,
                    data["category_id"],
                    data["limit_amount"],
                    data["month_year"],
                ),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Failed to create budget")
            budget_id = row[0]
        return jsonify({"status": "ok", "budget_id": budget_id}), 201
    except Exception as exc:
        app.logger.exception("Create budget failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/budget/status", methods=["GET"])
@jwt_required()
def budget_status():
    """Return budget utilization for a given month."""

    current_user_id = int(get_jwt_identity())
    user_id = request.args.get("user_id", type=int) or current_user_id
    month = request.args.get("month")

    if user_id != current_user_id:
        return jsonify({"status": "error", "message": "User mismatch"}), 403
    if not month:
        return jsonify({"status": "error", "message": "Month parameter required"}), 400

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.category_id,
                    c.name AS category,
                    b.limit_amount,
                    COALESCE(SUM(t.amount), 0) AS spent
                FROM budgets b
                LEFT JOIN transactions t
                    ON b.category_id = t.category_id
                    AND TO_CHAR(t.tx_date, 'YYYY-MM') = b.month_year
                    AND t.user_id = b.user_id
                LEFT JOIN categories c ON c.category_id = b.category_id
                WHERE b.user_id = %s AND b.month_year = %s
                GROUP BY b.category_id, c.name, b.limit_amount;
                """,
                (current_user_id, month),
            )
            rows = cur.fetchall()

        payload = []
        for row in rows:
            limit_amount = _to_float(row[2]) or 0.0
            spent = _to_float(row[3]) or 0.0
            used_percent = round((spent / limit_amount) * 100, 2) if limit_amount else 0.0
            payload.append(
                {
                    "category_id": row[0],
                    "category": row[1],
                    "limit_amount": limit_amount,
                    "spent": spent,
                    "used_percent": used_percent,
                }
            )
        return jsonify(payload)
    except Exception as exc:
        app.logger.exception("Budget status failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/report/monthly")
@jwt_required()
def monthly_report():
    """Return monthly expense aggregation."""

    current_user_id = int(get_jwt_identity())

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    TO_CHAR(t.tx_date, 'YYYY-MM') AS month,
                    SUM(t.amount) AS total_expense
                FROM transactions t
                JOIN categories c ON t.category_id = c.category_id
                WHERE c.type = 'expense' AND t.user_id = %s
                GROUP BY month
                ORDER BY month;
                """,
                (current_user_id,),
            )
            rows = cur.fetchall()
        payload = [
            {"month": row[0], "total_expense": _to_float(row[1])} for row in rows
        ]
        return jsonify(payload)
    except Exception as exc:
        app.logger.exception("Monthly report failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/report/category")
@jwt_required()
def category_report():
    """Return category expense aggregation."""

    current_user_id = int(get_jwt_identity())

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.name AS category,
                    SUM(t.amount) AS total_expense
                FROM transactions t
                JOIN categories c ON t.category_id = c.category_id
                WHERE c.type = 'expense' AND t.user_id = %s
                GROUP BY c.name
                ORDER BY total_expense DESC;
                """,
                (current_user_id,),
            )
            rows = cur.fetchall()
        payload = [
            {"category": row[0], "total_expense": _to_float(row[1])} for row in rows
        ]
        return jsonify(payload)
    except Exception as exc:
        app.logger.exception("Category report failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/predict")
@jwt_required()
def predict_expense():
    """Predict next month expense using linear regression."""

    current_user_id = int(get_jwt_identity())

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    TO_CHAR(t.tx_date, 'YYYY-MM') AS month,
                    SUM(t.amount) AS total
                FROM transactions t
                WHERE t.user_id = %s
                GROUP BY month
                ORDER BY month;
                """,
                (current_user_id,),
            )
            rows = cur.fetchall()

        if not rows:
            return jsonify({"status": "error", "message": "Not enough data"}), 400

        recent_rows = rows[-6:]
        months = [row[0] for row in recent_rows]
        totals = [float(row[1]) for row in recent_rows]

        if len(totals) == 1:
            predicted = totals[0]
        else:
            x = np.arange(len(totals), dtype=float)
            y = np.array(totals, dtype=float)
            slope, intercept = np.polyfit(x, y, 1)
            predicted = max(0.0, float(slope * len(totals) + intercept))

        return jsonify(
            {
                "months": months,
                "predicted_next": round(predicted, 2),
            }
        )
    except Exception as exc:
        app.logger.exception("Prediction failed")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()


@app.route("/report")
def report_page():
    """Render the dashboard page with Chart.js visualizations."""

    return render_template("report.html")


def _check_and_send_budget_alerts(user_id: int) -> None:
    """Check budget utilization and send email alerts if threshold exceeded."""
    from datetime import datetime

    current_month = datetime.now().strftime("%Y-%m")
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.category_id,
                    c.name AS category,
                    b.limit_amount,
                    COALESCE(SUM(t.amount), 0) AS spent,
                    b.month_year
                FROM budgets b
                LEFT JOIN transactions t
                    ON b.category_id = t.category_id
                    AND TO_CHAR(t.tx_date, 'YYYY-MM') = b.month_year
                    AND t.user_id = b.user_id
                LEFT JOIN categories c ON c.category_id = b.category_id
                WHERE b.user_id = %s AND b.month_year = %s
                GROUP BY b.category_id, c.name, b.limit_amount, b.month_year;
                """,
                (user_id, current_month),
            )
            rows = cur.fetchall()

        user_email = get_user_email(user_id)
        if not user_email:
            return

        for row in rows:
            limit_amount = _to_float(row[2]) or 0.0
            spent = _to_float(row[3]) or 0.0
            if limit_amount > 0:
                used_percent = round((spent / limit_amount) * 100, 2)
                if used_percent > 90.0:
                    send_budget_alert(
                        recipient_email=user_email,
                        category_name=row[1] or "Unknown",
                        limit_amount=limit_amount,
                        spent=spent,
                        used_percent=used_percent,
                        month=row[4] or current_month,
                    )
    except Exception as exc:
        app.logger.exception("Budget alert check failed")
    finally:
        if conn is not None:
            conn.close()


@app.route("/budget/check-alerts", methods=["POST"])
@jwt_required()
def check_budget_alerts():
    """Manually trigger budget alert check for the authenticated user."""

    current_user_id = int(get_jwt_identity())
    month = request.args.get("month")
    if not month:
        from datetime import datetime

        month = datetime.now().strftime("%Y-%m")

    try:
        _check_and_send_budget_alerts(current_user_id)
        return jsonify({"status": "ok", "message": "Budget alerts checked"})
    except Exception as exc:
        app.logger.exception("Budget alert check failed")
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)