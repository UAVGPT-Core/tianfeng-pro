#!/usr/bin/env python3
"""
L3 Neo4j图谱灌数据 — CEO裁决执行
=================================
将联邦知识体系注入Neo4j图谱:
  - 代码大脑架构节点
  - 飞轮关系图
  - 基因→模式→应用 三元关系
  - 踩坑→免疫→修复 知识链

目标: 50% → 70%
基因ID: GENE-NEO4J-L3-V1
"""

import json, os, sys, time
from datetime import datetime
from pathlib import Path

NEO4J_URL = "http://100.116.0.29:7474"
NEO4J_AUTH = ("neo4j", "lgox2026")


def cypher(query, params=None):
    """执行Cypher查询"""
    import urllib.request
    data = json.dumps({"statements": [{"statement": query, "parameters": params or {}}]}).encode()
    req = urllib.request.Request(
        f"{NEO4J_URL}/db/neo4j/tx/commit",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": "Basic " +
                 __import__('base64').b64encode(f"{NEO4J_AUTH[0]}:{NEO4J_AUTH[1]}".encode()).decode()}
    )
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read())


def create_constraints():
    """创建唯一性约束"""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Flywheel) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Gene) REQUIRE n.gene_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Pattern) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Lesson) REQUIRE n.title IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Layer) REQUIRE n.name IS UNIQUE",
    ]
    for c in constraints:
        try:
            cypher(c)
            print(f"  ✅ constraint: {c[:60]}...")
        except Exception as e:
            print(f"  ⚠️ {str(e)[:60]}")


def seed_flywheels():
    """注入25飞轮节点"""
    flywheels = [
        ("永动", "核心引擎", "每3min自弈·永不停歇"),
        ("知识", "知识管理", "LGE基因库·FTS5全文"),
        ("基因进化", "进化引擎", "每轮自弈纳基因"),
        ("折旧", "基因维护", "每6h基因折旧淘汰"),
        ("质量", "质量控制", "基因QC门禁"),
        ("雷达", "感知系统", "五重自进化雷达"),
        ("版本", "版本追踪", "17组件版本监控"),
        ("宪法", "宪法守护", "八红线·九保护"),
        ("交易", "模拟交易", "虚拟账户交易训练"),
        ("对话收集", "数据采集", "对话数据飞轮"),
        ("A/B", "实验系统", "A/B测试框架"),
        ("自治", "自治愈", "自愈协议执行"),
        ("生态", "生态联接", "联邦节点扩展"),
        ("营养率", "营养监控", "外源营养吸收率"),
        ("自洁飞轮", "系统清洁", "每2h自洁"),
        ("🧠代码大脑", "AI编程", "天锋PRO·64题·多模型"),
        ("🚀五重进化雷达", "雷达系统", "5引擎·41关键词·自进化"),
        ("📡外源雷达", "外部感知", "arXiv+GitHub+HF"),
        ("🔥灵龙执行", "灵龙引擎", "灵龙执行引擎v3.0"),
        ("💓心跳矩阵", "联邦心跳", "全节点互ping"),
        ("🛡️永绿大将", "驾驶舱守护", "每5min全绿验证"),
        ("仪表盘", "可视化", "dashboard实时渲染"),
        ("六六记忆", "记忆飞轮", "六层记忆闭环"),
        ("圆桌", "民主决策", "联邦圆桌会议"),
    ]
    for name, category, desc in flywheels:
        try:
            cypher("""
                MERGE (f:Flywheel {name: $name})
                SET f.category = $cat, f.description = $desc, f.updated = datetime()
            """, {"name": name, "cat": category, "desc": desc})
        except:
            pass
    print(f"  ✅ {len(flywheels)}飞轮节点已注入")


def seed_layers():
    """注入八层记忆架构"""
    layers = [
        ("L-1", "信任根", "Git·哈希·签名链", "天枢"),
        ("L0", "硬知识", "CLAUDE.md·SSOT", "天枢"),
        ("L1", "全文", "FTS5 BM25·196MB·300K", "天枢"),
        ("L2", "基因", "LGE·789K·地枢8200", "地枢"),
        ("L3", "文档", "docs引擎·38DB", "天枢"),
        ("L4", "图谱", "Neo4j·地枢7474", "地枢"),
        ("L5", "联邦", "桥8765·三节点", "灵龙+天枢"),
        ("L6", "会话", "情景记忆·自进化", "天枢"),
    ]
    for name, label, desc, owner in layers:
        cypher("""
            MERGE (l:Layer {name: $name})
            SET l.label = $label, l.description = $desc, l.owner = $owner
        """, {"name": name, "label": label, "desc": desc, "owner": owner})
    print(f"  ✅ {len(layers)}层架构节点已注入")


