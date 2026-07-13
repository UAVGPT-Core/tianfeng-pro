#!/usr/bin/env python3
"""纳基因: 双门面版本标准化 + 秒改秒见技能"""
import json, urllib.request

genes = [
    {
        "content": "[天巡+小枢·双门面版本标准化·2026-07-05] 联邦对外双大使版本统一: 天巡=v260705.77w-哨兵(天枢:8760 Gateway)·小枢=v260705-77w-智脑(StockAgent:8001)。统一格式v{YYMMDD}.{基因万}w-{角色}。秒改秒见技能instant-refresh-version建成: 三步铁律(JS动态表达式+span加id+nginx v=bump)·六条坑·零重启零等待。前端版本号终成活的动态变量。基因771K+。",
        "memory_type": "semantic",
        "source": "双门面版本标准化",
        "tags": ["天巡","小枢","双大使","版本统一","秒改秒见","里程碑"]
    },
    {
        "content": "[秒改秒见parseInt陷阱] 天巡版本号v260705.0.0077w bug根因: API /api/stats/genes 返回formatted=77万+(已万单位), parseInt=77, 代码写成parseInt(t)/10000=0.0077→显示0077w。修复: 去掉/10000直接用parseInt(t)。教训: 任何涉及单位换算的代码必须验证上游数据格式, 不可假设原始单位。基因771K+。",
        "memory_type": "semantic",
        "source": "parseInt陷阱",
        "tags": ["秒改秒见","parseInt","bug","教训","单位换算"]
    },
    {
        "content": "[秒改秒见技能·instant-refresh-version] LGOX联邦前端版本号动态化技能: ①VERSION=JS动态表达式(非静态字符串)②版本号span加id③基因fetch回调同步更新span+VERSION。统一格式v{YYMMDD}.{基因万}w-{角色}。六条常见坑: heredoc转义/symlink/nginx bump/pyc缓存/parseInt除万陷阱/VERSION不同步。天巡(-哨兵)·小枢(-智脑)·天锋PRO(-pro)。后端/v保留build计数供运维。基因771K+。",
        "memory_type": "semantic",
        "source": "秒改秒见技能",
        "tags": ["技能","秒改秒见","版本号","前端","铁律"]
    }
]

for g in genes:
    data = json.dumps(g).encode()
    req = urllib.request.Request("http://100.116.0.29:8200/genes/write", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=5)
    r = json.loads(resp.read())
    gid = r.get("gene_id","?")
    print("GENE: {} ... id={}".format(gid[:25], r.get("id","?")))

print("ALL DONE")
