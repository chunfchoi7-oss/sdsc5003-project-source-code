# 手动测试指南

## 前置准备

1. **确保服务运行**
   ```bash
   python app.py
   ```
   服务应在 `http://127.0.0.1:5050` 运行

2. **确保数据库已初始化**
   ```bash
   psql -U postgres -d expense_db -f schema.sql
   ```

3. **（可选）配置邮件服务**
   如果要测试邮件功能，设置环境变量：
   ```bash
   export MAIL_USERNAME="your-email@gmail.com"
   export MAIL_PASSWORD="your-app-password"
   export MAIL_DEFAULT_SENDER="your-email@gmail.com"
   ```

---

## 测试 1: 智能分类功能

### 步骤 1.1: 注册用户
```bash
curl -X POST http://127.0.0.1:5050/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "email": "test@example.com",
       "password": "test123"
     }'
```

**预期响应：**
```json
{"status":"ok","user_id":1}
```

### 步骤 1.2: 登录获取 Token
```bash
curl -X POST http://127.0.0.1:5050/login \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "password": "test123"
     }'
```

**预期响应：**
```json
{"status":"ok","token":"eyJ0eXAiOiJKV1QiLCJhbGc..."}
```

**保存 Token：**
```bash
export TOKEN="你的token值"
```

### 步骤 1.3: 测试自动分类（不提供 category_id）

#### 测试用例 1: Food 类别
```bash
curl -X POST http://127.0.0.1:5050/transactions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{
       "amount": 25.50,
       "note": "Lunch at McDonald"
     }'
```

**预期响应：**
```json
{
  "status": "ok",
  "tx_id": 1,
  "auto_category": 1
}
```
✅ `auto_category: 1` 表示自动分类为 Food

#### 测试用例 2: Transport 类别
```bash
curl -X POST http://127.0.0.1:5050/transactions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{
       "amount": 15.00,
       "note": "Taxi to airport"
     }'
```

**预期响应：**
```json
{
  "status": "ok",
  "tx_id": 2,
  "auto_category": 2
}
```
✅ `auto_category: 2` 表示自动分类为 Transport

#### 测试用例 3: Entertainment 类别
```bash
curl -X POST http://127.0.0.1:5050/transactions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{
       "amount": 12.99,
       "note": "Movie tickets"
     }'
```

**预期响应：**
```json
{
  "status": "ok",
  "tx_id": 3,
      "auto_category": 3
}
```
✅ `auto_category: 3` 表示自动分类为 Entertainment

#### 测试用例 4: Others 类别
```bash
curl -X POST http://127.0.0.1:5050/transactions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{
       "amount": 20.00,
       "note": "Pharmacy shopping"
     }'
```

**预期响应：**
```json
{
  "status": "ok",
  "tx_id": 4,
  "auto_category": 4
}
```
✅ `auto_category: 4` 表示自动分类为 Others

### 步骤 1.4: 验证分类结果
```bash
curl "http://127.0.0.1:5050/transactions" \
     -H "Authorization: Bearer $TOKEN"
```

查看返回的交易记录，确认 `category_id` 是否正确。

---

## 测试 2: 邮件预算提醒功能

### 步骤 2.1: 设置预算
```bash
# 设置 Food 类别预算为 100 元
curl -X POST http://127.0.0.1:5050/budget \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{
       "category_id": 1,
       "limit_amount": 100,
       "month_year": "2025-12"
     }'
```

**预期响应：**
```json
{"status":"ok","budget_id":1}
```

### 步骤 2.2: 添加交易接近预算上限
```bash
# 添加 4 笔交易，每笔 25 元，总计 100 元（达到 100%）
for i in {1..4}; do
  curl -X POST http://127.0.0.1:5050/transactions \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer $TOKEN" \
       -d "{
         \"amount\": 25.00,
         \"note\": \"Restaurant meal $i\"
       }"
done
```

### 步骤 2.3: 检查预算状态
```bash
curl "http://127.0.0.1:5050/budget/status?month=2025-12" \
     -H "Authorization: Bearer $TOKEN"
```

**预期响应：**
```json
[
  {
    "category_id": 1,
    "category": "Food",
    "limit_amount": 100.0,
    "spent": 100.0,
    "used_percent": 100.0
  }
]
```

✅ `used_percent: 100.0` 表示已超过 90% 阈值

### 步骤 2.4: 手动触发预算提醒检查
```bash
curl -X POST "http://127.0.0.1:5050/budget/check-alerts?month=2025-12" \
     -H "Authorization: Bearer $TOKEN"
```

**预期响应：**
```json
{"status":"ok","message":"Budget alerts checked"}
```

### 步骤 2.5: 验证邮件发送

