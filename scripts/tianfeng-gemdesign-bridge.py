#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天锋PRO GemDesign桥接插件 v1.0
融合GemDesign的MCP协议 + 天锋PRO本地代码生成能力
"""

import json, os, sys, subprocess, time, re, base64
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = "/Volumes/990Pro/public-web/gemdesign-output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    print(f"[{t}] {msg}")

NL = "\n"

# ======= 模板 =======
DASHBOARD_TPL = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#333}}
.header{{background:linear-gradient(135deg,#0a1628,#1a2a4a);color:#fff;padding:16px 24px;display:flex;align-items:center;justify-content:space-between}}
.header h1{{font-size:18px;font-weight:600}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:20px 24px}}
.stat-card{{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.stat-card .num{{font-size:24px;font-weight:700;color:#0a1628}}
.stat-card .label{{font-size:12px;color:#888}}
.content{{display:grid;grid-template-columns:2fr 1fr;gap:16px;padding:0 24px 24px}}
.chart-box{{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.side-card{{background:#fff;border-radius:10px;padding:16px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
@media(max-width:768px){{.stats{{grid-template-columns:repeat(2,1fr)}}.content{{grid-template-columns:1fr}}}}
</style></head><body>
<div class="header"><h1>{title}</h1><span style="font-size:13px;opacity:.7">{subtitle}</span></div>
<div class="stats">{stats_html}</div>
<div class="content"><div class="chart-box"><h3>核心指标趋势</h3><div style="height:280px;background:linear-gradient(180deg,rgba(0,212,170,.08),transparent);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#aaa">{chart_content}</div></div><div><div class="side-card"><h3>最近活动</h3>{side_content}</div></div></div>
</body></html>"""

