#!/bin/bash

# Complete Feature Testing Script for Smart Expense Tracker
# Tests all major features systematically

BASE_URL="http://127.0.0.1:5050"
CURRENT_MONTH=$(date +%Y-%m)

echo "🧪 Complete Feature Testing - Smart Expense Tracker"
echo "===================================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Login (assuming user exists)
echo -e "${BLUE}Step 1: Logging in...${NC}"
LOGIN_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser_real","password":"test123"}')

LOGIN_HTTP_CODE=$(echo "$LOGIN_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$LOGIN_HTTP_CODE" != "200" ]; then
  echo -e "${RED}❌ Login failed!${NC}"
  echo "Response: $LOGIN_BODY"
  exit 1
fi

TOKEN=$(echo "$LOGIN_BODY" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
if [ -z "$TOKEN" ]; then
  echo -e "${RED}❌ Failed to extract token${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Login successful${NC}"
echo ""

# Step 2: Test Auto-Category Classification
echo -e "${BLUE}Step 2: Testing Auto-Category Classification...${NC}"
echo ""

test_cases=(
  '{"amount":30.0,"note":"Coffee shop"}'
  '{"amount":25.0,"note":"Uber ride"}'
  '{"amount":15.0,"note":"Movie tickets"}'
  '{"amount":20.0,"note":"Pharmacy shopping"}'
  '{"amount":45.0,"note":"Restaurant dinner"}'
  '{"amount":12.0,"note":"Bus ticket"}'
  '{"amount":50.0,"note":"Concert show"}'
)

category_names=("Food" "Transport" "Entertainment" "Others" "Food" "Transport" "Entertainment")

for i in "${!test_cases[@]}"; do
  echo -e "${YELLOW}  Test $((i+1)): ${category_names[$i]}${NC}"
  RESPONSE=$(curl -s -X POST "$BASE_URL/transactions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "${test_cases[$i]}")
  
  AUTO_CAT=$(echo "$RESPONSE" | grep -o '"auto_category":[0-9]*' | grep -o '[0-9]*')
  TX_ID=$(echo "$RESPONSE" | grep -o '"tx_id":[0-9]*' | grep -o '[0-9]*')
  
  if [ ! -z "$AUTO_CAT" ] && [ ! -z "$TX_ID" ]; then
    echo -e "${GREEN}    ✅ Created (tx_id: $TX_ID) - Auto-categorized as: $AUTO_CAT${NC}"
  else
    echo -e "${RED}    ❌ Failed${NC}"
    echo "    Response: $RESPONSE"
  fi
done

echo ""

# Step 3: Test Reports
echo -e "${BLUE}Step 3: Testing Report APIs...${NC}"

echo -e "${YELLOW}  3.1 Monthly Report${NC}"
MONTHLY=$(curl -s "$BASE_URL/report/monthly" -H "Authorization: Bearer $TOKEN")
if echo "$MONTHLY" | grep -q "month"; then
  echo -e "${GREEN}    ✅ Monthly report retrieved${NC}"
  echo "$MONTHLY" | python3 -m json.tool 2>/dev/null | head -10
else
  echo -e "${RED}    ❌ Failed${NC}"
fi

echo ""
echo -e "${YELLOW}  3.2 Category Report${NC}"
CATEGORY=$(curl -s "$BASE_URL/report/category" -H "Authorization: Bearer $TOKEN")
if echo "$CATEGORY" | grep -q "category"; then
  echo -e "${GREEN}    ✅ Category report retrieved${NC}"
  echo "$CATEGORY" | python3 -m json.tool 2>/dev/null
else
  echo -e "${RED}    ❌ Failed${NC}"
fi

echo ""
echo -e "${YELLOW}  3.3 Expense Prediction${NC}"
PREDICT=$(curl -s "$BASE_URL/predict" -H "Authorization: Bearer $TOKEN")
if echo "$PREDICT" | grep -q "predicted_next"; then
  echo -e "${GREEN}    ✅ Prediction retrieved${NC}"
  echo "$PREDICT" | python3 -m json.tool 2>/dev/null
else
  echo -e "${YELLOW}    ⚠️  Prediction may need more data${NC}"
  echo "$PREDICT"
fi

echo ""

# Step 4: Test Transaction List
echo -e "${BLUE}Step 4: Testing Transaction List...${NC}"
TX_LIST=$(curl -s "$BASE_URL/transactions" -H "Authorization: Bearer $TOKEN")
TX_COUNT=$(echo "$TX_LIST" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
if [ ! -z "$TX_COUNT" ]; then
  echo -e "${GREEN}  ✅ Retrieved $TX_COUNT transactions${NC}"
else
  echo -e "${RED}  ❌ Failed${NC}"
fi

echo ""

# Step 5: Test Budget Status
echo -e "${BLUE}Step 5: Testing Budget Status...${NC}"
BUDGET_STATUS=$(curl -s "$BASE_URL/budget/status?month=$CURRENT_MONTH" -H "Authorization: Bearer $TOKEN")
if echo "$BUDGET_STATUS" | grep -q "category"; then
  echo -e "${GREEN}  ✅ Budget status retrieved${NC}"
  echo "$BUDGET_STATUS" | python3 -m json.tool 2>/dev/null
else
  echo -e "${YELLOW}  ⚠️  No budgets set for current month${NC}"
fi

echo ""

# Summary
echo -e "${GREEN}=========================================="
echo "✅ Testing Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Visit http://127.0.0.1:5050/report to test Web UI"
echo "2. Check email for budget alerts"
echo "3. Review all transactions and reports"
echo ""

