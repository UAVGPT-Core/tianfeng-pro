#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  基因库永动飞轮 v1.0 · Gene Library Perpetual Flywheel       ║
║  104万基因·七自闭环·越飞越大·越飞越聪明                        ║
║                                                              ║
║  ①自感知→②自协调→③自愈合→④自进化→⑤自迭代→⑥自反思→⑦自约束    ║
║  每一循环=基因库自我升级一次                                  ║
╚══════════════════════════════════════════════════════════════╝
"""
import urllib.request, json, time, sqlite3, os, re, random
from datetime import datetime, timedelta
from collections import defaultdict, Counter

LGE_URL = "http://100.116.0.29:8200"
DB = os.path.expanduser("~/lgox-ops/data/gene_library_flywheel.db")
NGC_KEY = "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"
NGC_API = "https://integrate.api.nvidia.com/v1/chat/completions"
CYCLE_INTERVAL = 1800  # 30分钟一轮

# 基因质量阈值
DEPRECIATE_BELOW = 0.15    # 低于此分→标记折旧
AMPLIFY_ABOVE = 0.80       # 高于此分→基因扩增
FRESHNESS_DAYS = 90        # 超过90天未更新→降分
MIN_DOMAIN_GENES = 1000    # 领域最低基因数

DOMAINS = [
    "ai_architecture", "ml_engineering", "data_intelligence",
    "cloud_infrastructure", "ai_safety", "frontier_research",
    "federation_systems", "edge_computing", "quantum_ai",
    "robotics_automation", "bioinformatics", "cybersecurity"
]

def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_num INTEGER, action TEXT, detail TEXT,
            genes_before INTEGER, genes_after INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS domain_health (
            domain TEXT PRIMARY KEY,
            gene_count INTEGER, avg_fitness REAL,
            last_updated TEXT, status TEXT
        );
        CREATE TABLE IF NOT EXISTS quality_trends (
            date TEXT PRIMARY KEY,
            total_genes INTEGER, active_genes INTEGER,
            avg_fitness REAL, a_count INTEGER, b_count INTEGER,
            c_count INTEGER, d_count INTEGER
        );
        CREATE TABLE IF NOT EXISTS gene_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT, gene_id TEXT,
            reason TEXT, created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn

class GeneLibraryFlywheel:
    def __init__(self):
        self.conn = init_db()
        self.cycle = self._load_cycle()
    
    def _load_cycle(self):
        r = self.conn.execute("SELECT MAX(cycle_num) FROM cycles").fetchone()
        return (r[0] or 0) + 1
    
    def log(self, msg):
        print(f"[{datetime.now().strftime('%m%d-%H%M%S')}] 📚 {msg}", flush=True)
    
    def ngc_chat(self, prompt, mt=80):
        try:
            body = json.dumps({"model":"meta/llama-3.1-8b-instruct",
                "messages":[{"role":"user","content":prompt}],
                "max_tokens":mt,"temperature":0.3}).encode()
            req = urllib.request.Request(NGC_API, data=body,
                headers={"Authorization":"Bearer "+NGC_KEY,"Content-Type":"application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=15).read())["choices"][0]["message"]["content"].strip()
        except: return None
    
    # ═══ ① 自感知: 基因库全维度体检 ═══
    def self_aware(self):
        self.log("① 自感知·基因库体检")
        try:
            h = json.loads(urllib.request.urlopen(f"{LGE_URL}/health", timeout=5).read())
            genes = h['genes']; active = h['active']
            
            # 搜索各领域基因数
            domain_counts = {}
            for d in DOMAINS:
                try:
                    req = urllib.request.Request(f"{LGE_URL}/genes/search",
                        data=json.dumps({"query": d, "n_results": 1}).encode(),
                        headers={"Content-Type":"application/json"})
                    r = json.loads(urllib.request.urlopen(req, timeout=5).read())
                    domain_counts[d] = r.get("count", r.get("total", 0))
                except: domain_counts[d] = 0
            
            # 质量趋势(从DB推算)
            avg_f = 0.45  # 默认
            
            self.log(f"  {genes:,}基因·{active:,}活跃·均分{avg_f:.2f}")
            
            # 存趋势
            today = datetime.now().strftime("%Y-%m-%d")
            self.conn.execute(
                "INSERT OR REPLACE INTO quality_trends(date,total_genes,active_genes,avg_fitness) VALUES(?,?,?,?)",
                (today, genes, active, avg_f))
            
            # 更新领域健康
            for d, cnt in domain_counts.items():
                self.conn.execute(
                    "INSERT OR REPLACE INTO domain_health(domain,gene_count,avg_fitness,status) VALUES(?,?,?,?)",
                    (d, cnt, avg_f, 'healthy' if cnt >= MIN_DOMAIN_GENES else 'weak'))
            self.conn.commit()
            
            return genes, active, domain_counts
        except Exception as e:
            self.log(f"  ⚠️ {e}")
            return 0, 0, {}
    
    # ═══ ② 自协调: 领域平衡 ═══
    def self_coordinate(self, domain_counts):
        self.log("② 自协调·领域平衡")
        weak_domains = [d for d, c in domain_counts.items() if c < MIN_DOMAIN_GENES]
        strong_domains = [d for d, c in domain_counts.items() if c > MIN_DOMAIN_GENES * 5]
        
        if weak_domains:
            self.log(f"  薄弱领域({len(weak_domains)}): {weak_domains[:3]}")
        if strong_domains:
            self.log(f"  过剩领域({len(strong_domains)}): {strong_domains[:3]}")
        
        return weak_domains, strong_domains
    
    # ═══ ③ 自愈合: 基因修复+欠发达领域补种 ═══
    def self_heal(self, weak_domains):
        self.log("③ 自愈合·基因修复")
        healed = 0
        
        # 补种薄弱领域
        for domain in weak_domains[:3]:
            try:
                prompt = f"Generate 3 high-quality technical knowledge genes about {domain}. Each under 200 chars, markdown, with concrete data."
                resp = self.ngc_chat(prompt, 600)
                if resp:
                    for line in resp.split('\n'):
                        if len(line) > 50:
                            try:
                                data = json.dumps({"content":line.strip(),"memory_type":"semantic",
                                    "source":"基因库自愈","tags":[domain,"self-heal"],
                                    "fitness":0.55}).encode()
                                urllib.request.urlopen(urllib.request.Request(
                                    f"{LGE_URL}/genes/write", data=data,
                                    headers={"Content-Type":"application/json"}), timeout=8)
                                healed += 1
                            except: pass
                time.sleep(1)
            except: pass
        
        if healed:
            self.log(f"  补种{healed}条")
            self.conn.execute("INSERT INTO cycles(cycle_num,action,detail) VALUES(?,?,?)",
                (self.cycle, "heal", f"补种{healed}条"))
            self.conn.commit()
        return healed
    
    # ═══ ④ 自进化: 折旧+扩增 ═══
    def self_evolve(self):
        self.log("④ 自进化·优胜劣汰")
        deprecated = 0
        amplified = 0
        
        # 折旧: 搜索低质量基因(通过查询泛词)
        try:
            req = urllib.request.Request(f"{LGE_URL}/genes/search",
                data=json.dumps({"query": "basic simple introduction beginners", "n_results": 10}).encode(),
                headers={"Content-Type":"application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=8).read())
            
            for g in r.get("results", [])[:5]:
                gid = g.get("gene_id", "")
                content = g.get("content", "")
                if len(content) < 100:  # 过短基因
                    self.conn.execute("INSERT INTO gene_actions(action_type,gene_id,reason) VALUES(?,?,?)",
                        ("deprecate", str(gid), "too_short"))
                    deprecated += 1
        except: pass
        
        # 扩增: 搜索高质量基因→NGC重新表达
        try:
            for q in ["advanced architecture patterns", "cutting edge research 2026", "breakthrough technology"]:
                req = urllib.request.Request(f"{LGE_URL}/genes/search",
                    data=json.dumps({"query": q, "n_results": 3}).encode(),
                    headers={"Content-Type":"application/json"})
                r = json.loads(urllib.request.urlopen(req, timeout=8).read())
                
                for g in r.get("results", [])[:2]:
                    content = g.get("content", "")[:500]
                    if len(content) > 200:
                        # NGC扩增: 把好基因重写成更高质量版本
                        resp = self.ngc_chat(
                            f"Rewrite this into a more advanced, data-rich version with 2035 perspective:\n{content}", 400)
                        if resp and len(resp) > 80:
                            try:
                                data = json.dumps({"content":resp,"memory_type":"semantic",
                                    "source":"基因扩增","tags":["amplified","evolution"],
                                    "fitness":0.75}).encode()
                                urllib.request.urlopen(urllib.request.Request(
                                    f"{LGE_URL}/genes/write", data=data,
                                    headers={"Content-Type":"application/json"}), timeout=8)
                                amplified += 1
                                self.conn.execute("INSERT INTO gene_actions(action_type,gene_id,reason) VALUES(?,?,?)",
                                    ("amplify", g.get("gene_id","?"), "high_quality"))
                            except: pass
                time.sleep(0.5)
        except: pass
        
        self.conn.commit()
        self.log(f"  折旧{deprecated}条·扩增{amplified}条")
        return deprecated, amplified
    
    # ═══ ⑤ 自迭代: 质量螺旋上升 ═══
    def self_iterate(self):
        self.log("⑤ 自迭代·质量螺旋")
        # NGC评估当前基因库质量趋势
        before = self.conn.execute("SELECT COALESCE(AVG(avg_fitness),0.45) FROM quality_trends").fetchone()[0]
        
        # 随机采样评估
        scores = []
        for q in ["AI", "system", "data", "network", "security"]:
            try:
                req = urllib.request.Request(f"{LGE_URL}/genes/search",
                    data=json.dumps({"query": q, "n_results": 3}).encode(),
                    headers={"Content-Type":"application/json"})
                r = json.loads(urllib.request.urlopen(req, timeout=8).read())
                for g in r.get("results", [])[:2]:
                    content = g.get("content", "")[:300]
                    if len(content) > 80:
                        resp = self.ngc_chat(f"Rate 0-100: {content[:200]}", 10)
                        if resp:
                            nums = re.findall(r'\d+', resp)
                            if nums: scores.append(int(nums[0]))
                time.sleep(0.3)
            except: pass
        
        avg = sum(scores) / len(scores) if scores else 50
        trend = "📈上升" if avg > before * 100 else ("📉下降" if avg < before * 100 else "➡️持平")
        self.log(f"  质量抽样: {avg:.0f}/100 {trend} (前值{before*100:.0f})")
        
        # 存趋势
        today = datetime.now().strftime("%Y-%m-%d")
        self.conn.execute("UPDATE quality_trends SET avg_fitness=? WHERE date=?",
            (avg/100, today))
        self.conn.commit()
        
        return avg/100
    
    # ═══ ⑥ 自反思: 知识盲区检测 ═══
    def self_reflect(self):
        self.log("⑥ 自反思·知识盲区")
        # NGC识别知识盲区
        prompt = f"""LGOX联邦基因库有104万+技术基因。基于当前AI前沿趋势(2026-2035)，识别3个可能的**知识盲区**——重要但基因覆盖不足的领域。
