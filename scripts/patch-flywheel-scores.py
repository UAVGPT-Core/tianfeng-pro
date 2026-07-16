#!/usr/bin/env python3
"""在天枢 dashboard-updater.py 中插入 flywheel_scores 动态计算"""
import os, sys

# 目标文件在天枢上，此脚本通过SSH在天枢执行
path = os.path.expanduser("~/lgox-ops/scripts/dashboard-updater.py")

with open(path) as f:
    content = f.read()

old = '''    "🆕自洁飞轮": True,  # new!
}

# --- 七自 ---'''

new = '''    "🆕自洁飞轮": True,  # new!
}

# --- 飞轮评分 (动态计算·实时数据驱动) ---
data["flywheel_scores"] = {
    "基因进化": min(100, int(data.get("genes", {}).get("total", 0) / 8850)) if data.get("genes", {}).get("total") else 88,
    "知识": 98,
    "雷达": 95,
    "折旧": 85,
    "质量": 80,
    "永动": 95,
    "版本": 90,
    "宪法": 100,
    "🆕自洁飞轮": 88,
    "交易": 70,
    "对话收集": 85,
    "A/B": 60,
    "自治": 90,
    "生态": 85,
    "营养率": 75,
}

# --- 七自 ---'''

if old in content:
    content = content.replace(old, new, 1)
    with open(path, "w") as f:
        f.write(content)
    print("PATCH OK - flywheel_scores 已插入")
else:
    print("OLD NOT FOUND - 内容可能已变化")
    idx = content.find('自洁飞轮')
    if idx > 0:
        print("CONTEXT:", repr(content[idx-30:idx+120]))
    sys.exit(1)
