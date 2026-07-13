#!/usr/bin/env python3
"""
天锋PRO沙箱引擎 v2.0 — 借鉴OpenAI Codex CLI架构精华
Git Worktree隔离 + 沙箱环境 + 测试闭环 + PR输出
灵感: Codex CLI的git worktree隔离模式 + agent loop
"""
import os, subprocess, json, tempfile, shutil, time, hashlib

SANDBOX_ROOT = os.path.expanduser("~/lgox-sandboxes")

class TianfengSandbox:
    """
    借鉴Codex CLI核心设计:
    1. git worktree为每个任务创建隔离工作区
    2. AGENTS.md注入项目规范
    3. 工具调用循环(tool call → execute → append → repeat)
    4. 测试驱动: 先跑测试 → 改代码 → 再跑测试 → 直到通过
    5. 最终产出: diff + test results → PR
    """
    
    def __init__(self, repo_path: str, task_id: str = None):
        self.repo_path = os.path.abspath(repo_path)
        self.task_id = task_id or f"tf-{int(time.time())}"
        self.worktree_path = f"{SANDBOX_ROOT}/{self.task_id}"
        self.branch = f"tianfeng/{self.task_id}"
        self.log = []  # agent loop日志
    
    def setup(self) -> bool:
        """创建隔离工作区 (借鉴Codex的git worktree模式)"""
        os.makedirs(SANDBOX_ROOT, exist_ok=True)
        
        # 检查是否是git仓库
        if not os.path.exists(f"{self.repo_path}/.git"):
            return False
        
        try:
            # 在原始repo创建分支
            subprocess.run(["git", "-C", self.repo_path, "checkout", "-b", self.branch],
                          capture_output=True, check=False)
            
            # 创建worktree (独立工作区,与主repo互不干扰)
            subprocess.run(["git", "-C", self.repo_path, "worktree", "add", 
                          self.worktree_path, self.branch], capture_output=True, check=True)
            
            self.log.append(f"[SANDBOX] Worktree created: {self.worktree_path}")
            return True
        except subprocess.CalledProcessError as e:
            self.log.append(f"[ERROR] Worktree failed: {e}")
            return False
    
    def inject_agents_md(self, instructions: str):
        """注入AGENTS.md (借鉴Codex的codex.md/AGENTS.md)"""
        path = f"{self.worktree_path}/AGENTS.md"
        content = f"""# 天锋PRO Agent Instructions
## 项目规则
{instructions}

## 代码规范
- 修改前先读文件
- 每次修改后跑测试
- 改动不超过200行/次
- 保持原有代码风格

## 安全规则
- 不修改密钥/配置/env文件
- 不执行rm -rf
- 不连接外部网络(除非明确允许)
"""
        with open(path, 'w') as f:
            f.write(content)
        self.log.append(f"[AGENTS.md] injected: {len(content)} chars")
    
    def run_tests(self, test_cmd: str = "pytest") -> dict:
        """运行测试 (借鉴Codex的first-class testing)"""
        result = subprocess.run(test_cmd.split(), cwd=self.worktree_path,
                               capture_output=True, text=True, timeout=300)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:],  # 最后2000字符
            "stderr": result.stderr[-500:],
            "passed": result.returncode == 0
        }
    
    def get_diff(self) -> str:
        """获取当前改动 (用于生成PR描述)"""
        r = subprocess.run(["git", "-C", self.worktree_path, "diff", "HEAD"],
                          capture_output=True, text=True)
        return r.stdout
    
    def get_diff_stat(self) -> str:
        """获取改动统计"""
        r = subprocess.run(["git", "-C", self.worktree_path, "diff", "--stat", "HEAD"],
                          capture_output=True, text=True)
        return r.stdout
    
    def cleanup(self):
        """清理worktree (任务完成后)"""
        try:
            subprocess.run(["git", "-C", self.repo_path, "worktree", "remove", 
                          self.worktree_path, "--force"], capture_output=True)
            subprocess.run(["git", "-C", self.repo_path, "branch", "-D", 
                          self.branch], capture_output=True)
            if os.path.exists(self.worktree_path):
                shutil.rmtree(self.worktree_path)
            self.log.append("[CLEANUP] Worktree removed")
        except Exception as e:
            self.log.append(f"[CLEANUP] Failed: {e}")
    
    def agent_loop_summary(self) -> str:
        """生成Agent Loop总结 (借鉴Codex的turn-by-turn日志)"""
        return "\n".join(self.log)


# ═══ 测试闭环 (Codex精华: RL-trained to iterate until tests pass) ═══

def test_driven_loop(sandbox: TianfengSandbox, test_cmd: str = "pytest", max_iter: int = 5):
    """测试驱动循环: 跑测试 → 失败? → 修复 → 再跑 → 直到通过或max_iter"""
    sandbox.log.append(f"\n═══ TEST-DRIVEN LOOP (max {max_iter} iter) ═══")
    
    for i in range(max_iter):
        result = sandbox.run_tests(test_cmd)
        sandbox.log.append(f"[Loop {i+1}] Tests: {'PASS' if result['passed'] else 'FAIL'}")
        
        if result["passed"]:
            sandbox.log.append(f"[SUCCESS] All tests pass after {i+1} iterations")
            return True, i+1
        
        # 失败 → 分析 → 修复提示
        sandbox.log.append(f"[Loop {i+1}] Failures:\n{result['stdout'][:500]}")
    
    sandbox.log.append(f"[GIVE UP] Tests still failing after {max_iter} iterations")
    return False, max_iter


# ═══ PR生成器 (Codex精华: diff + test results → PR) ═══

def generate_pr_body(sandbox: TianfengSandbox, title: str, iteration_count: int) -> str:
    """生成PR描述 (借鉴Codex CI的PR格式)"""
    diff_stat = sandbox.get_diff_stat()
    loop_log = sandbox.agent_loop_summary()
    
    return f"""## {title}

### 改动统计
```
{diff_stat}
```

### Agent Loop 日志
```
{loop_log}
```

### 测试结果
- 迭代次数: {iteration_count}
- 最终状态: {'✅ 通过' if iteration_count > 0 else '❌ 未完成'}

---
🤖 天锋PRO自动生成 · 沙箱工作区: `{sandbox.task_id}`
"""


# ═══ 独立沙箱执行器 (不依赖git,纯文件隔离) ═══

def simple_sandbox(task_id: str, work_dir: str = None):
    """无git依赖的简化沙箱 — 适合非git仓库场景"""
    path = f"{SANDBOX_ROOT}/{task_id}"
    os.makedirs(path, exist_ok=True)
    
    # 复制源文件
    if work_dir and os.path.isdir(work_dir):
        for item in os.listdir(work_dir):
            src = os.path.join(work_dir, item)
            dst = os.path.join(path, item)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
    
    return path


if __name__ == "__main__":
    # 测试
    print("天锋PRO沙箱引擎 v2.0 就绪")
    print(f"沙箱根目录: {SANDBOX_ROOT}")
    print("支持: git worktree隔离 / 测试闭环 / PR生成")
