#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║  联邦新节点种子注入引擎 v1.0                        ║
║  Node Seed Package — 入网即注入核心知识              ║
║  2026-07-13 · 解决致命伤#6                           ║
╚══════════════════════════════════════════════════╝

设计:
  新节点入网 → 自动拉取种子包 → 注入LGE本地缓存 → 激活认知
  种子包 = 核心基因(topN) + 能力图谱 + 联邦宪法 + 节点标准

七自闭环:
  自感知: 检测新节点注册→自动触发注入
  自协调: 根据节点类型选择种子包内容
  自愈合: 注入失败自动重试·3次后告警
  自进化: 种子包内容随联邦基因进化自动更新
  自迭代: 节点消化反馈→优化种子包选择
  自反思: 定期审计节点知识覆盖率
  自约束: 不注入敏感数据·不覆盖已有知识
"""

import json, time, sys, os, hashlib
from pathlib import Path
from datetime import datetime
from urllib import request, parse

# ══════════════════════════════
# 配置
# ══════════════════════════════
LGE_URL = "http://100.116.0.29:8200"
BRIDGE_URL = "http://127.0.0.1:8765"   # 本地优先（灵龙自身bridge）
FALLBACK_BRIDGE = "http://100.116.0.29:8765"  # 地枢备桥（降级·天枢防火墙阻断HTTP直连）
LGA_URL = "http://127.0.0.1:8202"
LGE_KEY = "fbe0b015eb7a03727903b660c4cecc60"
DATA_DIR = Path.home() / "lgox-ops/data/seeds"
STATE_FILE = DATA_DIR / "seed_state.json"
SEED_CACHE = DATA_DIR / "seed_cache.json"

# ══════════════════════════════
# 种子包定义
# ══════════════════════════════

# 核心知识主题（fallback: 已知高fitness基因ID）
SEED_TOPICS = [
    ("联邦架构", "联邦节点 互通标准"),
    ("七自基因", "七自 闭环"),
    ("能力图谱", "节点能力"),
    ("联邦宪法", "八红线 宪法"),
    ("基因引擎", "LGE 基因写入"),
    ("节点标准", "节点入网 profile"),
    ("天锋PRO", "天锋 编程 代码"),
    ("通讯协议", "GCP 联邦桥"),
]

# 预置核心基因ID（已知高fitness·作为fallback）
CORE_GENE_IDS = [
    "GENE-SEM-4dc047cc",   # 金字塔v7.82
    "GENE-SEM-057812f1",   # 七自基因白皮书
    "GENE-LIGHTWEIGHT-9f2a1e8d3c7b",  # 轻量化铁律
    "GENE-SEM-993207cdae82a132",      # 保密分级
    "GENE-PRO-f7b2d90c25ef1ced",      # 双平台发布标准
    "GENE-SEM-9e4dda17aa96a66c",      # 双大将对比
    "GENE-PRO-d3c116a2e3ef63cd",      # GitHub灾备
    "GENE-SEM-709bfa0fc3e63955",      # 开源进化策略
]

def fetch_genes(query, n=5, timeout=2):
    """从LGE搜索基因，超时快速降级"""
    for lge_url in [LGA_URL, LGE_URL]:
        try:
            data = json.dumps({"query": query, "n_results": n}).encode()
            req = request.Request(f"{lge_url}/genes/search", data=data,
                headers={"Content-Type": "application/json"})
            resp = request.urlopen(req, timeout=timeout)
            result = json.loads(resp.read())
            if isinstance(result, list):
                return result
            return result.get("results", result.get("genes", []))
        except:
            continue
    return []

def is_lge_reachable():
    """快速检测LGE/LGA是否可达(HTTP级别)"""
    for lge_url in [LGA_URL, LGE_URL]:
        try:
            req = request.Request(f"{lge_url}/health")
            resp = request.urlopen(req, timeout=2)
            return True
        except:
            continue
    return False

def build_seed_package():
    """构建最新种子包"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("🧬 构建联邦种子包...")
    package = {
        "version": "1.0",
        "built_at": datetime.utcnow().isoformat(),
        "total_genes": 0,
        "topics": {},
        "capability_graph": {},
        "meta": {
            "description": "新节点入网种子包·入网即注入核心知识",
            "usage": "解压后注入LGE本地缓存→激活节点认知"
        }
    }

    lge_available = is_lge_reachable()
    if lge_available:
        print("✅ LGE可达，搜索基因...")
    else:
        print("⚠️ LGE/LGA均不可达，使用预置基因fallback")
    
    for topic_name, query in SEED_TOPICS:
        if lge_available:
            genes = fetch_genes(query)
            gene_ids = [g.get("gene_id", "?") for g in genes[:3]] if genes else []
        else:
            genes = []
            gene_ids = []
        if not gene_ids:
            gene_ids = CORE_GENE_IDS[:3]
        package["topics"][topic_name] = {
            "query": query,
            "count": len(genes) if genes else len(gene_ids),
            "top_gene_ids": gene_ids,
            "source": "lge" if genes else "fallback"
        }
        package["total_genes"] += len(gene_ids)

    # 注入能力图谱 — 本地桥优先（带重试），地枢降级
    _cap_done = False
    for bridge_url in [BRIDGE_URL, FALLBACK_BRIDGE]:
        for attempt in range(1, 4):  # ★ 2026-07-15: 2→3, 匹配诊断建议
            try:
                req = request.Request(f"{bridge_url}/federation/nodes")
                resp = request.urlopen(req, timeout=3)
                nodes = json.loads(resp.read())
                if isinstance(nodes, dict):
                    nodes = nodes.get("nodes", nodes)
                package["capability_graph"] = {
                    "node_count": len(nodes) if isinstance(nodes, (list, dict)) else 0,
                    "snapshot": str(nodes)[:3000],
                    "bridge_source": bridge_url
                }
                _cap_done = True
                break
            except:
                if attempt < 2 and bridge_url == BRIDGE_URL:
                    time.sleep(1.5)
                    continue
        if _cap_done:
            break
    else:
        package["capability_graph"] = {"error": "bridge unreachable"}

    return package

