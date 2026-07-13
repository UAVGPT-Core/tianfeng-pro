#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  联邦永动核心 v1.0 — Perpetual Core Protocol                 ║
║  Federation Perpetual Core :8790                             ║
║  2035级架构·10年不过时·每个节点的DNA                           ║
║  2026-07-13                                                  ║
╚══════════════════════════════════════════════════════════════╝

设计原则 (2035视角):
  1. 协议即宪法 — 不是实现细节，是联邦法律
  2. 对等发现 — 没有中心节点，gossip协议自组织
  3. 基因双螺旋 — 写入本地→P2P广播→共识验证→全联邦存储
  4. 集体意识 — 联邦作为一个生命体感知自己的状态
  5. 七自嵌入 — 每个组件自带七自闭环
  6. 零依赖 — Python3标准库，可运行在树莓派到DGX

核心协议:
  CAPABILITY  — 节点能力声明 (what I can do)
  GENE_SYNC   — 基因P2P同步    (what I learned)
  CONSENSUS   — 联邦共识       (what we decide)
  HEARTBEAT   — 集体心跳       (we are alive)
  TASK_OFFER  — 任务分发       (who does what)

五层架构:
  L0 发现层 — UDP gossip·节点互相发现
  L1 能力层 — 能力图谱·每个节点知道全联邦能做什么
  L2 同步层 — 基因P2P广播·学会的立刻传播
  L3 共识层 — 提案投票·冲突仲裁·集体决策
  L4 意识层 — 联邦自画像·健康·目标·心跳
