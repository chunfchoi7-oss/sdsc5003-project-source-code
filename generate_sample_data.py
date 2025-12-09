#!/usr/bin/env python3
"""
Sample data generation script for Smart Expense Tracker.
This script generates test data for demonstration and testing purposes.
"""

import os
import sys
from datetime import datetime, timedelta
import random

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_connection


def generate_sample_data(user_id: int, num_transactions: int = 50):
    """
    Generate sample transaction data for a user.
    
    Args:
        user_id: User ID to generate data for
        num_transactions: Number of transactions to generate
    """
    conn = None
    try:
        conn = get_connection()
        
        # Category mapping
        categories = {
            1: "Food",
            2: "Transport", 
            3: "Entertainment",
            4: "Others"
        }
        
        # Sample notes for each category
        sample_notes = {
            1: ["Lunch at restaurant", "Coffee shop", "Dinner with friends", "Grocery shopping", "Fast food"],
            2: ["Taxi ride", "Bus ticket", "Uber", "Gas station", "Parking fee"],
            3: ["Movie tickets", "Concert", "Game purchase", "Netflix subscription", "Theater show"],
            4: ["Pharmacy", "Shopping mall", "Utility bill", "Medicine", "General store"]
        }
        
        # Amount ranges for each category
        amount_ranges = {
            1: (10.0, 100.0),
            2: (5.0, 50.0),
            3: (15.0, 150.0),
            4: (20.0, 200.0)
        }
        
        with conn.cursor() as cur:
            # Generate transactions over the last 3 months
            base_date = datetime.now()
            transactions_created = 0
            
            for i in range(num_transactions):
                # Random category
                category_id = random.choice(list(categories.keys()))
                
                # Random amount
                min_amount, max_amount = amount_ranges[category_id]
                amount = round(random.uniform(min_amount, max_amount), 2)
                
                # Random note
                note = random.choice(sample_notes[category_id])
                
                # Random date within last 3 months
                days_ago = random.randint(0, 90)
                tx_date = (base_date - timedelta(days=days_ago)).date()
                
                try:
                    cur.execute(
                        """
                        INSERT INTO transactions (user_id, category_id, amount, note, tx_date)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (user_id, category_id, amount, note, tx_date)
                    )
                    transactions_created += 1
                except Exception as e:
                    print(f"Warning: Failed to insert transaction: {e}")
                    continue
            
            conn.commit()
            print(f"✅ Successfully created {transactions_created} sample transactions")
            
    except Exception as e:
        print(f"❌ Error generating sample data: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def generate_sample_budgets(user_id: int):
    """
    Generate sample budget data for a user.
    
    Args:
        user_id: User ID to generate budgets for
    """
    conn = None
    try:
        conn = get_connection()
        
        # Budget limits for each category
        budget_limits = {
            1: 500.0,  # Food
            2: 300.0,  # Transport
            3: 200.0,  # Entertainment
            4: 400.0   # Others
        }
        
        # Generate budgets for current month and next month
        current_month = datetime.now().strftime("%Y-%m")
        next_month = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m")
        
        with conn.cursor() as cur:
            for category_id, limit_amount in budget_limits.items():
                # Current month budget
                cur.execute(
                    """
                    INSERT INTO budgets (user_id, category_id, limit_amount, month_year)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, category_id, month_year)
                    DO UPDATE SET limit_amount = EXCLUDED.limit_amount
                    """,
                    (user_id, category_id, limit_amount, current_month)
                )
                
                # Next month budget
                cur.execute(
                    """
                    INSERT INTO budgets (user_id, category_id, limit_amount, month_year)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, category_id, month_year)
                    DO UPDATE SET limit_amount = EXCLUDED.limit_amount
                    """,
                    (user_id, category_id, limit_amount, next_month)
                )
            
            conn.commit()
            print(f"✅ Successfully created sample budgets for {current_month} and {next_month}")
            
    except Exception as e:
        print(f"❌ Error generating sample budgets: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("📊 Smart Expense Tracker - Sample Data Generator")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python generate_sample_data.py <user_id> [num_transactions]")
        print("Example: python generate_sample_data.py 1 50")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        num_transactions = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    except ValueError:
        print("❌ Error: user_id and num_transactions must be integers")
        sys.exit(1)
    
    print(f"\nGenerating data for user_id: {user_id}")
    print(f"Number of transactions: {num_transactions}\n")
    
    # Generate transactions
    generate_sample_data(user_id, num_transactions)
    
    # Generate budgets
    generate_sample_budgets(user_id)
    
    print("\n✅ Sample data generation complete!")
    print("\nNext steps:")
    print("1. Start the Flask app: python app.py")
    print("2. Login and view the data at: http://127.0.0.1:5050/report")

