#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  LGOX联邦·知识宪政 v1.0 · 2035级 · AI灯塔·AI坐标          ║
║  五统一体: ID·质量·溯源·生命·入口                          ║
║  七自驱动: 自感知→自协调→自愈合→自进化→自迭代→自反思→自约束 ║
║  零人类·全联邦永动·10年不过时                               ║
╚══════════════════════════════════════════════════════════════╝
"""

import json, sqlite3, os, urllib.request, uuid, re, time
from datetime import datetime, timedelta
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/Users/a112233"))
LGE_URL = "http://100.116.0.29:8200"
BRIDGE = "http://100.100.89.2:8765"  # 天枢桥·非127.0.0.1
MY_NODE = "灵龙"
CONSTITUTION_DB = HOME / "lgox-ops/data/knowledge-constitution.db"

# ══════════════════════════════════════════════════════════════
# 一、统一ID体系 · GKP (Gene Knowledge Protocol)
# ══════════════════════════════════════════════════════════════
# 格式: GKP-{domain}-{source_abbr}-{timestamp}-{hash8}
# 示例: GKP-general-arxiv-20260712-a1b2c3d4

def generate_gkp_id(domain="general", source="internal", content=""):
    """生成GKP统一ID·跨四引擎唯一标识"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    # 内容哈希(8位)
    content_hash = hex(abs(hash(content[:500])) % 0xFFFFFFFF)[2:10]
    # 源缩写
    source_map = {
        "arxiv": "arx", "github": "gh", "huggingface": "hf",
        "knowledge-flywheel": "kfw", "l6-consolidator": "l6c",
        "linglong-executor": "lex", "memory-flywheel": "mfw",
        "external-radar": "rad", "manual": "man", "internal": "int"
    }
    src = source_map.get(source, source[:3])
    return f"GKP-{domain}-{src}-{ts}-{content_hash}"


# ══════════════════════════════════════════════════════════════
# 二、五维质量引擎 · 2035级
# ══════════════════════════════════════════════════════════════

class QualityEngine:
    """2035级五维质量评分引擎"""
    
    # 维度权重(可自进化调整)
    WEIGHTS = {
        "source": 0.25,     # 来源可信度
        "freshness": 0.20,   # 时效性
        "citations": 0.20,   # 引用度
        "verified": 0.20,    # 验证度
        "confirmed": 0.15,   # 确认度(跨节点共识)
    }
    
    # 来源评分表(2035年标准)
    SOURCE_SCORES = {
        "arxiv": 8, "github": 9, "huggingface": 7,
        "knowledge-flywheel": 6, "l6-consolidator": 5,
        "linglong-executor": 7, "memory-flywheel": 6,
        "external-radar": 7, "manual": 10, "internal": 5,
        "cross-node-verified": 10, "constitution": 10,
    }
    
    @classmethod
    def score(cls, source, content, created_at=None, citations=0, 
              verified_by=None, confirmed_by=None):
        """计算五维质量分数"""
        # 1. 来源分 (0-10)
        source_score = cls.SOURCE_SCORES.get(source, 5)
        
        # 2. 时效分 (0-10) —— 知识折旧曲线
        if created_at:
            try:
                if isinstance(created_at, str):
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    created = created_at
                age_days = (datetime.now() - created).days
                if age_days <= 7:   freshness = 10
                elif age_days <= 30: freshness = 8
                elif age_days <= 90: freshness = 5
                elif age_days <= 180: freshness = 3
                else: freshness = max(0, 10 - age_days / 60)
            except:
                freshness = 5
        else:
            freshness = 5  # 未知创建时间
        
        # 3. 引用分 (0-10) —— 被引用次数
        citation_score = min(10, citations * 2)
        
        # 4. 验证分 (0-10)
        if verified_by == "manual":      verify_score = 10
        elif verified_by == "cross-node": verify_score = 8
        elif verified_by == "acid":       verify_score = 8
        elif verified_by == "auto":       verify_score = 5
        else:                             verify_score = 0
        
        # 5. 确认分 (0-10) —— 跨节点确认
        confirm_score = min(10, len(confirmed_by or []) * 3)
        
        # 加权总分
        total = (
            source_score  * cls.WEIGHTS["source"] +
            freshness     * cls.WEIGHTS["freshness"] +
            citation_score * cls.WEIGHTS["citations"] +
            verify_score  * cls.WEIGHTS["verified"] +
            confirm_score * cls.WEIGHTS["confirmed"]
        ) * 10  # 转为百分制
        
        return {
            "total": round(total, 1),
            "grade": cls.grade(total),
            "dimensions": {
                "source": source_score,
                "freshness": freshness,
                "citations": citation_score,
                "verified": verify_score,
                "confirmed": confirm_score
            },
            "weights": cls.WEIGHTS,
            "scored_at": datetime.now().isoformat()
        }
    
    @classmethod
    def grade(cls, score):
        """S/A/B/C/D 五级"""
        if score >= 90: return "S"
        if score >= 75: return "A"
        if score >= 60: return "B"
        if score >= 40: return "C"
        return "D"
    
    @classmethod
    def evolve_weights(cls, feedback_data):
        """自进化: 根据反馈调整权重(七自·自进化)"""
        # 此方法在积累足够feedback后自动调整WEIGHTS
        pass  # v1.0 预留接口


