#!/usr/bin/env python3
"""
小枢·超个体信号进化引擎 v1.1 — 2035永动闭环
═══════════════════════════════════════════
七自飞轮:
  自感知 → 自协调 → 自愈合 → 自进化 → 自迭代 → 自反思 → 自约束

数据源:
  TickDB: 从tickdb-quote.json(天枢cron每2min拉)及signals-v2.json
  Wind: 从signals-v2.json及signals.html在线数据(备胎)
═══════════════════════════════════════════
"""

import json, os, time, urllib.request, hashlib
from datetime import datetime
from pathlib import Path

HOME = os.path.expanduser("~")
LGE = "http://100.116.0.29:8200"
VOD_URL = "https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions"

# 读VOD Key
VOD_KEY = ""
for p in [os.path.expanduser("~/.hermes/.env"), os.path.expanduser("~/.env")]:
    if os.path.exists(p):
        for line in open(p):
            if "BAIDU_VOD_KEY" in line:
                VOD_KEY = line.split("=",1)[1].strip().strip('"').strip("'")
                break
    if VOD_KEY: break

LOG = os.path.join(HOME, "lgox-ops/logs/xiaoshu-evo.log")
STATE_FILE = os.path.join(HOME, "lgox-ops/data/xiaoshu-evo-state.json")
SIGNALS_FILE = "/Volumes/990Pro/public-web/signals-v2.json"
TICKDB_FILE = "/Volumes/990Pro/public-web/tickdb-quote.json"

# 灵龙备胎:从联邦桥HTTP读
TICKDB_HTTP = "http://100.100.89.2:80/tickdb-quote.json"
SIGNALS_HTTP = "http://100.100.89.2:80/signals-v2.json"
# 备胎:公网
TICKDB_PUBLIC = "https://stock.uavgpt.com/tickdb-quote.json"
SIGNALS_PUBLIC = "https://stock.uavgpt.com/signals-v2.json"

def log(m):
    with open(LOG, "a") as f: f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {m}\n")
    print(m)

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except: return {"runs":0,"signals_generated":0,"genes_written":0,"avg_quality":50,"last_run":None,"errors":[]}

def save_state(s):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f: json.dump(s, f, indent=2)

state = load_state()

# ══════════════════════════════════════════
# ① 自感知: 行情采集
# ══════════════════════════════════════════

def collect_market():
    """从天枢的静态数据文件读行情"""
    log("📡 行情采集...")
    data = {"tickdb": {}, "signals": {}}
    
    # TickDB: 从天枢读(本地文件或HTTP)
    td_data = None
    if os.path.exists(TICKDB_FILE):
        try:
            with open(TICKDB_FILE) as f: td_data = json.load(f)
        except: pass
    if not td_data:
        for url in [TICKDB_HTTP, TICKDB_PUBLIC]:
            try:
                req = urllib.request.Request(url)
                resp = urllib.request.urlopen(req, timeout=5)
                td_data = json.loads(resp.read())
                if td_data: break
            except: pass
    
    if td_data:
        for item in td_data.get("data", []):
            sym = item["symbol"]
            data["tickdb"][sym] = {
                "price": float(item.get("last_price", 0)),
                "change_pct": float(item.get("price_change_percent_24h", 0)),
                "volume": int(item.get("volume_24h", 0)),
                "name": item.get("name", sym),
                "source": "tickdb"
            }
    
    # A股: 从signals-v2.json读(本地或HTTP)
    sig_data = None
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE) as f: sig_data = json.load(f)
        except: pass
    if not sig_data:
        for url in [SIGNALS_HTTP, SIGNALS_PUBLIC]:
            try:
                req = urllib.request.Request(url)
                resp = urllib.request.urlopen(req, timeout=5)
                sig_data = json.loads(resp.read())
                if sig_data: break
            except: pass
    if sig_data:
        for s in sig_data[:30] if isinstance(sig_data, list) else sig_data.get("data",[])[:30]:
            code = s.get("ts_code", s.get("symbol", ""))
            if code:
                data["signals"][code] = {
                    "price": float(s.get("current_price", s.get("price", 0))),
                    "change_pct": float(s.get("change_pct", 0)),
                    "score": s.get("composite_score", 50),
                    "name": s.get("name", code),
                    "signal": s.get("signal_type", "neutral"),
                    "source": "wind"
                }
    
    total = len(data["tickdb"]) + len(data["signals"])
    log(f"  TickDB:{len(data['tickdb'])}只 | A股信号:{len(data['signals'])}只 | 共{total}只")
    return data

# ══════════════════════════════════════════
# ② 自协调: 多维信号分析
# ══════════════════════════════════════════

