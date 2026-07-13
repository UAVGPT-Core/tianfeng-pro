#!/usr/bin/env python3
"""批量秒改秒见: 全部HTML页面浮窗优化"""
import os, re

BASE = "/Volumes/990Pro/public-web"

# 分类规则
XIAOSHU_ONLY = [  # 只留红色小枢(股票/金融/量化)
    "stock.html", "quant-api-application.html",
    "xiaoshu-v15.html", "xs-diag.html",
]

XIAOSHU_DIRS = [  # 整个目录只留小枢
    "xiaoshu/", "quote/", "mianmian-tianyi/", "mianmian/",
]

NONE_PAGES = [  # 不要浮窗
    "login.html", "register.html", "chat-fallback.html",
    "dashboard-fallback.html", "test-widget.html", "test-dual.html",
    "test-v7.html", "test-v15.html", "api-test.html",
    "voice-input.html",
]

NONE_DIRS = [  # 整个目录不要浮窗
    "admin-pages/", "internal/", "_archive_signals/",
    "_quarantine_compliance/", "tianfeng/", "tianyi/",
    "tianxun/", "widget/", "widget-admin/",
    "softphone/", "chat/", "demo/",
    "gemdesign-output/", "shenji/", "suppliers/",
    "baoli-eval/", "apache-gov/", "ai-plan/",
    "cto-proposal/", "evolution/", "fde-article/",
    "hrm-benchmark/", "guides/", "lgox-fde-response/",
    "lgox-response/", "templates/", "pyramid.old-backup/",
    "shangtejie-visit/", "shangtejie/",
]

ALREADY_DONE = {  # 已配置的页面(不动)
    "forestry.html": True, "forestry-pro.html": True,
    "futures.html": True, "signals.html": True,
    "jinhuo-cloud.html": True,
}

count = {"tianxun": 0, "xiaoshu": 0, "none": 0, "skip": 0}

def process_file(filepath):
    global count
    rel = os.path.relpath(filepath, BASE)
    fname = os.path.basename(filepath)
    
    # 跳过非HTML
    if not fname.endswith('.html'):
        return
    
    # 跳过隐藏文件
    if fname.startswith('._') or fname.startswith('.!'):
        return
    
    # 跳过已配置
    if fname in ALREADY_DONE and filepath == os.path.join(BASE, fname):
        count["skip"] += 1
        return
    
    # 判断分类
    widget = "tianxun"  # 默认: 蓝色天巡
    
    # 小枢目录
    for d in XIAOSHU_DIRS:
        if rel.startswith(d):
            widget = "xiaoshu"
            break
    
    # None目录
    for d in NONE_DIRS:
        if rel.startswith(d):
            widget = "none"
            break
    
    # 小枢特定文件
    if fname in XIAOSHU_ONLY:
        widget = "xiaoshu"
    
    # None特定文件
    if fname in NONE_PAGES:
        widget = "none"
    
    # 备份/archive页面 → none
    if 'backup' in fname.lower() or 'archive' in fname.lower():
        widget = "none"
    
    # 已是子目录的index(非根index) → none
    if fname == 'index.html' and rel != 'index.html':
        if widget == "tianxun":
            widget = "none"  # 子目录index默认不开浮窗
    
    # 读文件+修改
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return
    
    # 如果已有data-lgox-widget → 跳过
    if 'data-lgox-widget' in content:
        count["skip"] += 1
        return
    
    # 替换body标签
    if widget == "none":
        pass  # 不注入widget
    else:
        if '<body>' in content:
            content = content.replace('<body>', f'<body data-lgox-widget="{widget}">')
        elif '<body ' in content:
            # has existing body attrs
            pass  # 不处理已有属性的body
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        count[widget] += 1
    except Exception as e:
        pass

# 遍历所有HTML
for root, dirs, files in os.walk(BASE):
    # 跳过隐藏目录
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for f in files:
        process_file(os.path.join(root, f))

print(f"天巡(蓝): {count['tianxun']} | 小枢(红): {count['xiaoshu']} | 无浮窗: {count['none']} | 跳过: {count['skip']}")
