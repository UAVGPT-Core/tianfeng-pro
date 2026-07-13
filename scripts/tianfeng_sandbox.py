#!/usr/bin/env python3
"""
天锋PRO 代码沙箱 v3.0 — Git Worktree隔离执行
用法: TianfengSandbox(repo_path) → setup() → inject_agents_md(task)
"""
import os, subprocess, shutil, uuid, time, stat
from pathlib import Path
from datetime import datetime

SANDBOX_ROOT = os.path.expanduser("~/lgox-sandboxes")

class TianfengSandbox:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(os.path.expanduser(repo_path))
        self.repo_name = os.path.basename(self.repo_path.rstrip("/"))
        self.task_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        self.branch = f"tianfeng/{self.task_id}"
        self.worktree_path = os.path.join(SANDBOX_ROOT, f"{self.repo_name}_{self.task_id}")
        self.is_git = os.path.isdir(os.path.join(self.repo_path, ".git"))
    
    def setup(self) -> bool:
        """创建隔离工作区"""
        try:
            os.makedirs(SANDBOX_ROOT, exist_ok=True)
            if self.is_git:
                # Git worktree 隔离
                subprocess.run(["git", "-C", self.repo_path, "worktree", "add", "-b", self.branch, 
                              self.worktree_path], check=True, capture_output=True, timeout=30)
            else:
                # 非git目录: 拷贝
                if os.path.exists(self.worktree_path):
                    shutil.rmtree(self.worktree_path)
                shutil.copytree(self.repo_path, self.worktree_path, symlinks=True, ignore_dangling_symlinks=True)
            return True
        except Exception as e:
            print(f"Sandbox setup error: {e}")
            return False
    
    def inject_agents_md(self, task: str):
        """注入AGENTS.md任务描述"""
        agents_path = os.path.join(self.worktree_path, "AGENTS.md")
        content = f"# 天锋PRO 沙箱任务\n\n> **任务ID**: {self.task_id}\n> **创建时间**: {datetime.now().isoformat()}\n> **分支**: {self.branch}\n\n## 任务描述\n\n{task}\n\n---\n*此文件由天锋PRO自动生成*\n"
        with open(agents_path, "w") as f:
            f.write(content)
    
    def execute(self, code: str, workdir: str = ".") -> dict:
        """在沙箱中执行Python代码(兼容旧接口)"""
        import tempfile
        cwd = os.path.join(self.worktree_path, workdir)
        os.makedirs(cwd, exist_ok=True)
        script = os.path.join(cwd, f"_tianfeng_{uuid.uuid4().hex[:8]}.py")
        with open(script, "w") as f:
            f.write(code)
        t0 = time.time()
        try:
            r = subprocess.run(["python3", script], capture_output=True, text=True, 
                             timeout=30, cwd=cwd)
            elapsed = (time.time() - t0) * 1000
            return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr,
                    "returncode": r.returncode, "exception": None, "elapsed_ms": elapsed,
                    "script": script, "workdir": cwd}
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "TimeoutExpired(30s)", 
                    "returncode": -1, "exception": "TimeoutExpired", "elapsed_ms": 30000,
                    "script": script, "workdir": cwd}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e), 
                    "returncode": -1, "exception": str(e), "elapsed_ms": 0,
                    "script": script, "workdir": cwd}
        finally:
            try: os.remove(script)
            except Exception as e: pass
    
    def health(self) -> dict:
        """健康检查"""
        return {
            "healthy": os.path.isdir(self.worktree_path),
            "sandbox_root": SANDBOX_ROOT,
            "worktree": self.worktree_path,
            "branch": self.branch,
            "is_git": self.is_git,
            "task_id": self.task_id
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 tianfeng_sandbox.py <repo_path>")
        sys.exit(1)
    sb = TianfengSandbox(sys.argv[1])
    print(f"Repo: {sb.repo_path}")
    print(f"Git: {sb.is_git}")
    if sb.setup():
        print(f"✅ Sandbox: {sb.worktree_path}")
        print(f"   Branch: {sb.branch}")
    else:
        print("❌ Failed")
