#!/usr/bin/env python3
"""
BOX-ZERO · PC模拟AI Box·全闭环测试引擎
═══════════════════════════════════════════════════════
阶段1:收信 2:执行 3:进化 4:压力 5:全闭环
"""
import http.client, json, time, hashlib, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from lump import lump_encode, NODE_BRIDGE, aldp_scan_all

# 全联邦节点(AI Box模拟·一个不能少)
ALL_NODES = {
    "天枢": {"role":"master","ip":"100.100.89.2"},
    "地枢": {"role":"knowledge","ip":"100.116.0.29"},
    "天工": {"role":"gpu","ip":"100.118.207.31"},
    "太一": {"role":"watchdog","ip":"100.114.52.14"},
    "天玑": {"role":"edge","ip":"100.122.142.74"},
    "天怿": {"role":"home","ip":"100.83.8.151"},
    "织网": {"role":"comm","ip":"100.127.112.128"},
}
BOX_NODES = list(ALL_NODES.keys())  # 全节点·一个不能少
RESULTS_FILE = "/Users/a112233/lgox-ops/web/box-zero-results.json"

class BoxZero:
    def __init__(self):
        self.phase = self._detect_phase()
        self.results = self._load()
        self.stats = {"sent":0,"replied":0,"executed":0,"errors":0}

    def _load(self):
        try:
            if os.path.exists(RESULTS_FILE):
                with open(RESULTS_FILE) as f: return json.load(f)
        except: pass
        return {"phase":1,"round":0,"nodes":{},"history":[]}

    def _save(self):
        os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
        self.results["_ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(RESULTS_FILE,"w") as f: json.dump(self.results,f,ensure_ascii=False,indent=2)

    def _detect_phase(self):
        r = self._load()
        p = r.get("phase",1)
        if r.get("round",0) >= 10: return min(p+1, 5)
        return p

    def _send(self, to_node, content, msg_type="task", priority="P1"):
        reply_br = NODE_BRIDGE.get(to_node, "127.0.0.1:8765")
        mid, msg = lump_encode(content, to_node, msg_type, priority, reply_bridge=reply_br)
        body = json.dumps({"from":"灵龙","to":to_node,"content":msg}).encode()
        
        delivered = 0
        for host, port in [("127.0.0.1",8765),("100.100.89.2",8765)]:
            try:
                conn = http.client.HTTPConnection(host, port, timeout=3)
                conn.request("POST","/messages/send", body, {"Content-Type":"application/json"})
                d = json.loads(conn.getresponse().read())
                if d.get("status")=="delivered": delivered += 1
                conn.close()
            except: pass
        
        self.stats["sent"] += 1
        return mid, delivered

    # ═══ 阶段1: 收信测试 ═══
    def phase1_receive(self):
        print(f"\n📡 BOX-ZERO·阶段1·收信测试·第{self.results['round']+1}轮")
        
        # 扫描全节点
        alive = aldp_scan_all()
        online = [n for n in BOX_NODES if alive.get(n,{}).get("status")=="online"]
        offline = [n for n in BOX_NODES if n not in online and n != "灵龙"]
        print(f"  在线: {len(online)} | 离线: {len(offline)}")
        if online: print(f"  🟢 {','.join(online)}")
        if offline: print(f"  🔴 {','.join(offline)} (store兜底)")
        
        # 全节点发送(在线直发·离线store)
        for node in BOX_NODES:
            if node == "灵龙": continue
            mid, paths = self._send(node, f"BOX-ZERO·P1·收信测试·第{self.results['round']+1}轮。请{node}({ALL_NODES.get(node,{}).get('role','?')})收到后回复:BOX-ZERO-ACK。", "task", "P1")
            tag = "📤" if node in online else "💾"
            print(f"  {tag} {node}: {paths}/2路 mid={mid[:8]}")
            self.results["nodes"].setdefault(node, {"received":0,"replied":0,"executed":0})
        
        self.results["round"] += 1
        self._save()

    # ═══ 阶段2: 执行测试 ═══
    def phase2_execute(self):
        print(f"\n⚡ BOX-ZERO·阶段2·执行测试·第{self.results['round']+1}轮")
        
        alive = aldp_scan_all()
        online = [n for n in BOX_NODES if alive.get(n,{}).get("status")=="online"]
        
        tasks = {
            "天工": {"cmd":"nvidia-smi 2>/dev/null || echo 'no GPU'","q":"报告GPU状态"},
            "太一": {"cmd":"systeminfo | findstr /B /C:\"OS\" 2>nul || uname -a","q":"报告系统信息"},
            "天玑": {"cmd":"df -h / | tail -1","q":"报告磁盘空间"},
        }
        
        for node in BOX_NODES:
            if node == "灵龙": continue
            is_online = node in online
            task = tasks.get(node, {"cmd":"uname -a","q":"报告系统信息"})
            mid, paths = self._send(node, f"BOX-ZERO·P2·执行: {task['q']}", "task", "P1")
            tag = "⚡" if is_online else "💾"
            print(f"  {tag} {node}({ALL_NODES[node]['role']}): {task['q'][:30]}... mid={mid[:8]}")
            self.results["nodes"].setdefault(node, {}).setdefault("executed",0)
        
        self.results["round"] += 1
        self._save()

    # ═══ 阶段3: 进化测试 ═══
    def phase3_evolve(self):
        print(f"\n🧬 BOX-ZERO·阶段3·进化测试·第{self.results['round']+1}轮")
        alive = aldp_scan_all()
        online = [n for n in BOX_NODES if alive.get(n,{}).get("status")=="online"]
        
        for node in BOX_NODES:
            if node == "灵龙": continue
            is_online = node in online
            mid, paths = self._send(node, f"BOX-ZERO·P3·进化:请汇报上次任务结果并纳基因。", "task", "P1")
            tag = "🧬" if is_online else "💾"
            print(f"  {tag} {node}({ALL_NODES[node]['role']}): 进化请求 mid={mid[:8]}")
        
        self.results["round"] += 1
        self._save()

    # ═══ 主循环 ═══
    def run(self):
        phase = self._detect_phase()
        self.results["phase"] = phase
        
        phase_funcs = {1: self.phase1_receive, 2: self.phase2_execute, 
                       3: self.phase3_evolve, 4: self.phase1_receive, 5: self.phase1_receive}
        
        func = phase_funcs.get(phase, self.phase1_receive)
        func()
        
        # 统计
        nodes = self.results.get("nodes",{})
        total = sum(n.get("received",0)+n.get("replied",0)+n.get("executed",0) for n in nodes.values())
        self.results["stats"] = {"total_actions": total, "phase": phase, "round": self.results["round"]}
        self._save()
        
        print(f"  📊 P{phase}·R{self.results['round']}·sent={self.stats['sent']}")

if __name__ == "__main__":
    BoxZero().run()
