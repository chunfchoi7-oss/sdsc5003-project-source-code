#!/bin/bash

# Smart Expense Tracker - Feature Testing Script
# Tests: Auto-category classification & Email budget alerts

BASE_URL="http://127.0.0.1:5050"
CURRENT_MONTH=$(date +%Y-%m)

echo "🧪 Smart Expense Tracker Feature Testing"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Register a test user
echo -e "${BLUE}Step 1: Registering test user...${NC}"
TEST_USERNAME="testuser_$(date +%s)"
REGISTER_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$TEST_USERNAME\",
    \"email\": \"test@example.com\",
    \"password\": \"test123\"
  }")

HTTP_CODE=$(echo "$REGISTER_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
REGISTER_BODY=$(echo "$REGISTER_RESPONSE" | sed '/HTTP_CODE:/d')

if [ -z "$HTTP_CODE" ] || [ "$HTTP_CODE" != "201" ]; then
  echo -e "${YELLOW}⚠️  Registration returned HTTP $HTTP_CODE${NC}"
  echo "Response: $REGISTER_BODY"
  echo ""
  echo "Trying to login with existing user 'testuser'..."
  TEST_USERNAME="testuser"
  LOGIN_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/login" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "testuser",
      "password": "test123"
    }')
else
  USER_ID=$(echo "$REGISTER_BODY" | grep -o '"user_id":[0-9]*' | grep -o '[0-9]*')
  echo -e "${GREEN}✅ User registered successfully! User ID: $USER_ID${NC}"
  
  # Step 2: Login
  echo -e "${BLUE}Step 2: Logging in...${NC}"
  LOGIN_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$TEST_USERNAME\",
      \"password\": \"test123\"
    }")
fi

LOGIN_HTTP_CODE=$(echo "$LOGIN_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | sed '/HTTP_CODE:/d')

if [ -z "$LOGIN_HTTP_CODE" ] || [ "$LOGIN_HTTP_CODE" != "200" ]; then
  echo -e "${RED}❌ Login failed! HTTP $LOGIN_HTTP_CODE${NC}"
  echo "Response: $LOGIN_BODY"
  echo ""
  echo -e "${YELLOW}💡 Tip: Make sure Flask app is running and database is initialized.${NC}"
  echo "   Run: python app.py"
  echo "   Run: psql -U postgres -d expense_db -f schema.sql"
  exit 1
fi

TOKEN=$(echo "$LOGIN_BODY" | grep -o '"token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo -e "${RED}❌ Failed to extract token from response!${NC}"
  echo "Response: $LOGIN_BODY"
  exit 1
fi

echo -e "${GREEN}✅ Login successful! Token obtained.${NC}"
echo ""

# Step 3: Test Auto-Category Classification
echo -e "${BLUE}Step 3: Testing Auto-Category Classification...${NC}"
echo ""

test_cases=(
  '{"amount":25.50,"note":"Lunch at McDonald"}'
  '{"amount":15.00,"note":"Taxi to airport"}'
  '{"amount":12.99,"note":"Movie tickets"}'
  '{"amount":8.50,"note":"Coffee shop"}'
  '{"amount":45.00,"note":"Uber ride downtown"}'
  '{"amount":30.00,"note":"Concert tickets"}'
  '{"amount":20.00,"note":"Pharmacy shopping"}'
)

category_names=("Food" "Transport" "Entertainment" "Food" "Transport" "Entertainment" "Others")

for i in "${!test_cases[@]}"; do
  echo -e "${YELLOW}Test $((i+1)): Creating transaction with auto-category...${NC}"
  RESPONSE=$(curl -s -X POST "$BASE_URL/transactions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "${test_cases[$i]}")
  
  TX_ID=$(echo $RESPONSE | grep -o '"tx_id":[0-9]*' | grep -o '[0-9]*')
  AUTO_CAT=$(echo $RESPONSE | grep -o '"auto_category":[0-9]*' | grep -o '[0-9]*')
  
  if [ ! -z "$TX_ID" ]; then
    if [ ! -z "$AUTO_CAT" ]; then
      echo -e "${GREEN}  ✅ Transaction created (tx_id: $TX_ID) - Auto-categorized as category_id: $AUTO_CAT${NC}"
    else
      echo -e "${GREEN}  ✅ Transaction created (tx_id: $TX_ID) - Manual category${NC}"
    fi
  else
    echo -e "${RED}  ❌ Failed to create transaction${NC}"
    echo "  Response: $RESPONSE"
  fi
done

echo ""

# Step 4: Set up budgets
echo -e "${BLUE}Step 4: Setting up budgets...${NC}"

budgets=(
  '{"category_id":1,"limit_amount":100,"month_year":"'$CURRENT_MONTH'"}'
  '{"category_id":2,"limit_amount":80,"month_year":"'$CURRENT_MONTH'"}'
  '{"category_id":3,"limit_amount":50,"month_year":"'$CURRENT_MONTH'"}'
)

for budget in "${budgets[@]}"; do
  RESPONSE=$(curl -s -X POST "$BASE_URL/budget" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "$budget")
  
  BUDGET_ID=$(echo $RESPONSE | grep -o '"budget_id":[0-9]*' | grep -o '[0-9]*')
  if [ ! -z "$BUDGET_ID" ]; then
    echo -e "${GREEN}  ✅ Budget set (budget_id: $BUDGET_ID)${NC}"
  fi
done

echo ""

# Step 5: Add transactions to trigger budget alert (>90%)
echo -e "${BLUE}Step 5: Adding transactions to trigger budget alert (>90%)...${NC}"

# Add enough Food transactions to exceed 90% of 100 budget
for i in {1..4}; do
  curl -s -X POST "$BASE_URL/transactions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"amount\":25.00,\"note\":\"Restaurant meal $i\"}" > /dev/null
done

echo -e "${GREEN}  ✅ Added transactions to exceed budget threshold${NC}"
echo ""

# Step 6: Check budget status
echo -e "${BLUE}Step 6: Checking budget status...${NC}"
BUDGET_STATUS=$(curl -s "http://127.0.0.1:5050/budget/status?month=$CURRENT_MONTH" \
  -H "Authorization: Bearer $TOKEN")

echo "$BUDGET_STATUS" | python3 -m json.tool 2>/dev/null || echo "$BUDGET_STATUS"
echo ""

# Step 7: Manually trigger budget alert check
echo -e "${BLUE}Step 7: Manually triggering budget alert check...${NC}"
ALERT_RESPONSE=$(curl -s -X POST "http://127.0.0.1:5050/budget/check-alerts?month=$CURRENT_MONTH" \
  -H "Authorization: Bearer $TOKEN")

echo "$ALERT_RESPONSE"
echo ""

# Step 8: View all transactions
echo -e "${BLUE}Step 8: Viewing all transactions...${NC}"
TRANSACTIONS=$(curl -s "http://127.0.0.1:5050/transactions" \
  -H "Authorization: Bearer $TOKEN")

echo "$TRANSACTIONS" | python3 -m json.tool 2>/dev/null || echo "$TRANSACTIONS"
echo ""

# Summary
echo -e "${GREEN}=========================================="
echo "✅ Testing Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Check your email (test@example.com) for budget alert"
echo "2. Visit http://127.0.0.1:5050/report to view charts"
echo "3. Use the token below for manual API testing:"
echo ""
echo "Token: $TOKEN"
echo ""

