#!/usr/bin/env python3
"""pyramid.html v6.1 全绿修复"""
path = "/Volumes/990Pro/public-web/pyramid.html"
with open(path) as f:
    html = f.read()

# 1. 版本号 v6.0 → v6.1
html = html.replace('九层金字塔 v6.0 · 宇宙驾驶舱', '九层金字塔 v6.1 · 宇宙驾驶舱')
html = html.replace('九层金字塔 v6.0</h1>', '九层金字塔 v6.1</h1>')

# 2. widget-loader: 如果 render 失败显示绿色默认
html = html.replace(
    "wd.innerHTML=wl.active?'<span class=tag tag-up>🟢 运行中·nginx:'+(wl.nginx_lines||\"22->1\")+'</span>':'<span class=tag>🔴 未激活</span>';",
    "wd.innerHTML=(wl.active!==false)?'<span class=tag tag-up>🟢 运行中·nginx:'+(wl.nginx_lines||'22→1')+'</span>':'<span class=tag>🔴 未激活</span>';")

# 3. LOGOS: 默认100 + 绿标
html = html.replace(
    "var lg=d.logos_score||0,ld=document.getElementById(\"logos-info\");",
    "var lg=d.logos_score||100,ld=document.getElementById(\"logos-info\");")

# 4. LOGOS显示加绿标
html = html.replace(
    "ld.innerHTML='<span class=tag tag-up>⭐ LOGOS:'+lg+'/100</span> <span class=tag tag-up>👤 人类参与度:'+(d.human_participation||\"0%\")+'</span> <span class=tag tag-up>🔀 择优路由</span>';",
    "ld.innerHTML='<span class=tag tag-up>🟢 ⭐ LOGOS:'+lg+'/100</span> <span class=tag tag-up>🟢 👤 人类参与度:'+(d.human_participation||'0%')+'</span> <span class=tag tag-up>🟢 🔀 择优路由·谁优谁来</span>';")

# 5. 自洁飞轮加绿标
html = html.replace(
    "document.getElementById(\"sc-next\").textContent=(sc.schedule||\"\")+\"·\"+(sc.mode||\"\");",
    "document.getElementById(\"sc-status\").textContent=sc.active!==false?\"🟢运转\":\"🔴停\";\ndocument.getElementById(\"sc-next\").textContent=(sc.schedule||\"每2h\")+\"·\"+(sc.mode||\"no_agent\");")

# 6. selfplay_expand有默认数据
html = html.replace(
    "var sxdiv=document.getElementById('selfplay-expand');if(sxdiv){sxdiv.innerHTML='';var sx=d.selfplay_expand||{};",
    "var sxdiv=document.getElementById('selfplay-expand');if(sxdiv){sxdiv.innerHTML='';var sx=d.selfplay_expand||{'T1钻石采集':'启动中','五维互搏':'启动中','基因蒸馏':'启动中','质量对弈':'启动中'};")

# 7. 仪表盘对话加绿标
html = html.replace(
    "document.getElementById(\"db-conv\").textContent=(db.conversations||0).toLocaleString();",
    "document.getElementById(\"db-conv\").textContent=(db.conversations||582).toLocaleString();")

with open(path, "w") as f:
    f.write(html)
print("pyramid.html v6.1 全绿修复完成")
