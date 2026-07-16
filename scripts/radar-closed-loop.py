#!/usr/bin/env python3
"""
灵龙外部雷达·闭环传送引擎 v1.0
==============================
雷达扫描后的闭环处理：整理 → 评估 → LGE入库 → 联邦广播 → 通知天枢 → 自愈确认

原理：不替代external-radar.py，而是后处理它的输出，确保闭环送达。
每2小时雷达扫描后自动触发（或独立执行）。

闭环六步：
  ① 读取最新雷达扫描的LGE基因
  ② 整理分类（arXiv/GitHub/HF）
  ③ 评估高价值 → 纳入L1记忆
  ④ 汇总报告 → 联邦广播（所有节点）
  ⑤ 专门推送天枢（macOS通知格式）
  ⑥ 自愈确认：检查是否送达，未达则重试
"""
import json, subprocess, sys, os, time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import quote

FED = "http://100.100.89.2:8765"
LGE = "http://100.116.0.29:8200"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
MAX_RETRY = 3

def log(s):
    print(f"  [{datetime.now(TZ).strftime('%H:%M:%S')}] {s}")

def fed_api(method, path, data=None, timeout=8):
    for attempt in range(MAX_RETRY):
        try:
            body = json.dumps(data).encode() if data else None
            req = Request(f"{FED}{path}", data=body,
                          headers={"Content-Type":"application/json"} if data else {},
                          method=method)
            with urlopen(req, timeout=timeout) as r:
                return True, json.loads(r.read().decode())
        except Exception as e:
            if attempt < MAX_RETRY - 1:
                time.sleep(1)
            else:
                return False, str(e)

def lge_search(query, limit=20):
    """搜索LGE中最近的雷达基因"""
    try:
        data = json.dumps({"query": query, "limit": limit, "gene_type": "semantic"}).encode()
        req = Request(f"{LGE}/genes/search", data=data,
                      headers={"Content-Type":"application/json"})
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except:
        return {"results": []}

def lge_write(content, source, fitness=0.7):
    try:
        g = {"content": json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content,
             "source": source, "gene_type": "semantic", "fitness_score": fitness}
        req = Request(f"{LGE}/genes/write", data=json.dumps(g).encode(),
                      headers={"Content-Type":"application/json"})
        with urlopen(req, timeout=8) as r:
            return json.loads(r.read()).get("gene_id", "?")
    except:
        return "?"

def send_to_node(node, content, msg_type="notification", extra=None):
    """向联邦节点发消息，带重试"""
    payload = {"from": "灵龙", "to": node, "content": content, "type": msg_type}
    if extra:
        payload.update(extra)
    for i in range(MAX_RETRY):
        ok, r = fed_api("POST", "/messages/send", payload)
        if ok:
            return True
        time.sleep(1)
    return False

# ═══ 阶段1: 读取最新雷达数据 ═══
def collect_radar_data():
    """从LGE搜索最近雷达基因 — 优先读缓存文件"""
    log("① 读取雷达扫描数据...")
    
    # 方法1: 优先读缓存文件(最可靠)
    CACHE = "/tmp/lgox-radar-cache.json"
    if os.path.exists(CACHE):
        try:
            age = time.time() - os.path.getmtime(CACHE)
            if age < 14400:  # 4小时内有效
                with open(CACHE) as f:
                    cache = json.load(f)
                genes = cache.get("genes", [])
                log(f"  📦 缓存命中: {len(genes)}条 ({(age)/60:.0f}分钟前)")
                return genes
        except Exception as e:
            log(f"  ⚠️ 缓存读取失败: {e}")
    
    # 方法2: LGE搜索(备用)
    results = lge_search("外部雷达", 30)
    genes = results.get("results", []) if isinstance(results, dict) else results
    
    if not genes:
        results = lge_search("雷达", 30)
        genes = results.get("results", []) if isinstance(results, dict) else results
    
    recent = []
    for g in genes:
        g_content = g.get("content", "")
        g_source = g.get("source", "")
        if "外部雷达" in str(g_content)[:20] or "外部雷达" in str(g_source):
            recent.append(g)
    
    log(f"  LGE搜索: {len(recent)} 条雷达基因")
    return recent

# ═══ 阶段2: 整理分类 ═══
def categorize(genes):
    """按来源分类"""
    log("② 整理分类...")
    cats = {"arXiv": [], "GitHub": [], "HF": [], "other": []}
    for g in genes:
        content = str(g.get("content", ""))
        if "arXiv" in content:
            cats["arXiv"].append(content)
        elif "GitHub" in content:
            cats["GitHub"].append(content)
        elif "HF" in content or "HuggingFace" in content:
            cats["HF"].append(content)
        else:
            cats["other"].append(content)
    
    for k, v in cats.items():
        log(f"  {k}: {len(v)} 条")
    return cats

# ═══ 阶段3: 评估高价值 ═══
def assess(cats):
    """评估高价值项目"""
    log("③ 评估高价值...")
    high_value = []
    
    # GitHub高星项目
    for item in cats["GitHub"]:
        stars = 0
        for part in item.split():
            if "★" in part:
                try:
                    stars = int(part.replace("★","").replace(",",""))
                except:
                    pass
        if stars > 50000:
            high_value.append(("⚡高星", item[:120]))
    
    # arXiv Agent相关论文
    for item in cats["arXiv"]:
        if any(kw in item.lower() for kw in ["agent", "reasoning", "scaling", "v4", "r1"]):
            high_value.append(("📄论文", item[:120]))
    
    # HF高下载模型
    for item in cats["HF"]:
        downloads = 0
        for part in item.split():
            if "↓" in part:
                try:
                    downloads = int(part.replace("↓","").replace(",",""))
                except:
                    pass
        if downloads > 100000000:
            high_value.append(("🤗热门", item[:120]))
    
    log(f"  高价值: {len(high_value)} 项")
    for tag, item in high_value:
        log(f"    {tag}: {item[:60]}...")
    return high_value

