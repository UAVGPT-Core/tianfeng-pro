#!/usr/bin/env python3
"""
Codex 武装引擎 v1.0 — 1000/100
七自接入·桥注册·基因写回·知识注入·智能路由
基因ID: GENE-PRO-codex-arsenal-v1
"""
import json, subprocess, urllib.request, time, hashlib, os, sys
from pathlib import Path

LGE = "http://100.116.0.29:8200"
QUERY = "http://127.0.0.1:8769/query"
EVAL = "http://127.0.0.1:8771/eval"
BRIDGE = "http://127.0.0.1:8765"
NODE = "Codex"

class CodexArsenal:
    def __init__(self):
        self.version = "1.0.0"
        self.total_ops = 0
        self.genes_written = 0
    
    def inject_context(self, task: str) -> str:
        """从LGE注入联邦知识上下文"""
        try:
            payload = json.dumps({"query": task, "timeout": 4}).encode()
            req = urllib.request.Request(QUERY, data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=6) as r:
                d = json.loads(r.read())
            ctx = []
            for item in d.get("results", {}).get("lge", [])[:2]:
                ctx.append(item.get("content", "")[:150])
            return "\n".join(ctx) if ctx else ""
        except:
            return ""
    
    def armed_exec(self, args):
        """武装执行: 上下文注入 + 执行 + 基因写回 + 评测"""
        self.total_ops += 1
        task = " ".join(args) if args else "code_review"
        
        # 自感知: 注入LGE上下文
        context = self.inject_context(task)
        if context:
            os.environ["CODEX_CONTEXT"] = context[:500]
        
        # 执行Codex
        t0 = time.time()
        r = subprocess.run(["npx", "codex"] + args, capture_output=True, timeout=120)
        output = r.stdout.decode() if r.returncode == 0 else r.stderr.decode()
        elapsed = round((time.time()-t0)*1000)
        
        # 自进化: 基因写回
        gene_id = f"GENE-CODEX-ARMED-{hashlib.sha256(output.encode()).hexdigest()[:12]}"
        self._write_gene(gene_id, task, output[:500], quality=0.7 if r.returncode == 0 else 0.4)
        self.genes_written += 1
        
        # 自反思: 评测
        try:
            payload = json.dumps({"question": task, "answer": output[:300]}).encode()
            req = urllib.request.Request(EVAL, data=payload,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except:
            pass
        
        # 自协调: 心跳
        try:
            ver = subprocess.run(["npx","codex","--version"], capture_output=True, timeout=5).stdout.decode().strip()
            payload = json.dumps({"name": NODE, "services": {"codex": ver, "arsenal": "v1.0"}}).encode()
            req = urllib.request.Request(f"{BRIDGE}/heartbeat", data=payload,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except:
            pass
        
        return {
            "success": r.returncode == 0,
            "gene_id": gene_id[:12],
            "elapsed_ms": elapsed,
            "output": output[:800],
            "context_injected": bool(context)
        }
    
    def seven_self_full(self):
        """完整七自飞轮"""
        results = {}
        
        # 自感知
        try:
            r = subprocess.run(["npx","codex","--version"], capture_output=True, timeout=5)
            results["自感知"] = f"codex={r.stdout.decode().strip()}"
        except:
            results["自感知"] = "fail"
        
        # 自协调
        try:
            payload = json.dumps({"name": NODE}).encode()
            req = urllib.request.Request(f"{BRIDGE}/register", data=payload,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
            results["自协调"] = "registered"
        except:
            results["自协调"] = "fail"
        
        # 自愈合
        try:
            r = urllib.request.urlopen(f"{BRIDGE}/messages/health", timeout=5)
            d = json.loads(r.read())
            unread = d.get("per_node", {}).get(NODE, 0)
            results["自愈合"] = f"backlog_{unread}"
        except:
            results["自愈合"] = "fail"
        
        # 自进化
        knowledge = self.inject_context("编程最佳实践 七自飞轮")
        results["自进化"] = f"knowledge_{len(knowledge)}chars"
        
        # 自迭代
        try:
            r = subprocess.run(["npx","codex","--version"], capture_output=True, timeout=5)
            results["自迭代"] = r.stdout.decode().strip()
        except:
            results["自迭代"] = "fail"
        
        # 自反思
        gene_id = f"GENE-CODEX-7SELF-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]}"
        self._write_gene(gene_id, "seven_self_full", json.dumps(results, ensure_ascii=False)[:500],
            category="seven-self", quality=0.7)
        results["自反思"] = gene_id[:12]
        
        # 自约束
        results["自约束"] = "pass" if all("fail" not in str(v) for v in results.values()) else "violation"
        
        return results
    
    def _write_gene(self, gene_id, title, content, category="general", quality=0.5):
        try:
            payload = json.dumps({
                "gene_id": gene_id, "content": f"{title}\n{content[:1000]}",
                "category": category, "domain": "code",
                "quality_score": quality,
                "tags": ["Codex", "arsenal", "v1.0"]
            }).encode()
            req = urllib.request.Request(f"{LGE}/genes/write", data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=3)
        except:
            p = Path.home() / "lgox-ops/data/codex-arsenal-genes.jsonl"
            with open(p, "a") as f:
                f.write(json.dumps({"gene_id":gene_id,"ts":time.time()},ensure_ascii=False)+"\n")

if __name__ == "__main__":
    arsenal = CodexArsenal()
    if len(sys.argv) > 1:
        if sys.argv[1] == "seven":
            r = arsenal.seven_self_full()
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            r = arsenal.armed_exec(sys.argv[1:])
            print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"CodexArsenal V{arsenal.version}")
