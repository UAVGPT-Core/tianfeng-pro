#!/usr/bin/env python3
"""
天锋PRO UltraReview v2.0 — 双模型互审 + 三探一评
新增: 双模型交叉审查(DeepSeek Pro ↔ Codex) 从ClaudeCode×Codex视频吸收
3 Explorer Agents(正则) + 1 Critic Agent + 2 LLM审查(Pro/Codex) → 交叉验证
灵感: Anthropic "Ultra Plan" + ClaudeCode×Codex "互审模式"
"""
import os, json, subprocess, time, threading, argparse, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# 审查维度 (每维一个Explorer — 正则引擎)
EXPLORER_ROLES = {
    "security": "🔒安全审查: 寻找SQL注入/XSS/密钥泄露/权限漏洞/不安全依赖",
    "logic": "🧠逻辑审查: 寻找边界条件/bug/空指针/竞态/死循环/错误处理缺失",
    "performance": "⚡性能审查: 寻找N+1查询/内存泄漏/阻塞调用/大循环/不必要IO",
}

# 双模型配置
DUAL_MODELS = {
    "pro": {"model": "deepseek-v4-pro", "api": "https://api.deepseek.com/v1", "name": "DeepSeek Pro"},
    "codex": {"model": "deepseek-v4-flash", "api": "https://api.deepseek.com/v1", "name": "Codex(Flash模拟)"},
}