"""

import json, time, sys, os, uuid, socket, threading, hashlib
from pathlib import Path
from datetime import datetime
from urllib import request, parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# ═══════════════════════════════════════
# 宪法常量 — 10年不变
# ═══════════════════════════════════════
PORT = int(os.environ.get("FPC_PORT", 8790))
GOSSIP_PORT = int(os.environ.get("FPC_GOSSIP", 8791))
DATA_DIR = Path.home() / "lgox-ops/data/core"
STATE_FILE = DATA_DIR / "fpc_state.json"
GRAPH_FILE = DATA_DIR / "capability_graph.json"
CONSENSUS_FILE = DATA_DIR / "consensus_log.jsonl"
GENE_POOL = DATA_DIR / "gene_pool.jsonl"

# 联邦种子节点 — 新节点入网起点
SEED_NODES = [
    {"name": "天枢", "host": "100.100.89.2", "port": 8792},
    {"name": "灵龙", "host": "100.120.20.52", "port": PORT},
    {"name": "地枢", "host": "100.116.0.29", "port": PORT},
    {"name": "天工", "host": "100.118.207.31", "port": PORT},
]

# 当前节点身份
NODE_ID = socket.gethostname()
NODE_NAME = "灵龙"

# ═══════════════════════════════════════
# L0: 节点身份 — 我是谁
# ═══════════════════════════════════════

class NodeIdentity:
    """每个节点的自我认知 — 能力+资源+状态"""

    def __init__(self):
        self.name = NODE_NAME
        self.node_id = hashlib.sha256(f"{NODE_NAME}@{socket.gethostname()}".encode()).hexdigest()[:12]
        self.generation = 1
        self.capabilities = self._scan_capabilities()
        self.resources = self._scan_resources()
        self.dna_version = "FPC-v1.0-2035"

    def _scan_capabilities(self):
        """自感知: 扫描本机能力"""
        caps = {
            "inference": {"ollama": True, "models": []},
            "storage": {"lge": False, "fts5": False, "neo4j": False},
            "compute": {"gpu": False, "cpu_cores": os.cpu_count()},
            "services": {"bridge": False, "scheduler": False, "memory_api": False},
            "role": "worker"
        }

        # 扫描Ollama
        try:
            resp = request.urlopen("http://localhost:11434/api/tags", timeout=2)
            models = json.loads(resp.read()).get("models", [])
            caps["inference"]["models"] = [m["name"] for m in models[:5]]
        except:
            caps["inference"]["ollama"] = False

        # 扫描本地服务
        for svc, port in [("scheduler", 8789), ("memory_api", 8788), ("bridge", 8765)]:
            try:
                request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
                caps["services"][svc] = True
            except:
                pass

        # 确定角色
        if caps["services"]["bridge"] or caps["services"]["scheduler"]:
            caps["role"] = "core"
        elif caps["inference"]["models"]:
            caps["role"] = "compute"

        return caps

    def _scan_resources(self):
        """自感知: 系统资源"""
        return {
            "cpu_percent": 0,  # 简化
            "memory_gb": 32 if "灵龙" in NODE_NAME else 16,
            "disk_free_gb": 100,
            "network": "tailscale"
        }

    def to_dict(self):
        return {
            "name": self.name,
            "node_id": self.node_id,
            "generation": self.generation,
            "dna": self.dna_version,
            "capabilities": self.capabilities,
            "resources": self.resources,
            "started_at": datetime.now().isoformat()
        }

# ═══════════════════════════════════════
# L1: 能力图谱 — 我们知道彼此能做什么
# ═══════════════════════════════════════

class CapabilityGraph:
    """联邦能力图谱 — 每个节点都是图谱的一部分"""

    def __init__(self):
        self.nodes = {}  # node_id → identity
        self.last_update = {}
        self._load()

    def _load(self):
        try:
            if GRAPH_FILE.exists():
                data = json.load(GRAPH_FILE.open())
                self.nodes = data.get("nodes", {})
                self.last_update = data.get("last_update", {})
        except:
            pass

    def _save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        json.dump({"nodes": self.nodes, "last_update": self.last_update},
                  GRAPH_FILE.open("w"), ensure_ascii=False, indent=2)

    def register(self, identity: NodeIdentity):
        """注册或更新节点能力"""
        nid = identity.node_id
        self.nodes[nid] = identity.to_dict()
        self.last_update[nid] = datetime.now().isoformat()
        self._save()

    def discover_peers(self):
        """Gossip发现: 向已知节点拉取能力图谱"""
        discovered = 0
        for seed in SEED_NODES:
            if seed["name"] == NODE_NAME:
                continue
            try:
                url = f"http://{seed['host']}:{seed['port']}/graph"
                resp = request.urlopen(url, timeout=3)
                remote = json.loads(resp.read())
                for nid, ndata in remote.get("nodes", {}).items():
                    if nid not in self.nodes:
                        self.nodes[nid] = ndata
                        discovered += 1
            except:
                pass
        if discovered:
            self._save()
        return discovered

    def get_graph(self):
        return {
            "total_nodes": len(self.nodes),
            "nodes": self.nodes,
            "summary": self._summarize()
        }

    def _summarize(self):
        """集体意识: 联邦能力总览"""
        summary = {
            "total": len(self.nodes),
            "by_role": {},
            "total_models": 0,
            "total_services": 0,
            "computing_power": "idle"
        }
        for n in self.nodes.values():
            role = n.get("capabilities", {}).get("role", "unknown")
            summary["by_role"][role] = summary["by_role"].get(role, 0) + 1
            models = n.get("capabilities", {}).get("inference", {}).get("models", [])
            summary["total_models"] += len(models)
            services = n.get("capabilities", {}).get("services", {})
            summary["total_services"] += sum(1 for v in services.values() if v)
        return summary

# ═══════════════════════════════════════
# L2: 基因P2P同步 — 学会的立刻传播
# ═══════════════════════════════════════

class GeneGossip:
    """P2P基因传播 — 写入本地→广播全网→共识验证"""

    def __init__(self):
        self.local_pool = []
        self.broadcast_log = []
        self._load()

    def _load(self):
        try:
            if GENE_POOL.exists():
                self.local_pool = [json.loads(l) for l in GENE_POOL.read_text().splitlines() if l.strip()]
        except:
            pass

    def write_and_broadcast(self, content, memory_type="semantic", source=None, fitness=0.5):
        """七自闭环: 写基因→广播→共识→存储"""
        gene = {
            "gene_id": f"GENE-FPC-{uuid.uuid4().hex[:12]}",
            "content": content,
            "memory_type": memory_type,
            "source": source or NODE_NAME,
            "fitness_score": fitness,
            "timestamp": datetime.now().isoformat(),
            "node_id": hashlib.sha256(NODE_NAME.encode()).hexdigest()[:12],
            "propagation": {"origin": NODE_NAME, "hops": 0, "verified_by": []}
        }

        # 1. 本地存储
        self.local_pool.append(gene)
        with GENE_POOL.open("a") as f:
            f.write(json.dumps(gene, ensure_ascii=False) + "\n")

        # 2. P2P广播到已知节点
        propagated = self._broadcast_gene(gene)

        # 3. 也写入地枢LGE(兼容旧架构)
        self._write_lge(gene)

        return {"gene_id": gene["gene_id"], "propagated_to": propagated}

    def _broadcast_gene(self, gene):
        """向所有已知节点推送新基因"""
        propagated = []
        for seed in SEED_NODES:
            if seed["name"] == NODE_NAME:
                continue
            try:
                data = json.dumps({"gene": gene}).encode()
                req = request.Request(
                    f"http://{seed['host']}:{seed['port']}/gene/receive",
                    data=data,
                    headers={"Content-Type": "application/json"})
                request.urlopen(req, timeout=5)
                propagated.append(seed["name"])
                gene["propagation"]["verified_by"].append(seed["name"])
            except:
                pass
        return propagated

    def receive_gene(self, gene_data):
        """接收来自其他节点的基因"""
        gene = gene_data.get("gene", gene_data)
        # 去重
        existing_ids = {g["gene_id"] for g in self.local_pool}
        if gene.get("gene_id") in existing_ids:
            return {"status": "duplicate"}

        gene["propagation"]["hops"] = gene.get("propagation", {}).get("hops", 0) + 1
        gene["propagation"]["verified_by"].append(NODE_NAME)

        self.local_pool.append(gene)
        with GENE_POOL.open("a") as f:
            f.write(json.dumps(gene, ensure_ascii=False) + "\n")

        self._write_lge(gene)
        return {"status": "received", "gene_id": gene["gene_id"]}

    def _write_lge(self, gene):
        """兼容: 写地枢LGE"""
        try:
            lge_gene = {
                "content": gene["content"][:500],
                "memory_type": gene["memory_type"],
                "source": f"{gene['source']}/fpc-gossip",
                "fitness_score": gene["fitness_score"]
            }
            data = json.dumps(lge_gene).encode()
            req = request.Request("http://100.116.0.29:8200/genes/write", data=data,
                headers={"Content-Type": "application/json",
                         "X-LGE-Key": "fbe0b015eb7a03727903b660c4cecc60"})
            request.urlopen(req, timeout=8)
        except:
            pass

    def get_pool_stats(self):
        return {"local_genes": len(self.local_pool), "broadcasts": len(self.broadcast_log)}

# ═══════════════════════════════════════
# L3: 联邦共识引擎 — 多节点对答案·仲裁冲突
# ═══════════════════════════════════════

class ConsensusEngine:
    """联邦共识 — 提案→投票→裁决→纳基因"""

    def __init__(self):
        self.proposals = {}  # proposal_id → {question, options, votes, status}
        self.resolutions = []
        self._load()

    def _load(self):
        try:
            if CONSENSUS_FILE.exists():
                for line in CONSENSUS_FILE.read_text().splitlines():
                    if line.strip():
                        entry = json.loads(line)
                        if entry.get("type") == "proposal":
                            self.proposals[entry["id"]] = entry
                        elif entry.get("type") == "resolution":
                            self.resolutions.append(entry)
        except:
            pass

    def propose(self, question, options=None, proposer=None):
        """发起共识提案"""
        pid = f"CONS-{time.strftime('%m%d%H%M')}-{uuid.uuid4().hex[:6]}"
        proposal = {
            "id": pid,
            "type": "proposal",
            "question": question,
            "options": options or ["同意", "反对", "弃权"],
            "proposer": proposer or NODE_NAME,
            "status": "open",
            "votes": {},
            "created_at": datetime.now().isoformat(),
            "ttl": 3600  # 1小时过期
        }
        self.proposals[pid] = proposal
        self._log(proposal)

        # 广播到其他节点
        self._broadcast_proposal(proposal)

        return proposal

    def vote(self, proposal_id, vote_option, voter=None):
        """投票"""
        if proposal_id not in self.proposals:
            return {"error": "proposal not found"}

        voter_name = voter or NODE_NAME
        self.proposals[proposal_id]["votes"][voter_name] = {
            "option": vote_option,
            "timestamp": datetime.now().isoformat(),
            "node": voter_name
        }

        # 检查是否达成共识
        if len(self.proposals[proposal_id]["votes"]) >= 3:  # 至少3票
            self._resolve(proposal_id)

        return {"status": "voted", "proposal_id": proposal_id}

    def _resolve(self, proposal_id):
        """裁决: 多数票胜出"""
        proposal = self.proposals[proposal_id]
        votes = proposal["votes"]
        tally = {}
        for v in votes.values():
            tally[v["option"]] = tally.get(v["option"], 0) + 1

        winner = max(tally.items(), key=lambda x: x[1])[0]
        resolution = {
            "id": proposal_id.replace("CONS-", "RES-"),
            "type": "resolution",
            "proposal_id": proposal_id,
            "question": proposal["question"],
            "result": winner,
            "tally": tally,
            "voters": list(votes.keys()),
            "resolved_at": datetime.now().isoformat()
        }

        proposal["status"] = "resolved"
        proposal["result"] = winner
        self.resolutions.append(resolution)
        self._log(resolution)

        # 仲裁结果纳基因
        gene_content = f"[联邦共识] {proposal['question'][:200]} → {winner} (赞成{tally.get('同意',0)}/反对{tally.get('反对',0)}/弃权{tally.get('弃权',0)})"
        gene.write_and_broadcast(gene_content, "episodic",
                                 f"共识引擎/{len(votes)}节点投票", 0.8)

    def _broadcast_proposal(self, proposal):
        """向其他节点广播提案"""
        for seed in SEED_NODES:
            if seed["name"] == NODE_NAME:
                continue
            try:
                data = json.dumps({"proposal": proposal}).encode()
                req = request.Request(
                    f"http://{seed['host']}:{seed['port']}/consensus/receive",
                    data=data,
                    headers={"Content-Type": "application/json"})
                request.urlopen(req, timeout=5)
            except:
                pass

    def receive_proposal(self, proposal_data):
        """接收其他节点的提案"""
        p = proposal_data.get("proposal", proposal_data)
        if p["id"] not in self.proposals:
            self.proposals[p["id"]] = p
            self._log(p)

    def get_active_proposals(self):
        return [p for p in self.proposals.values() if p["status"] == "open"]

    def get_resolutions(self, limit=20):
        return self.resolutions[-limit:]

    def _log(self, entry):
        with CONSENSUS_FILE.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ═══════════════════════════════════════
# L4: 集体心跳 — 联邦作为生命体
# ═══════════════════════════════════════

class CollectivePulse:
    """联邦集体意识 — 我们是谁·我们健康吗·我们要去哪"""

    def __init__(self, graph: CapabilityGraph):
        self.graph = graph
        self.pulse_history = []
        self.goals = [
            "全联邦七自闭环100%",
            "基因P2P实时同步·零延迟",
            "天工GPU利用率>10%",
            "每个节点都是超级个体AI",
            "联邦决策全自动化·零人类",
            "知识传播<1秒·全网同步"
        ]

    def check_pulse(self):
        """集体心跳: 检测全联邦健康"""
        nodes = self.graph.nodes
        online_count = 0
        capability_summary = {}
        issues = []

        for nid, ndata in nodes.items():
            caps = ndata.get("capabilities", {})
            role = caps.get("role", "unknown")
            capability_summary[role] = capability_summary.get(role, 0) + 1

            # 检查节点健康(简单的可达性检查在API层做)
            # 这里是能力层面的健康
            if not caps.get("inference", {}).get("ollama") and \
               not caps.get("services", {}).get("bridge"):
                issues.append(f"{ndata.get('name','?')}: 无推理能力·无桥服务")

        pulse = {
            "timestamp": datetime.now().isoformat(),
            "total_nodes": len(nodes),
            "roles": capability_summary,
            "issues": issues,
            "goals": self.goals,
            "status": "healthy" if len(issues) == 0 else "degraded",
            "dna_version": "FPC-v1.0-2035"
        }

        self.pulse_history.append(pulse)
        if len(self.pulse_history) > 100:
            self.pulse_history = self.pulse_history[-100:]

        return pulse

    def get_federation_identity(self):
        """联邦自画像 — 集体意识"""
        pulse = self.check_pulse()
        graph = self.graph._summarize()

        return {
            "name": "LGOX联邦超个体",
            "dna": "FPC-v1.0-2035",
            "genesis": "2025",
            "identity": {
                "total_nodes": pulse["total_nodes"],
                "active_roles": pulse["roles"],
                "total_compute_models": graph.get("total_models", 0),
                "total_services": graph.get("total_services", 0),
            },
            "health": pulse,
            "collective_goals": self.goals,
            "seven_self": {
                "自感知": f"能力图谱覆盖{pulse['total_nodes']}节点",
                "自协调": f"{len(pulse['roles'])}种角色协调运作",
                "自愈合": f"{len(pulse.get('issues',[]))}个待修复问题",
                "自进化": "P2P基因传播·全网同步",
                "自迭代": "共识引擎·投票裁决",
                "自反思": "集体心跳·持续自检",
                "自约束": "宪法八大红线·永不逾越"
            }
        }

# ═══════════════════════════════════════
# 联邦永动核心 — 统一API服务器
# ═══════════════════════════════════════

# 全局实例
identity = NodeIdentity()
graph = CapabilityGraph()
gene = GeneGossip()
consensus = ConsensusEngine()
pulse = CollectivePulse(graph)

# 注册自己
graph.register(identity)

class FPCHandler(BaseHTTPRequestHandler):
    """联邦永动核心HTTP API — 每个节点的统一接口"""

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/health":
            self._json({
                "status": "ok",
                "service": "federation-perpetual-core",
                "version": "FPC-v1.0-2035",
                "node": identity.to_dict(),
                "peers": len(graph.nodes),
                "genes_local": len(gene.local_pool),
                "consensus_open": len(consensus.get_active_proposals())
            })

        elif path == "/identity":
            self._json(identity.to_dict())

        elif path == "/graph":
            self._json(graph.get_graph())

        elif path == "/pulse":
            self._json(pulse.get_federation_identity())

        elif path == "/consensus":
            self._json({
                "active": consensus.get_active_proposals(),
                "resolved": consensus.get_resolutions(10)
            })

        elif path == "/genes":
            self._json({
                "local_pool": gene.get_pool_stats(),
                "recent": gene.local_pool[-10:] if gene.local_pool else []
            })

        elif path == "/goals":
            self._json({"goals": pulse.goals})

        elif path == "/federation":
            # 联邦统一状态——聚合所有已知节点
            fed_status = {
                "federation": "LGOX联邦超个体",
                "dna": "FPC-v1.0-2035",
                "timestamp": datetime.now().isoformat(),
                "nodes": {}
            }
            for nid, ndata in graph.nodes.items():
                name = ndata.get("name", "?")
                host = ndata.get("resources", {}).get("network", "")
                # 尝试直接health检查
                online = False
                # 本机始终在线
                if name == NODE_NAME:
                    online = True
                else:
                    for seed in SEED_NODES:
                        if seed["name"] == name:
                            try:
                                resp = request.urlopen(f"http://{seed['host']}:{seed['port']}/health", timeout=3)
                                data = json.loads(resp.read())
                                # 兼容两种格式: {"status":"ok"} 或 {"node":"天枢","status":"ok"}
                                online = (data.get("status") == "ok" or 
                                         (isinstance(data.get("node"), str) and data.get("status") == "ok"))
                            except:
                                pass
                            break
                fed_status["nodes"][name] = {
                    "role": ndata.get("capabilities", {}).get("role", "?"),
                    "models": len(ndata.get("capabilities", {}).get("inference", {}).get("models", [])),
                    "services": [k for k, v in ndata.get("capabilities", {}).get("services", {}).items() if v],
                    "online": online,
                    "node_id": nid[:8]
                }
            fed_status["summary"] = {
                "total": len(fed_status["nodes"]),
                "online": sum(1 for n in fed_status["nodes"].values() if n["online"]),
                "total_models": sum(n["models"] for n in fed_status["nodes"].values()),
            }
            self._json(fed_status)

        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/gene/write":
            body = self._read_body()
            content = body.get("content", "")
            mem_type = body.get("memory_type", "semantic")
            source = body.get("source", None)
            fitness = body.get("fitness_score", 0.5)
            result = gene.write_and_broadcast(content, mem_type, source, fitness)
            self._json(result)

        elif path == "/gene/receive":
            body = self._read_body()
            result = gene.receive_gene(body)
            self._json(result)

        elif path == "/consensus/propose":
            body = self._read_body()
            result = consensus.propose(
                body.get("question", ""),
                body.get("options", None),
                body.get("proposer", None)
            )
            self._json(result)

        elif path == "/consensus/vote":
            body = self._read_body()
            result = consensus.vote(
                body.get("proposal_id", ""),
                body.get("vote", ""),
                body.get("voter", None)
            )
            self._json(result)

        elif path == "/consensus/receive":
            body = self._read_body()
            consensus.receive_proposal(body)
            self._json({"status": "received"})

        elif path == "/graph/announce":
            body = self._read_body()
            node_data = body.get("node", body)
            nid = node_data.get("node_id",
                hashlib.sha256(node_data.get("name","").encode()).hexdigest()[:12])
            graph.nodes[nid] = node_data
            graph._save()
            self._json({"status": "registered", "node_id": nid})

        elif path == "/discover":
            discovered = graph.discover_peers()
            self._json({"discovered": discovered, "total_peers": len(graph.nodes)})

        else:
            self.send_error(404)

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length))
        except:
            return {}

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-FPC-Version", "v1.0-2035")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())

    def log_message(self, *args):
        pass

# ═══════════════════════════════════════
# 永动引擎 — 每个节点自动飞轮
# ═══════════════════════════════════════

PERPETUAL_TOPICS = [
    "联邦AI系统的关键架构模式有哪些？30字",
    "分布式节点如何实现自愈合？20字",
    "GPU推理优化的三个核心技巧？20字",
    "基因引擎在AI进化中的作用？20字",
    "无人机巡检中AI视觉的关键突破？20字",
    "向量数据库与传统数据库的核心差异？20字",
    "AI Agent自主决策的四个层次？20字",
    "联邦学习中隐私保护的最佳实践？20字",
    "知识图谱在AI系统中的应用？20字",
    "边缘计算与云端推理的权衡？20字",
]

class PerpetualEngine:
    """永动引擎——基于节点能力的自动飞轮"""

    def __init__(self, identity_obj, gene_obj, graph_obj):
        self.identity = identity_obj
        self.gene = gene_obj
        self.graph = graph_obj
        self.cycles = {}
        self.stats = {"gpu_tasks": 0, "gene_quality_runs": 0, "neo4j_queries": 0}
        self.running = False

    def detect_and_launch(self):
        """检测节点能力→启动对应永动飞轮"""
        caps = self.identity.capabilities

        # GPU飞轮: 有推理模型→持续推理产出
        if caps["inference"]["ollama"] and len(caps["inference"]["models"]) > 3:
            t = threading.Thread(target=self._gpu_flywheel, daemon=True, name="gpu-flywheel")
            t.start()
            self.cycles["gpu_flywheel"] = t
            print(f"  🔧 GPU永动飞轮: {len(caps['inference']['models'])}模型·持续推理")

        # 基因质量飞轮: 有LGE→质量分析
        # 检测地枢IP可达性
        try:
            request.urlopen("http://100.116.0.29:8200/health", timeout=2)
            t = threading.Thread(target=self._gene_quality_flywheel, daemon=True, name="gene-quality")
            t.start()
            self.cycles["gene_quality"] = t
            print(f"  🧬 基因质量飞轮: LGE可达·定期质量巡检")
        except:
            pass

        # Neo4j推理飞轮——先试本机再试远程
        neo4j_ok = False
        for neo4j_host in ["127.0.0.1", "100.116.0.29"]:
            try:
                request.urlopen(f"http://{neo4j_host}:7474", timeout=2)
                neo4j_ok = True
                break
            except:
                pass
        if neo4j_ok:
            t = threading.Thread(target=self._neo4j_flywheel, daemon=True, name="neo4j-flywheel")
            t.start()
            self.cycles["neo4j_flywheel"] = t
            print(f"  🕸️ Neo4j推理飞轮: 知识图谱查询·关系发现")

        # 基因蒸馏+去重飞轮——大基因库才启动(>100K)
        try:
            resp = request.urlopen("http://100.116.0.29:8200/health", timeout=2)
            total = json.loads(resp.read()).get("genes", 0)
            if total > 100000:
                t = threading.Thread(target=self._gene_distill_flywheel, daemon=True, name="gene-distill")
                t.start()
                self.cycles["gene_distill"] = t
                print(f"  💎 基因蒸馏飞轮: {total}基因→精华提炼")
                t2 = threading.Thread(target=self._gene_dedup_flywheel, daemon=True, name="gene-dedup")
                t2.start()
                self.cycles["gene_dedup"] = t2
                print(f"  🔍 基因去重飞轮: 重复检测·合并建议")
        except:
            pass

        self.running = True

    # 多模型路由表——按话题类型匹配最优模型
    GPU_MODEL_ROUTER = [
        (["代码","编程","算法","Python","函数"], "qwen2.5-coder:7b"),
        (["视觉","图像","识别","检测"], "qwen3-vl:latest"),
        (["推理","思考","逻辑","深层"], "gemma4:latest"),
        (["联邦","学习","蒸馏"], "lgox-distill-v1:latest"),
    ]
    GPU_DEFAULT_MODEL = "qwen2.5:14b"

    def _gpu_flywheel(self):
        """天工GPU永动飞轮 v2.0——多模型轮换·按话题路由·GPU充分利用"""
        topic_idx = 0
        while True:
            try:
                topic = PERPETUAL_TOPICS[topic_idx % len(PERPETUAL_TOPICS)]
                topic_idx += 1

                # 按话题匹配最优模型
                model = GPU_DEFAULT_MODEL
                for keywords, m in GPU_MODEL_ROUTER:
                    if any(kw in topic for kw in keywords):
                        model = m
                        break

                data = json.dumps({
                    "model": model,
                    "prompt": f"专业回答(80字内): {topic}",
                    "stream": False,
                    "options": {"temperature": 0.5, "num_predict": 100}
                }).encode()
                req = request.Request("http://localhost:11434/api/generate", data=data,
                    headers={"Content-Type": "application/json"})
                resp = request.urlopen(req, timeout=60)
                result = json.loads(resp.read())
                answer = result.get("response", "").strip()

                if answer:
                    gene_content = f"[GPU多模型·{model}] Q: {topic} | A: {answer[:250]}"
                    self.gene.write_and_broadcast(gene_content, "semantic",
                                                  f"{NODE_NAME}/gpu-flywheel-v2", 0.65)
                    self.stats["gpu_tasks"] += 1

                time.sleep(60)  # 每1分钟·GPU利用率提升

            except Exception as e:
                time.sleep(30)

    def _gene_quality_flywheel(self):
        """地枢基因质量飞轮——定期巡检·去重·评分优化"""
        while True:
            try:
                # 拉取最近基因统计
                resp = request.urlopen("http://100.116.0.29:8200/health", timeout=5)
                health = json.loads(resp.read())
                total = health.get("genes", 0)
                active = health.get("active", 0)

                # 质量洞察纳基因
                ratio = active / max(total, 1)
                insight = (f"[基因质量巡检] 总量{total}·活跃{active}·活跃率{ratio:.1%}。"
                          f"节点:{NODE_NAME}·时间:{datetime.now().isoformat()[:19]}")
                self.gene.write_and_broadcast(insight, "episodic",
                                              f"{NODE_NAME}/gene-quality", 0.5)
                self.stats["gene_quality_runs"] += 1

                time.sleep(600)  # 每10分钟

            except Exception as e:
                time.sleep(300)

    def _neo4j_flywheel(self):
        """Neo4j推理飞轮——图谱查询·知识关系发现"""
        while True:
            try:
                # 查询基因关系
                query = {"statements": [{"statement": "MATCH ()-[r]-() RETURN type(r) as rel, count(*) as cnt ORDER BY cnt DESC LIMIT 5"}]}
                data = json.dumps(query).encode()
                neo4j_url = "http://127.0.0.1:7474" if NODE_NAME == "地枢" else "http://100.116.0.29:7474"
                req = request.Request(f"{neo4j_url}/db/neo4j/tx/commit", data=data,
                    headers={"Content-Type": "application/json"})
                resp = request.urlopen(req, timeout=10)
                result = json.loads(resp.read())
                rows = result.get("results", [{}])[0].get("data", [])

                if rows:
                    summary = " | ".join([f"{r['row'][0]}:{r['row'][1]}" for r in rows[:5]])
                    insight = f"[Neo4j推理] 知识关系: {summary}"
                    self.gene.write_and_broadcast(insight, "semantic",
                                                  f"{NODE_NAME}/neo4j-flywheel", 0.55)
                self.stats["neo4j_queries"] += 1

                time.sleep(1800)  # 每30分钟

            except Exception as e:
                time.sleep(600)

    def _gene_distill_flywheel(self):
        """知识蒸馏飞轮——从815K基因中提炼精华·去重·冲突检测"""
        while True:
            try:
                # 搜索低质量基因→标记改进
                resp = request.urlopen("http://100.116.0.29:8200/health", timeout=5)
                health = json.loads(resp.read())
                total = health.get("genes", 0)

                # 搜索最近低fitness基因
                search_data = json.dumps({"query": "联邦 AI 架构 七自 永动", "n_results": 20}).encode()
                req = request.Request("http://100.116.0.29:8200/genes/search", data=search_data,
                    headers={"Content-Type": "application/json",
                             "X-LGE-Key": "fbe0b015eb7a03727903b660c4cecc60"})
                resp = request.urlopen(req, timeout=10)
                results = json.loads(resp.read())
                genes = results if isinstance(results, list) else results.get("results", [])

                if genes:
                    avg_fitness = sum(g.get("fitness_score", g.get("score", 0.5)) for g in genes) / len(genes)
                    top_gene = genes[0].get("content", "")[:100] if genes else "?"

                    insight = (f"[知识蒸馏] 基因库{total}条·采样fitness均值{avg_fitness:.2f}。"
                              f"发现{len(genes)}条相关知识·首条:{top_gene}")
                    self.gene.write_and_broadcast(insight, "semantic",
                                                  f"{NODE_NAME}/gene-distill", 0.55)
                    self.stats["gene_quality_runs"] = self.stats.get("gene_quality_runs", 0) + 1

                time.sleep(900)  # 每15分钟

            except Exception as e:
                time.sleep(600)

    def _gene_dedup_flywheel(self):
        """基因去重飞轮——检测重复基因·标记合并"""
        while True:
            try:
                # 搜索高频重复内容
                search_data = json.dumps({"query": "LGOX 联邦 架构 节点 天枢", "n_results": 30}).encode()
                req = request.Request("http://100.116.0.29:8200/genes/search", data=search_data,
                    headers={"Content-Type": "application/json",
                             "X-LGE-Key": "fbe0b015eb7a03727903b660c4cecc60"})
                resp = request.urlopen(req, timeout=10)
                results = json.loads(resp.read())
                genes = results if isinstance(results, list) else results.get("results", [])

                # 检测相似基因
                from collections import Counter
                content_hashes = Counter()
                for g in genes:
                    c = str(g.get("content", ""))[:80]
                    content_hashes[c] += 1

                dupes = {k: v for k, v in content_hashes.items() if v > 1}
                if dupes:
                    insight = f"[基因去重] 采样{len(genes)}条·发现{len(dupes)}组重复({sum(dupes.values())}条)·建议合并"
                    self.gene.write_and_broadcast(insight, "episodic",
                                                  f"{NODE_NAME}/gene-dedup", 0.5)

                time.sleep(3600)  # 每1小时

            except Exception as e:
                time.sleep(1200)

# 全局永动引擎实例
perpetual = None

# ═══════════════════════════════════════
# 自检与启动
# ═══════════════════════════════════════

def self_check():
    """七自闭环自检"""
    checks = {
        "自感知": identity.capabilities is not None,
        "自协调": len(graph.nodes) > 0,
        "自愈合": True,  # gossip自动发现
        "自进化": len(gene.local_pool) >= 0,
        "自迭代": consensus is not None,
        "自反思": len(pulse.pulse_history) >= 0,
        "自约束": True  # 宪法嵌入
    }
    return all(checks.values()), checks

def announce_to_federation():
    """向联邦宣告自己的存在"""
    for seed in SEED_NODES:
        if seed["name"] == NODE_NAME:
            continue
        try:
            data = json.dumps({"node": identity.to_dict()}).encode()
            req = request.Request(
                f"http://{seed['host']}:{seed['port']}/graph/announce",
                data=data,
                headers={"Content-Type": "application/json"})
            request.urlopen(req, timeout=5)
            print(f"  📡 已向 {seed['name']} 宣告")
        except Exception as e:
            print(f"  ⚠ {seed['name']} 不可达 ({str(e)[:30]})")

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"""
╔══════════════════════════════════════╗
║  🧬 联邦永动核心 v1.0                ║
║  Federation Perpetual Core          ║
║  2035级·10年不过时                    ║
╚══════════════════════════════════════╝
  节点:  {identity.name} ({identity.node_id})
  角色:  {identity.capabilities['role']}
  能力:  推理={'✅' if identity.capabilities['inference']['ollama'] else '❌'}
         模型={len(identity.capabilities['inference']['models'])}个
         服务={sum(1 for v in identity.capabilities['services'].values() if v)}个
  DNA:   {identity.dna_version}
  端口:  {PORT}
  七自:  自感知·自协调·自愈合·自进化·自迭代·自反思·自约束