def analyze(market):
    """信号融合分析"""
    log("🧠 信号融合...")
    signals = []
    
    # TickDB品种信号
    for sym, info in market["tickdb"].items():
        p = info.get("price", 0)
        if not p: continue
        score = 50
        chg = info.get("change_pct", 0)
        if chg > 2: score += 10
        elif chg > 1: score += 5
        elif chg > 0: score += 2
        elif chg < -2: score -= 10
        elif chg < -1: score -= 5
        elif chg < 0: score -= 2
        
        vol = info.get("volume", 0)
        if vol > 50000000: score += 5
        elif vol > 10000000: score += 2
        
        sig_type = "buy" if score >= 60 else ("sell" if score <= 40 else "neutral")
        signals.append({
            "symbol": sym, "name": info.get("name", sym),
            "price": p, "change_pct": chg, "score": min(100, max(0, score)),
            "signal": sig_type, "source": "tickdb",
            "timestamp": datetime.now().isoformat()
        })
    
    # A股信号增强
    for code, info in market["signals"].items():
        p = info.get("price", 0)
        if not p: continue
        orig_score = info.get("score", 50)
        sig_type = info.get("signal", "neutral")
        signals.append({
            "symbol": code, "name": info.get("name", code),
            "price": p, "change_pct": info.get("change_pct", 0),
            "score": orig_score, "signal": sig_type,
            "source": "wind+" + info.get("source", ""),
            "timestamp": datetime.now().isoformat()
        })
    
    return signals

# ══════════════════════════════════════════
# ③ 自进化: AI品质提升
# ══════════════════════════════════════════

def ai_enhance(signals):
    """Top信号AI增强"""
    if not signals or not VOD_KEY: return signals
    
    top = sorted(signals, key=lambda x: abs(x["score"] - 50), reverse=True)[:5]
    for s in top:
        try:
            prompt = f"分析{s.get('name',s['symbol'])}:价格${s['price']},涨跌{s['change_pct']:.1f}%,信号{s['signal']}。只说结论(15字内)。"
            req = urllib.request.Request(VOD_URL,
                data=json.dumps({"model":"deepseek-v4-flash","messages":[
                    {"role":"system","content":"你是小枢AI,简洁精准。"},
                    {"role":"user","content":prompt}
                ],"max_tokens":32,"temperature":0.1}).encode(),
                headers={"Content-Type":"application/json","Authorization":"Bearer "+VOD_KEY})
            resp = urllib.request.urlopen(req, timeout=15)
            text = json.loads(resp.read()).get("choices",[{}])[0].get("message",{}).get("content","")
            s["insight"] = text.strip()[:80]
        except:
            s["insight"] = ""
    
    return signals

# ══════════════════════════════════════════
# ④ 自迭代: 基因写入 + 小枢记忆
# ══════════════════════════════════════════

def write_lge(signals):
    """信号写入LGE(小枢用)"""
    count = 0
    for s in signals[:15]:
        try:
            tag = s["symbol"].split(".")[0].lower() if "." in s["symbol"] else s["symbol"][:4].lower()
            payload = json.dumps({
                "content": json.dumps({
                    "type":"xiaoshu-signal","symbol":s["symbol"],"name":s.get("name",""),
                    "price":s["price"],"score":s["score"],"signal":s["signal"],
                    "source":s["source"],"insight":s.get("insight",""),
                }, ensure_ascii=False),
                "memory_type":"procedural","source":"xiaoshu-evo",
                "tags":["signal","xiaoshu",s["signal"],tag]
            })
            urllib.request.urlopen(urllib.request.Request(LGE+"/genes/write",
                data=payload.encode(),headers={"Content-Type":"application/json"}), timeout=5)
            count += 1
        except: pass
    return count

# ══════════════════════════════════════════
# ⑤ 自愈合+自反思: 状态报告
# ══════════════════════════════════════════

def report():
    try:
        content = json.dumps({"type":"xiaoshu-evo-report","runs":state["runs"],
            "signals":state["signals_generated"],"genes":state["genes_written"],
            "quality":state["avg_quality"],"version":"v1.1"}, ensure_ascii=False)
        payload = json.dumps({"content":content,"memory_type":"semantic",
            "source":"xiaoshu-evo-report","tags":["xiaoshu","evo","report"]})
        urllib.request.urlopen(urllib.request.Request(LGE+"/genes/write",
            data=payload.encode(),headers={"Content-Type":"application/json"}), timeout=5)
    except: pass

# ══════════════════════════════════════════
# 入口
# ══════════════════════════════════════════

def evolve():
    global state
    state["runs"] += 1
    log(f"\n{'='*40}\n🔄 小枢超个体进化 #{state['runs']}")
    
    market = collect_market()
    signals = analyze(market)
    log(f"  📊 融合{len(signals)}个信号")
    
    signals = ai_enhance(signals)
    ai_n = sum(1 for s in signals if s.get("insight"))
    log(f"  🤖 AI增强{ai_n}个")
    
    written = write_lge(signals)
    state["signals_generated"] += len(signals)
    state["genes_written"] += written
    log(f"  🧬 写入{written}条基因")
    
    quality = min(100, 50 + written * 5)
    state["avg_quality"] = (state["avg_quality"] * (state["runs"] - 1) + quality) // state["runs"]
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    
    report()
    log(f"🏁 质量:{state['avg_quality']}% 信号:{state['signals_generated']} 基因:{state['genes_written']}")

if __name__ == "__main__":
    evolve()