1. **检查邮箱**：登录注册时使用的邮箱（test@example.com）
2. **查看收件箱**：应该收到主题为 "Budget Alert: Food - 100.0% Used" 的邮件
3. **邮件内容应包含**：
   - 类别名称：Food
   - 预算限额：$100.00
   - 已花费：$100.00
   - 使用率：100.0%

**注意**：如果未配置邮件服务，邮件发送会失败，但不会影响其他功能。

---

## 测试 3: 端到端流程测试

### 完整流程

1. **注册用户** → 获取 user_id
2. **登录** → 获取 JWT token
3. **使用智能分类创建交易** → 验证自动分类
4. **设置预算** → 创建预算记录
5. **添加多笔交易** → 累计支出
6. **检查预算状态** → 查看使用率
7. **触发预算提醒** → 验证邮件发送
8. **查看报表** → 访问 Web UI

### 一键测试脚本

使用提供的自动化测试脚本：

```bash
chmod +x test_features.sh
./test_features.sh
```

脚本会自动执行所有测试步骤。

---

## 测试 4: Web UI 测试

### 访问报表页面

1. 打开浏览器访问：`http://127.0.0.1:5050/report`

2. **输入信息**：
   - JWT Token：粘贴之前获取的 token
   - Reporting Month：输入当前月份（如：2025-12）

3. **点击 "Load Report"**

4. **验证显示**：
   - ✅ 月度支出趋势图（折线图）
   - ✅ 分类支出占比（饼图）
   - ✅ 预算使用情况列表（超过 90% 的应显示 🔔）
   - ✅ 下月支出预测

---

## 常见问题排查

### 1. 智能分类不工作

**问题**：返回的 `auto_category` 不正确

**排查步骤**：
- 确认 `note` 字段不为空
- 检查 `note` 中是否包含关键词（food, taxi, movie 等）
- 查看应用日志中的错误信息

**解决方案**：
- 使用更明确的描述（如 "Lunch at restaurant" 而不是 "Lunch"）
- 如果分类不准确，可以手动指定 `category_id`

### 2. 邮件未收到

**问题**：预算超过 90% 但未收到邮件

**排查步骤**：
1. 检查环境变量是否配置：
   ```bash
   echo $MAIL_USERNAME
   echo $MAIL_PASSWORD
   ```

2. 检查用户邮箱是否正确：
   ```bash
   curl "http://127.0.0.1:5050/transactions" \
        -H "Authorization: Bearer $TOKEN"
   ```

3. 查看应用日志中的错误信息

**解决方案**：
- 配置正确的 SMTP 服务器信息
- Gmail 用户需要使用应用专用密码
- 检查邮箱的垃圾邮件文件夹

### 3. Token 过期

**问题**：API 返回 401 Unauthorized

**解决方案**：
- 重新登录获取新 token
- Token 默认有效期为 24 小时

### 4. 预算状态查询为空

**问题**：`/budget/status` 返回空数组

**排查步骤**：
- 确认已设置预算（`POST /budget`）
- 确认月份格式正确（YYYY-MM）
- 确认预算的 `month_year` 与查询参数一致

---

## 测试检查清单

- [ ] 用户注册成功
- [ ] 登录获取 token
- [ ] 智能分类：Food 类别识别正确
- [ ] 智能分类：Transport 类别识别正确
- [ ] 智能分类：Entertainment 类别识别正确
- [ ] 智能分类：Others 类别识别正确
- [ ] 预算设置成功
- [ ] 预算状态查询正常
- [ ] 预算超过 90% 时触发提醒
- [ ] 邮件发送成功（如果配置了邮件服务）
- [ ] Web UI 报表正常显示
- [ ] 图表数据正确

---

## 性能测试建议

### 批量创建交易测试智能分类

```bash
# 创建 100 笔交易测试分类性能
for i in {1..100}; do
  curl -X POST http://127.0.0.1:5050/transactions \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer $TOKEN" \
       -d "{
         \"amount\": $((RANDOM % 100)),
         \"note\": \"Test transaction $i\"
       }" &
done
wait
```

### 压力测试预算提醒

```bash
# 快速添加交易触发多次提醒检查
for i in {1..10}; do
  curl -X POST http://127.0.0.1:5050/transactions \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer $TOKEN" \
       -d "{
         \"amount\": 10.00,
         \"note\": \"Quick transaction $i\"
       }"
done
```

---

## 下一步

测试完成后，可以：

1. **优化分类模型**：使用用户历史数据重新训练
2. **自定义邮件模板**：修改 `email_helper.py` 中的邮件内容
3. **添加更多类别**：扩展 `nlp_classifier.py` 中的关键词
4. **集成到 CI/CD**：将测试脚本加入自动化测试流程