LANDING_TPL = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color:#333}}
.hero{{background:linear-gradient(135deg,#0a1628,#1a2a4a);min-height:60vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:40px 20px}}
.hero h1{{font-size:36px;color:#fff;margin-bottom:16px}}
.hero .highlight{{background:linear-gradient(90deg,#00d4aa,#76b900);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.hero p{{font-size:16px;color:rgba(255,255,255,.65);max-width:600px;margin:0 auto 24px}}
.hero .cta{{display:inline-block;padding:12px 32px;background:linear-gradient(90deg,#00d4aa,#76b900);color:#fff;border-radius:8px;text-decoration:none;font-weight:600}}
.features{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;padding:60px 40px;max-width:960px;margin:0 auto}}
.feature{{text-align:center}}
.feature .icon{{font-size:36px;margin-bottom:12px}}
.feature h3{{font-size:16px;margin-bottom:6px}}
.feature p{{font-size:13px;color:#888}}
@media(max-width:768px){{.hero h1{{font-size:26px}}.features{{grid-template-columns:1fr;padding:40px 20px}}}}
</style></head><body>
<section class="hero"><div><div style="font-size:12px;color:rgba(0,212,170,.7);margin-bottom:12px;letter-spacing:2px">{tagline}</div><h1>{headline}</h1><p>{description}</p><a href="#" class="cta">{cta_text}</a></div></section>
<section class="features">{features_html}</section>
</body></html>"""

APP_PAGE_TPL = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f5f5;color:#333}}
.top-bar{{background:#fff;border-bottom:1px solid #eee;padding:10px 20px;display:flex;align-items:center;gap:16px}}
.top-bar .brand{{font-weight:700;font-size:16px;color:#0a1628}}
.top-bar .nav{{display:flex;gap:12px;margin-left:auto}}
.top-bar .nav a{{text-decoration:none;color:#666;font-size:13px;padding:6px 12px;border-radius:6px}}
.top-bar .nav a.active{{background:#0a1628;color:#fff}}
.page{{max-width:960px;margin:24px auto;padding:0 16px}}
.card{{background:#fff;border-radius:10px;padding:20px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.card h2{{font-size:16px;margin-bottom:12px;color:#1a2a4a}}
.btn{{padding:8px 20px;border:none;border-radius:6px;font-size:14px;cursor:pointer}}
.btn-primary{{background:#0a1628;color:#fff}}
.btn-success{{background:#00d4aa;color:#fff}}
.table{{width:100%;border-collapse:collapse;font-size:13px}}
.table th{{background:#f8faff;padding:8px 12px;text-align:left;border-bottom:2px solid #eee;font-weight:600}}
.table td{{padding:8px 12px;border-bottom:1px solid #eee}}
.tag{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:600}}
.tag-green{{background:rgba(0,212,170,.12);color:#00d4aa}}
.tag-blue{{background:rgba(79,143,234,.12);color:#4f8fea}}
.tag-orange{{background:rgba(255,165,0,.12);color:#ff8c00}}
@media(max-width:480px){{.top-bar{{flex-wrap:wrap}}.top-bar .nav{{margin-left:0;width:100%;overflow-x:auto}}}}
</style></head><body>
<div class="top-bar"><div class="brand">{brand}</div><div class="nav">{nav_html}</div></div>
<div class="page"><h1 style="font-size:22px;margin-bottom:16px">{page_title}</h1>{content_html}</div>
</body></html>"""

class GemDesignBridge:
    def generate_dashboard(self, prompt, stats=None):
        title = (prompt[:30] + "...") if len(prompt) > 30 else prompt
        if stats is None:
            stats = [("128", "活跃基因"), ("3,847", "联邦调用"), ("92%", "响应率"), ("12s", "平均耗时")]
        stats_html = "".join(f'<div class="stat-card"><div class="num">{n}</div><div class="label">{l}</div></div>' for n, l in stats)
        return DASHBOARD_TPL.format(
            title=title, subtitle="LGOX联邦 · 天锋PRO原型",
            stats_html=stats_html,
            chart_content="此处展示基因进化曲线 · 联邦调用量 · 节点健康度",
            side_content="<div style='font-size:13px;color:#666'>基因 GENE-SEM-9667 已同步联邦<br>天工节点在线 · 响应12ms<br>新登记3条战略分析基因</div>"
        )

    def generate_landing(self, prompt):
        features = [
            ("🧬", "基因进化", "AI知识自动提取为基因，全联邦共享"),
            ("🔗", "联邦互联", "多节点协同，数据不出域，知识全流通"),
            ("⚡", "自进化飞轮", "越用越聪明，每10分钟迭代一次"),
        ]
        f_html = "".join(f'<div class="feature"><div class="icon">{i}</div><h3>{t}</h3><p>{d}</p></div>' for i, t, d in features)
        return LANDING_TPL.format(
            tagline="LGOX联邦 · 天锋PRO",
            headline=prompt[:80],
            description=(prompt[80:200] if len(prompt) > 80 else "AI时代的FDE操作系统——让AI落地不再需要200个驻场工程师"),
            cta_text="立即体验",
            features_html=f_html
        )

    def generate_app_page(self, prompt):
        title = (prompt[:30] + "...") if len(prompt) > 30 else prompt
        nav_items = [("控制台", True), ("基因库", False), ("联邦", False), ("设置", False)]
        ACTIVE_CLS = " class=\"active\""
        nav_html = "".join(f'<a href="#"' + (ACTIVE_CLS if a else '') + f'>{t}</a>' for t, a in nav_items)
        content = """<div class=\"card\"><h2>任务管理</h2>
<table class=\"table\"><tr><th>任务</th><th>状态</th><th>优先级</th><th>节点</th></tr>
<tr><td>基因进化加速器</td><td><span class=\"tag tag-green\">运行中</span></td><td><span class=\"tag tag-orange\">高</span></td><td>地枢</td></tr>
<tr><td>联邦搜索同步</td><td><span class=\"tag tag-green\">运行中</span></td><td><span class=\"tag tag-blue\">中</span></td><td>龙虾</td></tr>
<tr><td>Onyx知识库巡检</td><td><span class=\"tag tag-green\">运行中</span></td><td><span class=\"tag tag-blue\">中</span></td><td>龙虾</td></tr>
</table></div>
<div class=\"card\"><h2>快速操作</h2>
<button class=\"btn btn-primary\" style=\"margin-right:8px\">+ 新建基因</button>
<button class=\"btn btn-success\">运行联邦同步</button>
</div>"""
        return APP_PAGE_TPL.format(brand="天锋PRO", nav_html=nav_html, page_title=title, content_html=content)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="天锋PRO GemDesign桥接插件")
    parser.add_argument("--prompt", default="LGOX联邦AI助手操作面板")
    parser.add_argument("--template", default="dashboard", choices=["dashboard", "landing", "app_page"])
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    log("天锋PRO GemDesign桥接插件启动")
    log("模板: " + args.template)

    bridge = GemDesignBridge()
    gen_map = {
        "dashboard": bridge.generate_dashboard,
        "landing": bridge.generate_landing,
        "app_page": bridge.generate_app_page,
    }
    html = gen_map[args.template](args.prompt)
    filename = args.output or f"tianfeng_gem_{int(time.time())}.html"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    log("已保存: " + path)
    log("文件大小: " + f"{len(html)/1024:.1f}KB")
    link = f"https://1mac-studio.tail30cdac.ts.net/public/gemdesign-output/{filename}"
    log("公网链接: " + link)

if __name__ == "__main__":
    main()