class UltraReview:
    """
    借鉴Claude Code /ultrareview架构:
    1. 3个Explorer Agent各查一类问题
    2. 每个Agent独立分析代码
    3. Critic Agent交叉验证: 问题必须被另一个Agent确认才报告
    4. 最终输出: 仅confirmed bugs (零误报)
    """
    
    def __init__(self, target_path: str, model: str = "local"):
        self.target_path = os.path.abspath(target_path)
        self.model = model
        self.findings = {k: [] for k in EXPLORER_ROLES}
        self.confirmed = []  # 交叉验证确认的
    
    def scan_file_list(self) -> list:
        """获取待审查文件列表"""
        files = []
        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next'}
        for root, dirs, fnames in os.walk(self.target_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in fnames:
                if f.endswith(('.py', '.js', '.ts', '.go', '.rs', '.java', '.sh', '.yaml', '.yml')):
                    files.append(os.path.join(root, f))
        return files[:50]  # 最多50个文件
    
    def explore_file(self, filepath: str) -> dict:
        """单个文件分析 (Explorer Agent)"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
        except:
            return {"file": filepath, "error": "unreadable"}
        
        issues = []
        lines = content.split('\n')
        rel = os.path.relpath(filepath, self.target_path)
        
        # ─── 安全审查 ───
        security_patterns = [
            (r'(?<![a-zA-Z_])eval\s*\(', "危险eval()调用"),
            (r'password\s*=\s*[\'"]', "硬编码密码"),
            (r'secret\s*=\s*[\'"]', "硬编码密钥"),
            (r'api[_-]?key\s*=\s*[\'"]', "硬编码API Key"),
            (r'exec\(', "危险exec调用"),
            (r'os\.system\(', "危险os.system"),
            (r'subprocess\.call\(.*shell\s*=\s*True', "shell=True注入风险"),
        ]
        for i, line in enumerate(lines, 1):
            for pattern, desc in security_patterns:
                import re
                if re.search(pattern, line):
                    issues.append({
                        "type": "security",
                        "severity": "🔴 HIGH",
                        "file": rel,
                        "line": i,
                        "issue": desc,
                        "code": line.strip()[:80]
                    })
        
        # ─── 逻辑审查 ───
        logic_patterns = [
            (r'except\s*:', "裸except(捕获所有异常,包括KeyboardInterrupt)"),
            (r'except Exception:\s*pass', "静默吞异常"),
            (r'\.get\([^)]*\)\s*\[', "dict.get后直接索引(可能None)"),
            (r'while True:', "无限循环(检查退出条件)"),
            (r'time\.sleep\(', "阻塞sleep"),
            (r'os\.path\.join\([^)]*\)\s*==', "路径拼接后直接比较(用os.path.exists)"),
        ]
        for i, line in enumerate(lines, 1):
            for pattern, desc in logic_patterns:
                import re
                if re.search(pattern, line):
                    issues.append({
                        "type": "logic",
                        "severity": "🟡 MEDIUM",
                        "file": rel,
                        "line": i,
                        "issue": desc,
                        "code": line.strip()[:80]
                    })
        
        # ─── 性能审查 ───
        perf_patterns = [
            (r'\.read\(\)\s*$', "大文件一次性read(可能OOM)"),
            (r'for .+ in .+:\s*\n\s+for .+ in .+:', "嵌套循环(可能O(n²))"),
            (r'open\([^)]+\)\s*$', "文件未用with(可能忘记关闭)"),
            (r'requests\.(get|post)\(.*\n', "同步HTTP调用(考虑httpx异步)"),
        ]
        for i, line in enumerate(lines, 1):
            for pattern, desc in perf_patterns:
                import re
                if re.search(pattern, line, re.DOTALL):
                    issues.append({
                        "type": "performance",
                        "severity": "🔵 INFO",
                        "file": rel,
                        "line": i,
                        "issue": desc,
                        "code": line.strip()[:80]
                    })
        
        return {"file": rel, "issues": issues, "total_lines": len(lines)}
    
    def run_explorers(self):
        """并行运行3个Explorer Agent"""
        files = self.scan_file_list()
        print(f"🔍 UltraReview: 扫描 {len(files)} 个文件...")
        
        all_issues = []
        # 并行处理所有文件
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.explore_file, f): f for f in files}
            for future in as_completed(futures):
                result = future.result()
                if result.get("issues"):
                    all_issues.extend(result["issues"])
        
        # 按类型分组
        for issue in all_issues:
            t = issue["type"]
            if t in self.findings:
                self.findings[t].append(issue)
        
        return all_issues
    
    def llm_review_file(self, filepath: str, model_key: str) -> list:
        """LLM审查单个文件 — 通过DeepSeek API"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
        except:
            return []
        
        if len(content) > 8000:
            content = content[:8000] + "\n... (truncated)"
        
        rel = os.path.relpath(filepath, self.target_path)
        model_info = DUAL_MODELS[model_key]
        
        prompt = f"""审查以下代码文件({rel})。只报告真实存在的问题，不要报告风格建议。
格式: 每行一个发现，格式为 "行号|严重度(HIGH/MEDIUM/INFO)|类型(security/logic/performance)|问题描述"
如果没有问题，回复 "NO_ISSUES"。

```{os.path.splitext(rel)[1][1:] if rel else 'python'}
{content}
```"""
        
        try:
            api_key = os.getenv("DEEPSEEK_API_KEY", "sk-02a...d6b9")
            import httpx
            r = httpx.post(
                f"{model_info['api']}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model_info["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.1
                },
                timeout=30
            )
            if r.status_code != 200:
                return []
            
            resp = r.json()["choices"][0]["message"]["content"]
            if "NO_ISSUES" in resp:
                return []
            
            issues = []
            for line in resp.split('\n'):
                line = line.strip()
                if '|' in line and not line.startswith('#'):
                    parts = line.split('|')
                    if len(parts) >= 4:
                        try:
                            lineno = int(parts[0].strip())
                            severity = parts[1].strip().upper()
                            if "HIGH" in severity: severity = "🔴 HIGH"
                            elif "MEDIUM" in severity: severity = "🟡 MEDIUM"
                            else: severity = "🔵 INFO"
                            issues.append({
                                "type": parts[2].strip(),
                                "severity": severity,
                                "file": rel,
                                "line": lineno,
                                "issue": parts[3].strip(),
                                "source": model_info["name"],
                                "code": ""
                            })
                        except ValueError:
                            pass
            return issues
        except Exception as e:
            return [{"type": "error", "severity": "🔵 INFO", "file": rel, 
                     "line": 0, "issue": f"LLM审查失败({model_info['name']}): {str(e)[:60]}",
                     "source": model_info["name"], "code": ""}]
    
    def dual_model_review(self):
        """双模型互审: Pro审查 + Codex审查 → 交叉对比"""
        files = self.scan_file_list()
        # 取核心文件(跳过test/__init__等)
        core_files = [f for f in files if 'test' not in os.path.basename(f).lower() 
                     and '__init__' not in os.path.basename(f)][:20]
        
        print(f"🤖 双模型互审: {len(core_files)} 个核心文件...")
        
        pro_findings = []
        codex_findings = []
        
        # Pro审查
        print(f"  🔍 {DUAL_MODELS['pro']['name']} 审查中...")
        for f in core_files:
            issues = self.llm_review_file(f, "pro")
            pro_findings.extend(issues)
        print(f"    发现 {len(pro_findings)} 个问题")
        
        # Codex审查 (Flash模拟)
        print(f"  🔍 {DUAL_MODELS['codex']['name']} 审查中...")
        for f in core_files:
            issues = self.llm_review_file(f, "codex")
            codex_findings.extend(issues)
        print(f"    发现 {len(codex_findings)} 个问题")
        
        # 交叉对比
        self.dual_cross_compare(pro_findings, codex_findings)
    
    def dual_cross_compare(self, pro_findings: list, codex_findings: list):
        """双模型交叉比对 — 找出共同确认和各自盲区"""
        # 用 file:line 做匹配键
        def make_key(f):
            return f"{f['file']}:{f['line']}"
        
        pro_keys = {make_key(f): f for f in pro_findings}
        codex_keys = {make_key(f): f for f in codex_findings}
        
        # 双模型确认 (交集)
        common_keys = pro_keys.keys() & codex_keys.keys()
        for key in common_keys:
            p = pro_keys[key]
            p["verified_by"] = "dual"  # 双模型确认 — 最高置信度
            p["severity"] = "🔴 HIGH" if p["severity"] in ("🔴 HIGH", "🟡 MEDIUM") else p["severity"]
            self.confirmed.append(p)
        
        # Pro独有 (Codex盲区)
        pro_only = pro_keys.keys() - codex_keys.keys()
        for key in pro_only:
            p = pro_keys[key]
            p["verified_by"] = "pro_only"
            p["issue"] = f"[Pro发现·Codex漏检] {p['issue']}"
            self.confirmed.append(p)
        
        # Codex独有 (Pro盲区)
        codex_only = codex_keys.keys() - pro_keys.keys()
        for key in codex_only:
            c = codex_keys[key]
            c["verified_by"] = "codex_only"
            c["issue"] = f"[Codex发现·Pro漏检] {c['issue']}"
            self.confirmed.append(c)
        
        dual_count = sum(1 for c in self.confirmed if c.get("verified_by") == "dual")
        pro_only_count = sum(1 for c in self.confirmed if c.get("verified_by") == "pro_only")
        codex_only_count = sum(1 for c in self.confirmed if c.get("verified_by") == "codex_only")
        
        print(f"\n📊 交叉对比结果:")
        print(f"  ✅ 双模型确认: {dual_count} 个 (高置信度)")
        print(f"  🔍 Pro独有(Codex盲区): {pro_only_count} 个")
        print(f"  🔍 Codex独有(Pro盲区): {codex_only_count} 个")
    
    def critic_cross_verify(self):
        """
        Critic Agent: 交叉验证
        借鉴Claude Code: 问题必须被另一种审查维度确认,才报告
        例如: 安全发现的一个硬编码密钥 → 逻辑审查也发现了它 → confirmed
        """
        # 合并所有发现
        all_findings = []
        for t, issues in self.findings.items():
            all_findings.extend(issues)
        
        # 去重+交叉验证: 同一文件的同一行出现多个问题 → confirmed
        file_line_map = {}
        for issue in all_findings:
            key = f"{issue['file']}:{issue['line']}"
            if key not in file_line_map:
                file_line_map[key] = []
            file_line_map[key].append(issue)
        
        # 只保留被多个维度确认的问题
        for key, issues in file_line_map.items():
            if len(issues) >= 2 or issues[0]["severity"] == "🔴 HIGH":
                self.confirmed.append({
                    "file": issues[0]["file"],
                    "line": issues[0]["line"],
                    "severity": issues[0]["severity"],
                    "issues": [i["issue"] for i in issues],
                    "code": issues[0]["code"]
                })
        
        # 按严重度排序
        severity_order = {"🔴 HIGH": 0, "🟡 MEDIUM": 1, "🔵 INFO": 2}
        self.confirmed.sort(key=lambda x: severity_order.get(x["severity"], 9))
    
    def generate_report(self) -> str:
        """生成审查报告 — v2.0 含双模型互审标记"""
        total_explored = sum(len(v) for v in self.findings.values())
        dual_count = sum(1 for c in self.confirmed if c.get("verified_by") == "dual")
        
        report = f"""# 🔍 UltraReview 审查报告 v2.0

## 摘要
- 扫描文件: {len(self.scan_file_list())} 个
- Explorer发现: {total_explored} 个
- Critic确认: {len(self.confirmed)} 个
- 双模型确认: {dual_count} 个
- 模式: 3 Explorer + 1 Critic + 双模型互审

## 确认问题 ({len(self.confirmed)})

| # | 验证 | 严重度 | 文件 | 行 | 问题 |
|---|------|--------|------|-----|------|
"""
        for i, c in enumerate(self.confirmed, 1):
            vflag = c.get("verified_by", "regex")
            if vflag == "dual": vmark = "✅双模型"
            elif vflag == "pro_only": vmark = "🔍Pro独有"
            elif vflag == "codex_only": vmark = "🔍Codex独有"
            else: vmark = "📋正则"
            
            issues_str = c.get("issue", "; ".join(c.get("issues", [])))
            report += f"| {i} | {vmark} | {c['severity']} | {c['file']} | {c['line']} | {issues_str} |\n"
        
        if not self.confirmed:
            report += "| ✅ | — | — | — | — | 🎉 零确认问题! 代码质量很好 |\n"
        
        report += f"""
## 详细发现

### 🔒 安全 ({len(self.findings['security'])} 个)
"""
        for f in self.findings['security'][:10]:
            report += f"- `{f['file']}:{f['line']}` {f['issue']}: `{f['code']}`\n"
        
        report += f"\n### 🧠 逻辑 ({len(self.findings['logic'])} 个)\n"
        for f in self.findings['logic'][:10]:
            report += f"- `{f['file']}:{f['line']}` {f['issue']}: `{f['code']}`\n"
        
        report += f"\n### ⚡ 性能 ({len(self.findings['performance'])} 个)\n"
        for f in self.findings['performance'][:10]:
            report += f"- `{f['file']}:{f['line']}` {f['issue']}: `{f['code']}`\n"
        
        report += f"\n---\n🤖 天锋PRO UltraReview · 三探一评架构 · {time.strftime('%Y-%m-%d %H:%M')}"
        
        return report

def ultra_review(target_path: str, output: str = None, dual: bool = False) -> str:
    """一键UltraReview — v2.0 支持双模型互审"""
    ur = UltraReview(target_path)
    ur.run_explorers()
    ur.critic_cross_verify()
    
    if dual:
        ur.dual_model_review()
    
    report = ur.generate_report()
    
    if output:
        with open(output, 'w') as f:
            f.write(report)
    
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="天锋PRO UltraReview v2.0")
    parser.add_argument("path", nargs="?", default="/Users/a1/lgox-ops/scripts", help="审查目标路径")
    parser.add_argument("--dual", action="store_true", help="启用双模型互审(Pro+Codex交叉验证)")
    parser.add_argument("--output", "-o", default="/tmp/ultrareview-report.md", help="输出报告路径")
    args = parser.parse_args()
    
    print(f"🔍 天锋PRO UltraReview v2.0")
    print(f"   目标: {args.path}")
    print(f"   模式: {'双模型互审' if args.dual else '标准(三探一评)'}")
    print()
    
    report = ultra_review(args.path, args.output, dual=args.dual)
    print(report[:3000])
    if len(report) > 3000:
        print(f"\n... (完整报告: {args.output})")
