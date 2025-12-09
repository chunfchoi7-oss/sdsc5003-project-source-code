#!/usr/bin/env python3
"""Test and visualize expense prediction."""

import numpy as np

# 模拟当前数据
months = ["2025-10", "2025-11", "2025-12"]
totals = [118.5, 20.0, 75.0]

print("📊 支出预测分析")
print("=" * 50)
print(f"\n历史数据：")
for i, (month, total) in enumerate(zip(months, totals)):
    print(f"  {month}: {total} RMB")

# 线性回归计算
x = np.arange(len(totals), dtype=float)
y = np.array(totals, dtype=float)
slope, intercept = np.polyfit(x, y, 1)

print(f"\n📈 趋势分析：")
print(f"  斜率 (slope): {slope:.2f}")
print(f"  截距 (intercept): {intercept:.2f}")
print(f"  趋势: {'上升' if slope > 0 else '下降'}")

# 预测下个月
next_month_index = len(totals)
predicted = slope * next_month_index + intercept
predicted = max(0.0, predicted)  # 确保不为负数

print(f"\n🔮 预测结果：")
print(f"  下个月 (2026-01) 预测支出: {predicted:.2f} RMB")
print(f"\n计算公式：")
print(f"  predicted = slope × {next_month_index} + intercept")
print(f"  predicted = {slope:.2f} × {next_month_index} + {intercept:.2f}")
print(f"  predicted = {predicted:.2f} RMB")