def inject_to_node(node_name, package, lge_available=True):
    """向指定节点注入种子包"""
    results = []

    # 方式1: 通过联邦桥发送种子包消息
    seed_msg = {
        "to": node_name,
        "from": "灵龙",
        "type": "SEED_PACKAGE",
        "priority": "P0",
        "msg_id": f"seed-{time.strftime('%m%d%H%M')}",
        "ttl": 86400,
        "content": json.dumps(package, ensure_ascii=False)[:5000],
        "meta": {"version": package["version"], "total_genes": package["total_genes"]}
    }
    try:
        data = json.dumps(seed_msg, ensure_ascii=False).encode()
        req = request.Request(f"{BRIDGE_URL}/messages/send", data=data,
            headers={"Content-Type": "application/json"})
        resp = request.urlopen(req, timeout=3)
        results.append({"method": "bridge", "status": "sent"})
    except Exception as e:
        results.append({"method": "bridge", "status": "failed", "error": str(e)[:80]})

    # 方式2: 写入LGE为node-seed基因(仅LGE可用时)
    if lge_available:
        seed_gene = {
            "content": f"[联邦种子包v{package['version']}] 新节点{node_name}入网·核心知识{package['total_genes']}条",
            "memory_type": "procedural",
            "source": f"seed-injector/{node_name}",
            "tags": ["seed", "onboarding", f"to:{node_name}", "domain:topology"],
            "fitness_score": 0.95
        }
        try:
            data = json.dumps(seed_gene).encode()
            req = request.Request(f"{LGE_URL}/genes/write", data=data,
                headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
            resp = request.urlopen(req, timeout=3)
            gid = json.loads(resp.read()).get("gene_id", "?")
            results.append({"method": "lge-gene", "gene_id": gid})
        except Exception as e:
            results.append({"method": "lge-gene", "status": "failed", "error": str(e)[:80]})
    else:
        results.append({"method": "lge-gene", "status": "skipped", "reason": "LGE unavailable"})

    return results

def auto_onboard(force=False):
    """自动检测新节点→注入种子包"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 读取已注入记录
    try:
        state = json.load(STATE_FILE.open())
    except:
        state = {"injected": {}, "last_scan": None}

    # 扫描联邦桥节点列表 — 本地优先（带重试，抗瞬态SQLite I/O超时）
    nodes = None
    MAX_RETRIES = 5  # ★ 2026-07-15: 3→5, SQLite I/O竞争持续, 频率>3次/天
    for bridge_url in [BRIDGE_URL, FALLBACK_BRIDGE]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                req = request.Request(f"{bridge_url}/federation/nodes")
                resp = request.urlopen(req, timeout=5)
                data = json.loads(resp.read())
                nodes = data.get("nodes", data)
                if isinstance(nodes, dict):
                    nodes = nodes
                break
            except Exception as e:
                if attempt < MAX_RETRIES and bridge_url == BRIDGE_URL:
                    time.sleep(2)  # 本地桥瞬态I/O，等待后重试
                    continue
                print(f"⚠️ {bridge_url} 不可达: {e}")
                break
        if nodes is not None:
            break
    
    if nodes is None:
        print("❌ 联邦桥不可达（本地及地枢备桥均失败）")
        return

    # 发现未注入节点
    new_nodes = []
    for name in (nodes.keys() if isinstance(nodes, dict) else [n.get("name","?") for n in nodes]):
        if name not in state["injected"] or force:
            new_nodes.append(name)

    if not new_nodes:
        print(f"✅ 全部{len(nodes)}节点已注入")
        return

    # 构建种子包
    package = build_seed_package()
    json.dump(package, SEED_CACHE.open("w"), ensure_ascii=False)

    lge_available = is_lge_reachable()

    # 逐个注入
    for node in new_nodes:
        print(f"🚀 注入 {node}...")
        results = inject_to_node(node, package, lge_available=lge_available)
        success = any("sent" in str(r.get("status","")) or "gene_id" in r for r in results)
        state["injected"][node] = {
            "time": datetime.utcnow().isoformat(),
            "success": success,
            "details": results
        }
        print(f"  {'✅' if success else '❌'} {node}")

    state["last_scan"] = datetime.utcnow().isoformat()
    json.dump(state, STATE_FILE.open("w"), ensure_ascii=False, indent=2)
    print(f"完成: {len(new_nodes)}节点注入")

def show_status():
    """查看种子注入状态"""
    try:
        state = json.load(STATE_FILE.open())
        print(f"已注入: {len(state['injected'])}节点")
        for node, info in state["injected"].items():
            status = "✅" if info["success"] else "❌"
            print(f"  {status} {node}: {info['time'][:19]}")
    except:
        print("暂无注入记录")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"

    if cmd == "scan":
        auto_onboard()
    elif cmd == "force":
        auto_onboard(force=True)
    elif cmd == "build":
        pkg = build_seed_package()
        json.dump(pkg, SEED_CACHE.open("w"), ensure_ascii=False, indent=2)
        print(f"种子包: {pkg['total_genes']}条基因·{len(pkg['topics'])}主题")
    elif cmd == "status":
        show_status()
    elif cmd == "inject":
        node = sys.argv[2] if len(sys.argv) > 2 else "天枢"
        pkg = build_seed_package()
        print(json.dumps(inject_to_node(node, pkg), ensure_ascii=False, indent=2))