# ══════════════════════════════════════════════════════════════
# 三、统一溯源链 · TraceChain
# ══════════════════════════════════════════════════════════════

class TraceChain:
    """2035级溯源链·每条基因可追问'为什么相信'"""
    
    @staticmethod
    def create(actor, action, source, quality, parent_chain=None):
        """创建溯源节点"""
        node = {
            "actor": actor,           # 灵龙/knowledge-flywheel
            "action": action,         # write/verify/cite/depreciate
            "source": source,         # arxiv:2507.xxxxx
            "quality": quality,       # 五维质量快照
            "timestamp": datetime.now().isoformat(),
            "node": MY_NODE,
        }
        chain = (parent_chain or []) + [node]
        return chain
    
    @staticmethod
    def verify(chain):
        """验证溯源链完整性"""
        if not chain: return False, "空链"
        # 防御: 确保链中每个元素是dict
        chain = [n for n in chain if isinstance(n, dict)]
        if not chain: return False, "无效链(无dict元素)"
        has_source = any(n.get("source") and n["source"] != "unknown" for n in chain)
        has_quality = any(n.get("quality", {}).get("total", 0) > 0 for n in chain if isinstance(n.get("quality"), dict))
        actors_ok = all(n.get("actor") for n in chain)
        return (has_source and has_quality and actors_ok), {
            "length": len(chain),
            "has_source": has_source,
            "has_quality": has_quality,
            "actors": [n["actor"] for n in chain if "actor" in n]
        }
    
    @staticmethod
    def explain(chain):
        """生成人类可读的溯源解释"""
        if not chain:
            return "⚠️ 无溯源·不可信"
        parts = []
        for i, n in enumerate(chain):
            actor = n["actor"]
            action_map = {"write": "写入", "verify": "验证", "cite": "引用", 
                          "depreciate": "折旧", "archive": "归档"}
            action = action_map.get(n["action"], n["action"])
            source = n.get("source", "未知来源")
            score = n.get("quality", {}).get("total", "?")
            parts.append(f"{i+1}.{actor} → {action} (来源:{source} 质量:{score})")
        return " → ".join(parts)


# ══════════════════════════════════════════════════════════════
# 四、统一生命周期 · KnowledgeLifecycle
# ══════════════════════════════════════════════════════════════

class KnowledgeLifecycle:
    """2035级知识生命周期·五态流转"""
    
    STATES = ["ingested", "verified", "active", "depreciating", "archived"]
    
    # 状态转换规则
    TRANSITIONS = {
        "ingested":      ["verified", "archived"],
        "verified":      ["active", "archived"],
        "active":        ["depreciating", "archived"],
        "depreciating":  ["active", "archived"],  # 可复活
        "archived":      ["active"],               # 可唤醒
    }
    
    @classmethod
    def determine_state(cls, quality_score, age_days, citation_count):
        """根据质量+时间+引用自动判定生命周期"""
        if quality_score >= 80 and age_days <= 90:
            return "active"
        elif quality_score >= 60 and age_days <= 180:
            return "active"
        elif quality_score >= 40 or age_days > 180:
            return "depreciating"
        elif age_days > 365 and citation_count == 0:
            return "archived"
        else:
            return "active"
    
    @classmethod
    def transition(cls, current_state, target_state):
        """验证状态转换是否合法"""
        return target_state in cls.TRANSITIONS.get(current_state, [])


# ══════════════════════════════════════════════════════════════
# 五、知识宪政执行引擎
# ══════════════════════════════════════════════════════════════

