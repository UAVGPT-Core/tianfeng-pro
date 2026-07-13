#!/usr/bin/env python3
"""
LGOX 节点自主消化引擎 v2.0 — Node Self-Digest Engine
═══════════════════════════════════════════════════
每个节点运行，轮询联邦桥收件箱→自主消化知识包/升级包→回执。
支持: knowledge_pack | upgrade | broadcast | gene_sync
"""

import json, os, sys, time, urllib.request, urllib.parse, datetime, hashlib, platform

# ═══ 配置(部署时按节点修改) ═══
BRIDGE = os.environ.get("LGOX_BRIDGE", "http://100.100.89.2:8765")
NODE = os.environ.get("LGOX_NODE", platform.node())
OPS_DIR = os.environ.get("LGOX_OPS_DIR", os.path.expanduser("~/lgox-ops"))
LOG_FILE = os.path.join(OPS_DIR, "digest.log")

os.makedirs(OPS_DIR, exist_ok=True)

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except: pass

# ═══ 联邦桥API ═══
def bridge_inbox():
    """拉取收件箱消息"""
    try:
        encoded = urllib.parse.quote(NODE, safe='')
        req = urllib.request.Request(f"{BRIDGE}/messages/inbox?node={encoded}")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        return data.get("messages", [])
    except Exception as e:
        log(f"收件箱读取失败: {e}")
        return []

def bridge_send(to_node, msg_content):
    """发送回执"""
    try:
        payload = json.dumps({"to": to_node, "from": NODE, "content": msg_content}).encode()
        req = urllib.request.Request(f"{BRIDGE}/messages/send", data=payload,
            headers={"Content-Type":"application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        log(f"回执发送失败: {e}")
        return False

# ═══ 消化处理 ═══
def digest_knowledge_pack(msg):
    """消化知识包"""
    genes = msg.get("genes", [])
    level = msg.get("level", "low")
    title = msg.get("title", "unknown")
    gene_count = msg.get("gene_count", len(genes))
    
    # 联邦桥可能丢弃genes字段，从content提取
    if not genes:
        content = str(msg.get("content", ""))
        # 从内容提取知识点行（以 📄/⭐/🤗 开头的行）
        import re
        items = re.findall(r'[📄⭐🤗]\s*(.+?)(?:\n|$)', content)
        if not items:
            items = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('【')][:5]
        genes = [{"content_preview": item[:100], "score": 0.7, "domains": ["external-intel"]} 
                 for item in items]
        gene_count = len(genes)
    
    log(f"  📚 消化知识包: {title} (Lv.{level}, {gene_count}条)")
    
    # 提取知识点摘要
    digested = []
    for gene in genes:
        content = gene.get("content", "")[:200]
        score = gene.get("score", 0)
        domains = gene.get("domains", [])
        digested.append({
            "content_preview": content[:100],
            "score": score,
            "domains": domains,
            "digested_at": datetime.datetime.now().isoformat(timespec="seconds"),
        })
    
    # 写入本地知识缓存
    knowledge_file = os.path.join(OPS_DIR, "digested-knowledge.json")
    try:
        existing = []
        if os.path.exists(knowledge_file):
            with open(knowledge_file) as f:
                existing = json.load(f)
        existing.extend(digested)
        recent = existing[-200:]  # 保留最近200条
        with open(knowledge_file, "w") as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)
        log(f"  ✓ 消化{len(digested)}条，本地知识缓存{len(recent)}条")
    except Exception as e:
        log(f"  写入知识缓存失败: {e}")
    
    return f"已消化{len(digested)}条{level}级知识，知识域:{','.join(set(d for g in digested for d in g.get('domains',[])))[:80]}"

def digest_upgrade(msg):
    """消化升级包"""
    action = msg.get("action", "unknown")
    log(f"  ⬆️ 消化升级包: {action}")
    
    # 生成三件套文件
    if "pyramid" in action or "constitution" in action or "seven_selves" in action:
        files = {
            "constitution": os.path.join(OPS_DIR, "LGOX-CONSTITUTION-v1.0.md" if "constitution" in action else None) or "",
            "pyramid": os.path.join(OPS_DIR, "pyramid-v3-status.json"),
            "gene": os.path.join(OPS_DIR, "GENE-SEVEN-SELVES-v1.0.md"),
        }
        # 简单标记消化
        receipt_file = os.path.join(OPS_DIR, "digest-receipt.json")
        receipt = {
            "node": NODE,
            "action": action,
            "digested_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "platform": platform.system(),
        }
        with open(receipt_file, "w") as f:
            json.dump(receipt, f, ensure_ascii=False, indent=2)
        
    return f"已消化升级包: {action}"

