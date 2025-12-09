"""Email notification helper using Flask-Mail."""

import os
from typing import Optional

from flask import Flask
from flask_mail import Mail, Message

mail = Mail()


def init_mail(app: Flask) -> None:
    """Initialize Flask-Mail with app configuration."""
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"])
    mail.init_app(app)


def send_budget_alert(
    recipient_email: str,
    category_name: str,
    limit_amount: float,
    spent: float,
    used_percent: float,
    month: str,
) -> bool:
    """
    Send budget alert email when usage exceeds 90%.

    Args:
        recipient_email: User's email address
        category_name: Category name
        limit_amount: Budget limit
        spent: Amount spent
        used_percent: Usage percentage
        month: Month string (YYYY-MM)

    Returns:
        True if email sent successfully, False otherwise
    """
    if not recipient_email:
        return False

    try:
        subject = f"Budget Alert: {category_name} - {used_percent:.1f}% Used"
        body = f"""
Hello,

Your budget for {category_name} in {month} has reached {used_percent:.1f}% usage.

Details:
- Category: {category_name}
- Budget Limit: ${limit_amount:.2f}
- Amount Spent: ${spent:.2f}
- Usage: {used_percent:.1f}%

Please review your spending to stay within budget.

Best regards,
Smart Expense Tracker
        """.strip()

        msg = Message(subject=subject, recipients=[recipient_email], body=body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def get_user_email(user_id: int) -> Optional[str]:
    """Get user's email address from database."""
    from db import get_connection

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()