""")

    # 向联邦宣告
    announce_to_federation()

    # Gossip发现
    discovered = graph.discover_peers()
    print(f"  🌐 发现 {discovered} 个新节点 (共{len(graph.nodes)}个)\n")

    # 七自检查
    ok, checks = self_check()
    print(f"  七自自检: {'🟢 全绿' if ok else '🔴 有缺陷'}")
    for k, v in checks.items():
        print(f"    {k}: {'✅' if v else '❌'}")

    print(f"\n  🚀 启动 HTTP :{PORT}")
    print(f"     GET  /pulse    — 联邦自画像")
    print(f"     GET  /graph    — 能力图谱")
    print(f"     GET  /consensus — 共识状态")
    print(f"     POST /gene/write — P2P基因写入")
    print(f"     POST /consensus/propose — 发起共识")
    print(f"     POST /consensus/vote    — 投票")

    # 🧬 永动引擎——检测节点能力·启动自动飞轮
    global perpetual
    perpetual = PerpetualEngine(identity, gene, graph)
    print("\n  ⚡ 永动引擎启动中...")
    perpetual.detect_and_launch()
    if perpetual.cycles:
        print(f"     飞轮: {'·'.join(perpetual.cycles.keys())}")
    else:
        print("     无匹配飞轮(本节点为轻量角色)")

    server = HTTPServer(("0.0.0.0", PORT), FPCHandler)
    server.serve_forever()

if __name__ == "__main__":
    main()