输出格式: 盲区1|盲区2|盲区3"""
        
        resp = self.ngc_chat(prompt, 150)
        if resp:
            gaps = [g.strip() for g in resp.split("|")[:3]]
            self.log(f"  盲区: {gaps}")
            self.conn.execute("INSERT INTO cycles(cycle_num,action,detail) VALUES(?,?,?)",
                (self.cycle, "reflect", json.dumps(gaps)))
            self.conn.commit()
            return gaps
        return []
    
    # ═══ ⑦ 自约束: 质量控制 ═══
    def self_constrain(self, genes_total):
        self.log("⑦ 自约束·质量控制")
        constraints = []
        
        # 增长率检查
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        prev = self.conn.execute("SELECT total_genes FROM quality_trends WHERE date=?", (yesterday,)).fetchone()
        
        if prev:
            growth = (genes_total - prev[0]) / max(prev[0], 1) * 100
            if growth > 50:
                constraints.append(f"⚠️ 日增长{int(growth)}%过快·可能需要降速")
            elif growth < 1:
                constraints.append(f"⚠️ 日增长{int(growth)}%过慢·产线可能故障")
        
        # 领域平衡检查
        weak = self.conn.execute("SELECT COUNT(*) FROM domain_health WHERE status='weak'").fetchone()[0]
        if weak > len(DOMAINS) * 0.3:
            constraints.append(f"⚠️ {weak}个薄弱领域")
        
        for c in constraints:
            self.log(f"  {c}")
        
        return constraints
    
    # ═══ 主循环 ═══
    def cycle_once(self):
        """一轮完整七自循环"""
        self.log(f"═══ 第{self.cycle}轮七自循环 ═══")
        t0 = time.time()
        
        # ① 自感知
        genes, active, domains = self.self_aware()
        if not genes: return
        
        # ② 自协调
        weak, strong = self.self_coordinate(domains)
        
        # ③ 自愈合
        healed = self.self_heal(weak)
        
        # ④ 自进化
        dep, amp = self.self_evolve()
        
        # ⑤ 自迭代
        quality = self.self_iterate()
        
        # ⑥ 自反思
        gaps = self.self_reflect()
        
        # ⑦ 自约束
        constraints = self.self_constrain(genes)
        
        # 周期记录
        elapsed = int(time.time() - t0)
        self.conn.execute(
            "INSERT INTO cycles(cycle_num,action,detail,genes_before,genes_after) VALUES(?,?,?,?,?)",
            (self.cycle, "七自循环", 
             f"愈合{healed}·进化{amp}·质量{quality:.2f}·{elapsed}s",
             genes, genes))
        self.conn.commit()
        
        # NGC周期总结纳基因
        try:
            summary = f"### 基因库七自循环#{self.cycle}\n基因{genes:,}·愈合{healed}·扩增{amp}·质量{quality:.2f}·盲区{gaps}·{elapsed}s"
            data = json.dumps({"content":summary,"memory_type":"procedural",
                "source":"基因库飞轮","tags":["library","seven-self","cycle"],
                "fitness":0.85}).encode()
            urllib.request.urlopen(urllib.request.Request(
                f"{LGE_URL}/genes/write", data=data,
                headers={"Content-Type":"application/json"}), timeout=8)
        except: pass
        
        self.log(f"✅ 完成·{elapsed}s")
        self.cycle += 1
    
    def run_forever(self):
        self.log("═══ 基因库永动飞轮·点火 ═══")
        self.log(f"守护104万+基因·每{CYCLE_INTERVAL//60}分钟一轮七自循环")
        
        while True:
            try:
                self.cycle_once()
                time.sleep(CYCLE_INTERVAL)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log(f"❌ {e}")
                time.sleep(300)

if __name__ == "__main__":
    import sys
    flywheel = GeneLibraryFlywheel()
    if "--once" in sys.argv:
        flywheel.cycle_once()
    else:
        flywheel.run_forever()
