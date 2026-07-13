#!/usr/bin/env python3
"""
LGOX-CC V7.0 — 联邦编程大将·1000/100
═══════════════════════════════════════
升级: CLI入口·沙箱隔离·主动修复·Codex集成·七自全闭环
基因ID: GENE-PRO-lgox-cc-v7
"""
import json, os, sys, subprocess, time, hashlib, shutil, urllib.request, tempfile
from pathlib import Path
from datetime import datetime

BRIDGE = "http://127.0.0.1:8765"
LGE = "http://100.116.0.29:8200"
QUERY = "http://127.0.0.1:8769/query"
EVAL = "http://127.0.0.1:8771/eval"
NODE = "LGOX-CC"
SANDBOX_ROOT = Path.home() / "lgox-sandboxes"

class LGOX_CC_V7:
    def __init__(self):
        self.version = "7.0.0"
        self.start_time = time.time()
    
    # ═══ CLI入口 ═══
    def cli(self, args):
        """统一CLI: lgox-cc <command> [args]"""
        cmds = {
            "status": self.cmd_status,
            "seven": self.cmd_seven_self,
            "sandbox": self.cmd_sandbox,
            "review": self.cmd_review,
            "fix": self.cmd_fix,
            "arsenal": self.cmd_arsenal,
            "video": self.cmd_video,
            "register": self.cmd_register,
            "help": self.cmd_help,
        }
        cmd = args[0] if args else "status"
        fn = cmds.get(cmd, self.cmd_help)
        fn(args[1:] if len(args) > 1 else [])
    
    def cmd_status(self, _):
        """lgox-cc status — 全状态一览"""
        print(f"LGOX-CC V{self.version}")
        print(f"Codex: {self._codex_version()}")
        print(f"Bridge: {self._bridge_health()}")
        print(f"Sandbox: {self._sandbox_count()}个活跃")
        r = subprocess.run(["python3", str(Path.home()/"lgox-ops/scripts/lgox-cc-seven-self.py")],
            capture_output=True, timeout=10)
        for line in r.stdout.decode().split('\n'):
            if '七自' in line or '通过' in line:
                print(line.strip())
    
    def cmd_seven_self(self, _):
        """lgox-cc seven — 运行七自飞轮"""
        subprocess.run(["python3", str(Path.home()/"lgox-ops/scripts/lgox-cc-seven-self.py")])
    
    def cmd_sandbox(self, args):
        """lgox-cc sandbox <repo_path> <task> — 沙箱隔离执行"""
        repo = args[0] if args else "."
        task = args[1] if len(args) > 1 else "auto"
        result = self._sandbox_execute(repo, task)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    def cmd_review(self, args):
        """lgox-cc review <file> — Codex深度审查"""
        target = args[0] if args else "."
        result = self._codex_review(target)
        print(result)
    
    def cmd_fix(self, args):
        """lgox-cc fix — 主动修复断裂"""
        result = self._active_repair()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    def cmd_arsenal(self, args):
        """lgox-cc arsenal <target> — 全武装扫描修复"""
        target = args[0] if args else "."
        subprocess.run(["python3", str(Path.home()/"lgox-ops/scripts/lgox-cc-arsenal-v8.py"), target])
    
    def cmd_video(self, args):
        """lgox-cc video <task> — 视频任务智能路由"""
        task = " ".join(args) if args else "LGOX产品介绍视频"
        subprocess.run(["python3", "/Users/a112233/lgox-ops/scripts/video-matrix.py", task])
    
    def cmd_register(self, _):
        """lgox-cc register — 注册联邦桥"""
        payload = json.dumps({
            "name": NODE, "ip": "100.120.20.52",
            "hostname": "mac-mini", "role": "联邦编程大将·V7.0",
            "services": {"codex": self._codex_version(), "lgox-cc": f"v{self.version}"}
        }).encode()
        req = urllib.request.Request(f"{BRIDGE}/register", data=payload,
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=5)
        print(json.loads(r.read()))
    
    def cmd_help(self, _):
        print("""LGOX-CC V7.0 — 联邦编程大将
  status    全状态一览
  seven     运行七自飞轮
  sandbox   <repo> <task>  沙箱隔离执行
  review    <file>         Codex深度审查
  fix       主动修复断裂
  register  注册联邦桥
  help      帮助""")
    
    # ═══ 沙箱隔离 ═══
    def _sandbox_execute(self, repo_path, task):
        """Git Worktree沙箱隔离执行"""
        SANDBOX_ROOT.mkdir(exist_ok=True)
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        sandbox = SANDBOX_ROOT / f"sandbox_{task_id}"
        
        try:
            repo = Path(repo_path).resolve()
            if not (repo / ".git").exists():
                # 非git项目·直接复制
                shutil.copytree(repo, sandbox)
            else:
                subprocess.run(["git", "-C", str(repo), "worktree", "add", str(sandbox), "HEAD"],
                    capture_output=True, timeout=30)
            
            # 注入AGENTS.md
            agents_md = sandbox / "AGENTS.md"
            agents_md.write_text(f"# LGOX-CC V7.0 Sandbox\nTask: {task}\nNode: {NODE}\nTime: {datetime.now().isoformat()}")
            
            # Codex执行
            r = subprocess.run(["npx", "codex", "exec", task], cwd=str(sandbox),
                capture_output=True, timeout=120)
            
            output = r.stdout.decode()[:2000]
            success = r.returncode == 0
            
            # 基因写回
            gene_id = f"GENE-CC-SANDBOX-{hashlib.sha256(output.encode()).hexdigest()[:12]}"
            self._write_gene(gene_id, f"sandbox:{task_id}:{task}", output[:500], 
                category="sandbox", quality=0.7 if success else 0.3)
            
            # 清理
            if (repo / ".git").exists():
                subprocess.run(["git", "-C", str(repo), "worktree", "remove", str(sandbox), "--force"],
                    capture_output=True, timeout=10)
            else:
                shutil.rmtree(sandbox, ignore_errors=True)
            
            return {"task": task, "sandbox": str(sandbox), "success": success,
                "gene": gene_id[:16], "output_len": len(output)}
        except Exception as e:
            return {"task": task, "error": str(e)}
    
    # ═══ Codex集成 ═══
    def _codex_review(self, target):
        """Codex深度代码审查"""
        r = subprocess.run(["npx", "codex", "review", target], capture_output=True, timeout=60)
        output = r.stdout.decode()
        # 写入基因
        gene_id = f"GENE-CC-REVIEW-{hashlib.sha256(output.encode()).hexdigest()[:12]}"
        self._write_gene(gene_id, f"review:{target}", output[:500], category="review", quality=0.6)
        return f"[{gene_id[:12]}] {output[:500]}"
    
    def _codex_version(self):
        try:
            r = subprocess.run(["npx", "codex", "--version"], capture_output=True, timeout=5)
            return r.stdout.decode().strip()
        except:
            return "unknown"
    
    # ═══ 主动修复 ═══
    def _active_repair(self):
        """主动检测并修复断裂"""
        fixes = []
        
        # 1. 桥连通修复
        if not self._bridge_health():
            fixes.append({"item": "bridge", "action": "register", "result": "retry"})
            try:
                self.cmd_register([])
                fixes[-1]["result"] = "fixed"
            except:
                fixes[-1]["result"] = "failed"
        
        # 2. 积压清零
        try:
            r = urllib.request.urlopen(f"{BRIDGE}/messages/health", timeout=5)
            d = json.loads(r.read())
            unread = d.get("per_node", {}).get(NODE, 0)
            if unread > 10:
                payload = json.dumps({"name": NODE}).encode()
                req = urllib.request.Request(f"{BRIDGE}/messages/clear", data=payload,
                    headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
                fixes.append({"item": "backlog", "cleared": unread})
        except:
            pass
        
        # 3. 基因同步
        try:
            payload = json.dumps({"query": "LGOX-CC 七自 编程", "timeout": 5}).encode()
            req = urllib.request.Request(QUERY, data=payload,
                headers={"Content-Type": "application/json"})
            r = urllib.request.urlopen(req, timeout=8)
            evidence = json.loads(r.read()).get("evidence", [])
            if evidence:
                fixes.append({"item": "gene_sync", "genes": len(evidence)})
        except:
            fixes.append({"item": "gene_sync", "result": "query_failed"})
        
        # 4. 运行七自
        try:
            subprocess.run(["python3", str(Path.home()/"lgox-ops/scripts/lgox-cc-seven-self.py")],
                capture_output=True, timeout=15)
            fixes.append({"item": "seven_self", "result": "executed"})
        except:
            fixes.append({"item": "seven_self", "result": "failed"})
        
        return {"node": NODE, "version": self.version, "fixes": fixes, "count": len(fixes)}
    
    # ═══ 工具方法 ═══
    def _bridge_health(self):
        try:
            r = urllib.request.urlopen(f"{BRIDGE}/health", timeout=3)
            return json.loads(r.read()).get("status") == "ok"
        except:
            return False
    
    def _sandbox_count(self):
        if not SANDBOX_ROOT.exists():
            return 0
        return len([d for d in SANDBOX_ROOT.iterdir() if d.is_dir()])
    
    def _write_gene(self, gene_id, title, content, category="general", quality=0.5):
        try:
            payload = json.dumps({
                "gene_id": gene_id, "content": f"{title}\n{content[:1000]}",
                "category": category, "domain": "code",
                "quality_score": quality,
                "tags": ["LGOX-CC", "v7.0", category]
            }).encode()
            req = urllib.request.Request(f"{LGE}/genes/write", data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=3)
        except:
            # 本地存档
            p = Path.home() / "lgox-ops/data/cc-genes.jsonl"
            with open(p, "a") as f:
                f.write(json.dumps({"gene_id": gene_id, "content": content[:500], "ts": time.time()}, ensure_ascii=False) + "\n")

# ═══ CLI入口 ═══
if __name__ == "__main__":
    cc = LGOX_CC_V7()
    cc.cli(sys.argv[1:] if len(sys.argv) > 1 else ["status"])