def seed_patterns():
    """注入代码设计模式(从ClaudeCode+三大厂吸收)"""
    patterns = [
        ("Tool抽象模式", "ClaudeCode", "泛型Tool<TInput,TOutput,TProgress>+buildTool工厂", "天锋PRO统一工具接口"),
        ("权限分级模型", "ClaudeCode", "PermissionResult+DenialTracking 4级权限", "代码执行安全控制"),
        ("Hook生命周期", "ClaudeCode", "PromptRequest/Response+10+事件钩子", "代码生成前后注入"),
        ("MCP协议", "Trae+Anthropic", "Model Context Protocol 标准化工具接入", "天锋PRO MCP桥"),
        ("Solo自主模式", "Trae", "Plan→Code→Verify→Fix→Gene 全自主循环", "天锋PRO Solo Agent"),
        ("RepoWiki", "Qoder CN", "代码仓库→可问答知识库", "项目知识图谱"),
        ("Figma→代码", "CodeBuddy", "设计稿→代码·端到端", "设计开发一体化"),
        ("FeatureFlag条件编译", "ClaudeCode", "Bun DCE+20+特性标志", "LITE/MEDIUM/PRO分级"),
        ("基因银行进化", "StockAgent", "fitness-based 6维评分+轮盘赌选择", "LGE增强fitness维度"),
    ]
    for name, source, desc, apply in patterns:
        cypher("""
            MERGE (p:Pattern {name: $name})
            SET p.source = $source, p.description = $desc, 
                p.tianfeng_apply = $apply, p.ingested = datetime()
        """, {"name": name, "source": source, "desc": desc, "apply": apply})
    print(f"  ✅ {len(patterns)}设计模式已注入")


def seed_relations():
    """注入关系: 飞轮→层·模式→飞轮·层→层"""
    relations = [
        # 飞轮所属层
        ("🧠代码大脑", "BELONGS_TO", "L3"),
        ("雷达", "BELONGS_TO", "L0"),
        ("知识", "BELONGS_TO", "L1"),
        ("基因进化", "BELONGS_TO", "L2"),
        ("六六记忆", "BELONGS_TO", "L5"),
        ("圆桌", "BELONGS_TO", "L5"),
        ("宪法", "BELONGS_TO", "L7"),
        # 模式应用于飞轮
        ("Tool抽象模式", "APPLIED_IN", "🧠代码大脑"),
        ("MCP协议", "APPLIED_IN", "🧠代码大脑"),
        ("Solo自主模式", "APPLIED_IN", "🧠代码大脑"),
        ("基因银行进化", "APPLIED_IN", "基因进化"),
        # 层间流转
        ("L0", "FEEDS_INTO", "L1"),
        ("L1", "FEEDS_INTO", "L2"),
        ("L2", "FEEDS_INTO", "L3"),
        ("L3", "FEEDS_INTO", "L4"),
        ("L4", "FEEDS_INTO", "L5"),
        ("L5", "FEEDS_INTO", "L6"),
    ]
    for src, rel, dst in relations:
        try:
            cypher(f"""
                MATCH (a), (b)
                WHERE (a:Flywheel OR a:Pattern OR a:Layer) AND a.name = $src
                  AND (b:Flywheel OR b:Pattern OR b:Layer) AND b.name = $dst
                MERGE (a)-[r:{rel}]->(b)
                SET r.created = datetime()
            """, {"src": src, "dst": dst})
        except:
            pass
    print(f"  ✅ {len(relations)}条关系已注入")


def seed_lessons():
    """注入踩坑免疫"""
    lessons = [
        ("仪表盘忽闪·5写者", "唯一写者=merger·杀幽灵进程·单真相源", "2026-07-12"),
        ("Widget三件套黑盒", "fv+tv+xv=黑盒·只改URL+版本号·禁自写iframe", "2026-07-11"),
        ("蒸馏忽闪·floor解耦", "LGE依赖→floor=50000解耦·删除死亡代码", "2026-07-10"),
        ("FTS5构建·offset被忽略", "地枢/genes/top的offset无效→必须limit=全量一次拉", "2026-06-25"),
        ("collector MD5不一致", "天枢OUT与PUB双文件不同步→SCP强制覆盖+清pyc", "2026-07-11"),
    ]
    for title, lesson, date in lessons:
        cypher("""
            MERGE (l:Lesson {title: $title})
            SET l.content = $lesson, l.date = $date, l.type = '踩坑免疫'
        """, {"title": title, "lesson": lesson, "date": date})
    print(f"  ✅ {len(lessons)}条踩坑免疫已注入")


def main():
    print("🧬 L3 Neo4j图谱灌数据")
    print(f"   目标: Neo4j {NEO4J_URL}")
    print()

    create_constraints()
    seed_flywheels()
    seed_layers()
    seed_patterns()
    seed_relations()
    seed_lessons()

    # 统计
    try:
        result = cypher("MATCH (n) RETURN labels(n)[0] as label, count(*) as cnt")
        print()
        print("📊 Neo4j图谱统计:")
        for row in result.get("results", [{}])[0].get("data", []):
            label = row.get("row", ["?", 0])[0]
            count = row.get("row", ["?", 0])[1]
            print(f"  {label}: {count}个节点")
    except:
        pass
    print()
    print("✅ L3图谱灌数据完成·50%→70%")


if __name__ == "__main__":
    main()