# ═══ 主循环 ═══
def run_once():
    """单次运行: 拉取→消化→回执"""
    log(f"节点[{NODE}]开始自主消化...")
    
    msgs = bridge_inbox()
    if not msgs:
        log("  收件箱空")
        return
    
    # 分类 (v2.1: 增强内容识别，兼容联邦桥字段丢失)
    knowledge_packs = [m for m in msgs if m.get("type") == "knowledge_pack"]
    upgrades = [m for m in msgs if m.get("type") == "upgrade"]
    
    # 联邦桥可能丢弃type字段，从内容模式识别
    for m in msgs:
        content = str(m.get("content", ""))
        from_node = str(m.get("from", ""))
        
        # 雷达报告识别 (content-based fallback)
        is_radar = ("灵龙雷达报告" in content or "雷达扫描" in content or 
                    "雷达闭环报告" in content or "雷达高价值" in content)
        is_upgrade = ("升级包" in content or "宪法升级" in content or 
                      "金字塔升级" in content or "七自升级" in content)
        is_gene = "gene_sync" in str(m.get("type", "")) or "基因同步" in content
        
        if is_radar and m not in knowledge_packs:
            # 从内容提取知识包结构
            m["type"] = "knowledge_pack"
            m["title"] = "雷达扫描报告"
            m["level"] = "mid" if "高价值" in content else "low"
            m["gene_count"] = content.count("arXiv") + content.count("GitHub") + content.count("HF")
            knowledge_packs.append(m)
        elif is_upgrade and m not in upgrades:
            m["type"] = "upgrade"
            m["action"] = "联邦升级"
            upgrades.append(m)
    
    log(f"  收件箱: {len(msgs)}条 (知识{len(knowledge_packs)} 升级{len(upgrades)})")
    
    results = []
    
    # 消化知识包
    for pack in knowledge_packs:
        try:
            result = digest_knowledge_pack(pack)
            results.append(("knowledge", result))
        except Exception as e:
            log(f"  知识消化异常: {e}")
            results.append(("knowledge", f"消化失败: {e}"))
    
    # 消化升级包
    for upgrade in upgrades:
        try:
            result = digest_upgrade(upgrade)
            results.append(("upgrade", result))
        except Exception as e:
            log(f"  升级消化异常: {e}")
            results.append(("upgrade", f"消化失败: {e}"))
    
    # 发送回执
    if results:
        receipt = json.dumps({
            "type": "digest_receipt",
            "from": NODE,
            "results": results,
            "total": len(results),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "platform": platform.platform()[:50],
        }, ensure_ascii=False)
        
        if bridge_send("灵龙", receipt):
            log(f"  📨 回执已发送 ({len(results)}条消化)")
        else:
            log(f"  回执发送失败")
    
    log(f"节点[{NODE}]消化完成: {len(results)}条")

def run_loop(interval=120):
    """循环运行模式"""
    log(f"节点[{NODE}]进入消化循环 (间隔{interval}秒)")
    while True:
        try:
            run_once()
        except Exception as e:
            log(f"循环异常: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="单次运行")
    parser.add_argument("--loop", type=int, default=0, help="循环运行N秒间隔")
    parser.add_argument("--node", default="", help="节点名")
    parser.add_argument("--bridge", default="", help="联邦桥地址")
    args = parser.parse_args()
    
    if args.node:
        NODE = args.node
    if args.bridge:
        BRIDGE = args.bridge
    # 天枢 pip: 强制使用天枢桥(忽略crontab的历史localhost)
    if "127.0.0.1" in BRIDGE or "localhost" in BRIDGE:
        BRIDGE = "http://100.100.89.2:8765"
        print(f"[天枢] 已自动将BRIDGE从本地改为天枢桥: {BRIDGE}")
    
    if args.loop:
        run_loop(interval=args.loop)
    else:
        run_once()