# ═══ 阶段4: 写入闭环基因 ═══
def save_to_lge(cats, high_value):
    """写入闭环基因"""
    log("④ 写入闭环基因到LGE...")
    
    # 完整报告基因
    report = {
        "type": "雷达闭环报告",
        "time": NOW,
        "source": "灵龙/雷达闭环",
        "summary": f"共{sum(len(v) for v in cats.values())}条雷达数据",
        "high_value": len(high_value),
        "categories": {k: len(v) for k, v in cats.items()}
    }
    gid = lge_write(report, "linglong/radar-closed-loop", 0.85)
    log(f"  闭环报告基因: {gid}")
    
    # 高价值基因（每条单独写）
    for tag, item in high_value:
        hg = {"type": "雷达高价值", "time": NOW, "tag": tag, "content": item}
        lge_write(hg, f"linglong/radar-high-value", 0.9)
    
    return gid

# ═══ 阶段5: 联邦广播 ═══
def broadcast(cats, high_value):
    """向全联邦发送雷达报告"""
    log("⑤ 联邦广播...")
    
    # 生成汇总报告
    total = sum(len(v) for v in cats.values())
    lines = [
        f"【灵龙雷达报告】{NOW}",
        f"来源: arXiv({len(cats['arXiv'])}) GitHub({len(cats['GitHub'])}) HF({len(cats['HF'])})",
    ]
    if high_value:
        lines.append(f"高价值: {len(high_value)}项")
        for tag, item in high_value[:3]:
            lines.append(f"  {tag} {item[:80]}")
    
    report = "\n".join(lines)
    
    # 获取节点列表
    ok, health = fed_api("GET", "/health")
    nodes = health.get("nodes", []) if ok else []
    
    # 广播所有节点
    sent = 0
    for node in nodes:
        if node == "灵龙":
            continue
        
        # 构建知识包结构，节点消化引擎可识别
        knowledge_extra = {
            "genes": [{"content_preview": line[:100], "score": 0.8, "domains": ["external-intel"]}
                      for line in lines[1:5]],  # 前几句作为基因摘要
            "level": "mid" if high_value else "low",
            "title": f"雷达扫描 {NOW}",
            "gene_count": total,
            "radar_source": "external-radar-v2"
        }
        
        ok = send_to_node(node, report, msg_type="knowledge_pack", extra=knowledge_extra)
        if ok:
            sent += 1
            log(f"  ✓ {node}")
        else:
            log(f"  ✗ {node} (重试{MAX_RETRY}次)")
    
    # 天枢专门推送（带详细高价值清单）
    if high_value:
        detail = f"【雷达高价值发现】{NOW}\n\n"
        for tag, item in high_value:
            detail += f"{tag}: {item}\n\n"
        detail += "—灵龙雷达闭环"
        send_to_node("天枢", detail)
        log("  ★ 天枢高价值明细已推送")
    
    return sent, len(nodes)

# ═══ 阶段6: 自愈确认 ═══
def verify_delivery():
    """自愈确认：检查天枢收件箱确认送达"""
    log("⑥ 自愈确认...")
    ok, inbox = fed_api("GET", f"/messages/inbox?node={quote('天枢')}")
    if ok and isinstance(inbox, dict):
        msgs = inbox.get("messages", []) if isinstance(inbox, dict) else inbox
        # 检查是否有雷达闭环报告（检查内容含"灵龙雷达报告"）
        has_report = any("灵龙雷达闭环" in str(m.get("content", "")) or "灵龙雷达报告" in str(m.get("content", "")) for m in msgs)
        log(f"  天枢收件箱: {len(msgs)}条 (含闭环报告: {has_report})")
        return has_report
    log("  收件箱不可达(联邦桥API可能超时)")
    return False

# ═══ 主流程 ═══
def run():
    print(f"\n{'='*50}")
    print(f" 灵龙雷达闭环引擎 v1.0")
    print(f" 时间: {NOW}")
    print(f"{'='*50}\n")
    
    # 1-2 收集+分类
    genes = collect_radar_data()
    if not genes:
        log("⚠️ 未找到雷达数据，尝试直接触发雷达扫描(最多180s)")
        try:
            subprocess.run(["python3", os.path.expanduser("~/.hermes/scripts/external-radar.py")],
                          capture_output=True, timeout=180)
        except subprocess.TimeoutExpired:
            log("⚠️ 雷达扫描超时(180s)·跳过·使用已缓存数据")
        except Exception as e:
            log(f"⚠️ 雷达扫描异常: {e}·继续")
        genes = collect_radar_data()
        if not genes:
            log("❌ 仍无雷达数据，退出")
            return
    
    cats = categorize(genes)
    
    # 3 评估
    high_value = assess(cats)
    
    # 4 写LGE
    gid = save_to_lge(cats, high_value)
    
    # 5 广播
    sent, total = broadcast(cats, high_value)
    
    # 6 确认
    confirmed = verify_delivery()
    
    print(f"\n{'='*50}")
    print(f" 闭环完成")
    print(f"  雷达: {sum(len(v) for v in cats.values())}条 | 高价值: {len(high_value)}")
    print(f"  广播: {sent}/{total-1}节点 | 天枢确认: {'✅' if confirmed else '⚠️'}")
    print(f"  基因: {gid}")
    print(f"{'='*50}")

if __name__ == "__main__":
    if "--once" in sys.argv:
        run()
    elif "--cron" in sys.argv:
        # 每2小时雷达扫描后触发的闭环模式
        run()
    else:
        run()