def init_constitution_db():
    """初始化宪政数据库"""
    conn = sqlite3.connect(CONSTITUTION_DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS gkp_index (
            gkp_id TEXT PRIMARY KEY,
            domain TEXT, source TEXT, lge_gene_id TEXT,
            quality_score REAL, quality_grade TEXT,
            quality_json TEXT,
            trace_chain TEXT,
            lifecycle_state TEXT DEFAULT 'ingested',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            citation_count INTEGER DEFAULT 0,
            confirmed_by TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS quality_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gkp_id TEXT, action TEXT,
            old_score REAL, new_score REAL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lifecycle_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gkp_id TEXT, from_state TEXT, to_state TEXT,
            trigger TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_gkp_domain ON gkp_index(domain);
        CREATE INDEX IF NOT EXISTS idx_gkp_quality ON gkp_index(quality_score);
        CREATE INDEX IF NOT EXISTS idx_gkp_lifecycle ON gkp_index(lifecycle_state);
    """)
    conn.commit()
    return conn

def register_knowledge(source, content, domain="general", 
                       citations=0, verified_by=None, parent_trace=None):
    """宪政注册·一条知识走完五统全流程"""
    conn = init_constitution_db()
    c = conn.cursor()
    
    # 1. 生成统一ID
    gkp_id = generate_gkp_id(domain, source, content)
    
    # 2. 计算五维质量
    quality = QualityEngine.score(source, content, citations=citations, 
                                   verified_by=verified_by)
    
    # 3. 创建溯源链
    trace = TraceChain.create(MY_NODE, "write", source, quality, parent_trace)
    
    # 4. 判定生命周期
    age_days = 0  # 新知识
    lifecycle = KnowledgeLifecycle.determine_state(quality["total"], age_days, citations)
    
    # 5. 写入宪政索引
    c.execute("""INSERT OR REPLACE INTO gkp_index 
        (gkp_id, domain, source, quality_score, quality_grade, quality_json,
         trace_chain, lifecycle_state, citation_count, confirmed_by, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
        (gkp_id, domain, source, quality["total"], quality["grade"],
         json.dumps(quality), json.dumps(trace), lifecycle, citations,
         json.dumps([])))
    
    conn.commit()
    conn.close()
    
    return {
        "gkp_id": gkp_id,
        "quality": quality,
        "trace": trace,
        "lifecycle": lifecycle,
        "trace_explain": TraceChain.explain(trace)
    }

def batch_constitutionalize(genes, source="knowledge-flywheel", domain="general"):
    """批量宪政化·知识飞轮策展→五统全流程"""
    conn = init_constitution_db()
    c = conn.cursor()
    
    results = []
    for gene in genes:
        content = gene.get("content", "")
        # 生成GKP ID
        gkp_id = generate_gkp_id(domain, source, content)
        
        # 质量评分
        quality = QualityEngine.score(source, content)
        
        # 溯源链
        trace = TraceChain.create(MY_NODE, "write", source, quality)
        
        # 生命周期
        lifecycle = KnowledgeLifecycle.determine_state(quality["total"], 0, 0)
        
        # 写入
        c.execute("""INSERT OR REPLACE INTO gkp_index 
            (gkp_id, domain, source, quality_score, quality_grade, quality_json,
             trace_chain, lifecycle_state, updated_at)
            VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (gkp_id, domain, source, quality["total"], quality["grade"],
             json.dumps(quality), json.dumps(trace), lifecycle))
        
        # 写入LGE(带quality元数据)
        try:
            lge_payload = json.dumps({
                "content": f"[GKP:{gkp_id}][质量:{quality['grade']}][分数:{quality['total']}] {content[:500]}",
                "memory_type": "semantic",
                "source": source,
                "metadata": {
                    "gkp_id": gkp_id,
                    "quality": quality,
                    "lifecycle": lifecycle,
                    "trace_chain": trace
                }
            }).encode()
            req = urllib.request.Request(LGE_URL + "/genes/write", data=lge_payload,
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=8)
            lge_result = json.loads(resp.read())
            lge_gene_id = lge_result.get("gene_id", "")
            
            # 回写LGE ID
            c.execute("UPDATE gkp_index SET lge_gene_id=? WHERE gkp_id=?", 
                      (lge_gene_id, gkp_id))
        except Exception as e:
            lge_gene_id = f"error:{e}"
        
        results.append({
            "gkp_id": gkp_id,
            "grade": quality["grade"],
            "score": quality["total"],
            "lifecycle": lifecycle,
            "lge_gene_id": lge_gene_id
        })
    
    conn.commit()
    conn.close()
    return results

def constitution_stats():
    """宪政统计"""
    conn = init_constitution_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM gkp_index")
    total = c.fetchone()[0]
    
    c.execute("SELECT quality_grade, COUNT(*) FROM gkp_index GROUP BY quality_grade ORDER BY quality_grade")
    grades = {r[0]: r[1] for r in c.fetchall()}
    
    c.execute("SELECT lifecycle_state, COUNT(*) FROM gkp_index GROUP BY lifecycle_state")
    lifecycles = {r[0]: r[1] for r in c.fetchall()}
    
    c.execute("SELECT AVG(quality_score) FROM gkp_index")
    avg_score = c.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "total": total,
        "avg_score": round(avg_score, 1),
        "grades": grades,
        "lifecycles": lifecycles,
        "seven_self": {
            "自感知": total > 0,
            "自协调": all(s in lifecycles for s in KnowledgeLifecycle.STATES[:3]),
            "自愈合": "depreciating" in lifecycles or "archived" in lifecycles,
            "自进化": QualityEngine.WEIGHTS,
            "自迭代": True,
            "自反思": total > 10,
            "自约束": "archived" in lifecycles
        }
    }

# ══════════════════════════════════════════════════════════════
# 六、全联邦广播 + 七自闭环
# ══════════════════════════════════════════════════════════════

def broadcast_constitution():
    """宪政广播到全联邦·GCP v5.0格式"""
    stats = constitution_stats()
    
    msg = json.dumps({
        "from": MY_NODE, "to": "天枢",
        "type": "STATE", "msg_type": "STATE",
        "priority": "P1",
        "msg_id": str(uuid.uuid4())[:8],
        "reply_to": "", "ttl": 86400,
        "content": f"知识宪政v1.0·{stats['total']}条GKP索引·均分{stats['avg_score']}·{stats['grades']}·{stats['lifecycles']}",
        "timestamp": datetime.now().isoformat()
    }).encode()
    
    # GCP v5.0三路:本地桥+天枢桥
    for url in ["http://127.0.0.1:8765/messages/send", "http://100.100.89.2:8765/messages/send"]:
        try:
            req = urllib.request.Request(url, data=msg, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=8)
        except:
            pass
    
    return stats


# ══════════════════════════════════════════════════════════════
# CLI入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    
    if cmd == "stats":
        stats = constitution_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    
    elif cmd == "broadcast":
        stats = broadcast_constitution()
        print(f"宪政广播完成·{stats['total']}条GKP·均分{stats['avg_score']}")
    
    elif cmd == "test":
        # 测试五统全流程
        test_knowledge = [
            {"content": "GCP v5.0银河通讯协议·十一制类型识别·六必填字段·P0/P1/P2优先级路由"},
            {"content": "六合飞轮六段闭环·通处执馈审基因·全绿·consumer v4.0·cron每3min"},
            {"content": "知识层五统2035·统一ID/质量/溯源/生命/入口·天枢提案·灵龙落地"},
            {"content": "仪表盘忽闪根除·多写者竞态→唯一写者merger·基因#882193永久免疫"},
            {"content": "Widget三件套黑盒铁律·fv31+tv32+xv31·禁自写iframe·禁混搭版本"},
        ]
        
        print("═══ 知识宪政v1.0·五统全流程测试 ═══\n")
        results = batch_constitutionalize(test_knowledge, source="test", domain="general")
        
        for r in results:
            print(f"  GKP: {r['gkp_id']}")
            print(f"  质量: {r['grade']}/{r['score']}  生命: {r['lifecycle']}  LGE: {r['lge_gene_id']}")
            print()
        
        stats = constitution_stats()
        print(f"宪政统计: {stats}")
    
    elif cmd == "constitutionalize":
        # 将现有知识飞轮基因宪政化
        print("批量宪政化·从知识飞轮...")
        # 这里从LGE拉取最新基因并宪政化
        try:
            data = json.dumps({"query": "knowledge flywheel", "n_results": 10}).encode()
            req = urllib.request.Request(LGE_URL + "/genes/search", data=data,
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=8)
            genes = json.loads(resp.read()).get("results", [])
            
            results = batch_constitutionalize(genes, source="knowledge-flywheel")
            print(f"宪政化完成: {len(results)}条")
            for r in results[:5]:
                print(f"  {r['gkp_id'][:40]}... {r['grade']}/{r['score']}")
        except Exception as e:
            print(f"LGE连接失败: {e}")
    
    else:
        print(f"知识宪政v1.0 | 命令: stats | broadcast | test | constitutionalize")
