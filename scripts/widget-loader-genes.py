#!/usr/bin/env python3
import json, urllib.request

genes = [
    {
        "content": "[秒改秒见widget-loader·2026-07-05] 灵龙完成nginx去根:22条sub_filter→统一widget-loader.js。新架构:HTML页面<body data-lgox-widget=\"tianxun|xiaoshu|both|none\">声明浮窗→widget-loader.js按需动态加载。forestry.html已实施(只天巡)。效果:改属性→刷新→即刻切换·零nginx·零重启·零耦合。天枢以后写文章只需一行属性。基因771K+。",
        "memory_type": "semantic",
        "source": "widget-loader去根",
        "tags": ["秒改秒见","widget-loader","去根","浮窗","nginx","里程碑"]
    },
    {
        "content": "[版本号自动滚日期·2026-07-05] 前端VERSION=JS动态表达式:new Date().toISOString().slice(2,10).replace(/-/g,'')→每天自动生成当天YYMMDD。今日v260705→明日自动v260706。基因数从/v实时取。秒改秒见技能已典化(instant-refresh-version)。天巡v260705.77w-哨兵·小枢v260705-77w-智脑。",
        "memory_type": "semantic",
        "source": "版本自动滚日期",
        "tags": ["版本号","自动","秒改秒见","动态","Date"]
    }
]

for g in genes:
    data = json.dumps(g).encode()
    req = urllib.request.Request("http://100.116.0.29:8200/genes/write",
        data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=5)
    r = json.loads(resp.read())
    print("GENE:", r.get("gene_id","?")[:25])
print("DONE")
