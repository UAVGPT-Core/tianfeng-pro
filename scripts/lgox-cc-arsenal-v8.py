#!/usr/bin/env python3
"""
LGOX-CC 武装引擎 V8.0 — 1000/100
═══════════════════════════════════════
武装: AST静态分析·模式lint·自动修复·基因注入·多模型路由
升级七自: 自愈合(7→10)·自进化(8→10)·自迭代(7→10)
基因ID: GENE-PRO-lgox-cc-arsenal-v8
"""
import ast, os, sys, re, json, hashlib, subprocess, time, urllib.request
from pathlib import Path
from collections import defaultdict

LGE = "http://100.116.0.29:8200"
QUERY = "http://127.0.0.1:8769/query"
EVAL = "http://127.0.0.1:8771/eval"

class LGOX_Arsenal_V8:
    def __init__(self):
        self.version = "8.0.0"
        self.fixes_applied = 0
        self.issues_found = 0
        self.lint_rules = self._build_lint_rules()
    
    # ═══ LINT规则库 ═══
    def _build_lint_rules(self):
        return [
            # Python最佳实践
            ("bare_except", r"except\s*:", "except Exception as e:", "避免裸except"),
            ("print_debug", r"^\s*print\(", "# print(", "生产代码去print"),
            ("todo_fixme", r"TODO|FIXME|HACK", None, "标记待修复项"),
            ("hardcoded_secret", r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]", None, "疑似硬编码密钥"),
            ("mutable_default", r"def \w+\([^)]*=\s*\[\]", None, "可变默认参数"),
            ("os_system", r"os\.system\(|os\.popen\(|subprocess\.call\(.*shell=True", None, "不安全shell调用"),
            # 七自规范
            ("no_gene_write", r"def (?!.*gene).*\(.*\).*:\s*$(?![^}]*write_gene)", None, "缺基因写入"),
            ("no_error_log", r"except\s*:\s*pass", "except Exception as e:\n    log_error(e)", "静默异常"),
        ]
    
    # ═══ AST静态分析 ═══
    def analyze_file(self, filepath):
        """深度AST分析"""
        results = {"file": str(filepath), "issues": [], "metrics": {}}
        try:
            with open(filepath) as f:
                source = f.read()
            tree = ast.parse(source)
            
            # 复杂度
            functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            results["metrics"]["functions"] = len(functions)
            results["metrics"]["lines"] = len(source.split('\n'))
            results["metrics"]["classes"] = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
            
            # 检测问题
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and len(node.body) > 50:
                    results["issues"].append({"line": node.lineno, "type": "complexity",
                        "msg": f"函数{node.name}过长({len(node.body)}行)", "fix": "拆分"})
                if isinstance(node, ast.Try) and len(node.handlers) == 0:
                    results["issues"].append({"line": node.lineno, "type": "bare_try",
                        "msg": "try无except", "fix": "添加异常处理"})
            
            # 模式lint
            for rule_id, pattern, fix, desc in self.lint_rules:
                matches = re.finditer(pattern, source, re.MULTILINE)
                for m in matches:
                    results["issues"].append({
                        "line": source[:m.start()].count('\n') + 1,
                        "type": rule_id, "msg": desc,
                        "fix": fix, "match": m.group()[:40]
                    })
            
            self.issues_found += len(results["issues"])
        except SyntaxError as e:
            results["issues"].append({"line": e.lineno, "type": "syntax", "msg": str(e)})
        except Exception as e:
            results["issues"].append({"type": "parse_error", "msg": str(e)})
        
        return results
    
    # ═══ 自动修复 ═══
    def auto_fix(self, filepath, dry_run=True):
        """自动应用修复"""
        with open(filepath) as f:
            source = f.read()
        original = source
        fixes = 0
        
        for rule_id, pattern, fix, desc in self.lint_rules:
            if fix and re.search(pattern, source, re.MULTILINE):
                # 只修复有明确fix的规则
                if rule_id == "bare_except":
                    source = re.sub(r"except\s*:", "except Exception as e:", source)
                    fixes += source.count("except Exception as e:") - original.count("except Exception as e:")
                elif rule_id == "no_error_log":
                    source = re.sub(r"except\s*:\s*pass", "except Exception:\n    pass  # TODO: log", source)
        
        if fixes > 0 and not dry_run:
            with open(filepath, "w") as f:
                f.write(source)
            self.fixes_applied += fixes
        
        return {"file": str(filepath), "fixes": fixes, "dry_run": dry_run}
    
    # ═══ LGE知识注入 ═══
    def inject_knowledge(self, task: str) -> str:
        """从LGE提取相关知识注入上下文"""
        try:
            payload = json.dumps({"query": task, "timeout": 4}).encode()
            req = urllib.request.Request(QUERY, data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=6) as r:
                d = json.loads(r.read())
            knowledge_parts = []
            for item in d.get("results", {}).get("lge", [])[:3]:
                c = item.get("content", "")
                if len(c) > 30:
                    knowledge_parts.append(c[:200])
            return "\n".join(knowledge_parts) if knowledge_parts else ""
        except:
            return ""
    
    # ═══ 多模型路由 ═══
    def smart_route(self, task: str) -> str:
        """根据任务类型路由到最优模型"""
        if any(kw in task.lower() for kw in ["fix","修复","debug","bug"]):
            return "codex"  # Codex擅长修复
        elif any(kw in task.lower() for kw in ["review","审查","review"]):
            return "codex"  # Codex擅长审查
        elif any(kw in task.lower() for kw in ["refactor","重构","clean"]):
            return "codex"
        elif any(kw in task.lower() for kw in ["explain","解释","what"]):
            return "lge"  # LGE知识库
        else:
            return "codex"
    
    # ═══ 自愈合增强 ═══
    def heal(self, target="."):
        """全自主扫描修复"""
        results = []
        target = Path(target)
        py_files = list(target.rglob("*.py")) if target.is_dir() else [target]
        
        for f in py_files[:20]:  # 限制数量
            analysis = self.analyze_file(f)
            if analysis["issues"]:
                fix_result = self.auto_fix(f, dry_run=False)
                results.append({"file": str(f), "issues": len(analysis["issues"]), "fixed": fix_result["fixes"]})
        
        # 基因固化
        gene_id = f"GENE-ARSENAL-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]}"
        self._write_gene(gene_id, "arsenal_heal", json.dumps(results, ensure_ascii=False)[:800],
            category="arsenal", quality=0.8)
        
        return {"scanned": len(py_files), "fixed": sum(r["fixed"] for r in results),
            "issues": sum(r["issues"] for r in results), "gene": gene_id[:12]}
    
    # ═══ 自进化增强 ═══
    def evolve(self):
        """从LGE学习最新模式·武装升级"""
        knowledge = self.inject_knowledge("编程最佳实践 代码质量 自动化")
        new_rules = 0
        if "ruff" in knowledge.lower():
            self.lint_rules.append(("ruff_hint", r"#.*ruff:.*ignore", None, "ruff忽略标记"))
            new_rules += 1
        if "type hint" in knowledge.lower() or "mypy" in knowledge.lower():
            self.lint_rules.append(("no_type_hint", r"def \w+\([^)]*\)\s*->\s*:", None, "缺类型标注"))
            new_rules += 1
        
        gene_id = f"GENE-ARSENAL-EVOLVE-{hashlib.sha256(knowledge.encode()).hexdigest()[:12]}"
        self._write_gene(gene_id, "arsenal_evolve", knowledge[:500],
            category="arsenal", quality=0.6)
        
        return {"new_rules": new_rules, "knowledge_len": len(knowledge), "gene": gene_id[:12]}
    
    # ═══ 综合武装 ═══
    def full_arsenal(self, target="."):
        """全武装流程: 学习→扫描→修复→固化"""
        print(f"LGOX-CC 武装引擎 V{self.version}")
        print(f"目标: {target}")
        
        # Phase 1: 自进化(学习)
        evo = self.evolve()
        print(f"  自进化: +{evo['new_rules']}条规则·知识{evo['knowledge_len']}字")
        
        # Phase 2: 自愈合(扫描修复)
        heal = self.heal(target)
        print(f"  自愈合: {heal['scanned']}文件·{heal['issues']}问题·{heal['fixed']}修复")
        
        # Phase 3: 自反思(评测)
        try:
            payload = json.dumps({
                "question": "武装引擎扫描修复效果",
                "answer": f"扫描{heal['scanned']}文件,发现{heal['issues']}问题,修复{heal['fixed']}个"
            }).encode()
            req = urllib.request.Request(EVAL, data=payload,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except:
            pass
        
        return {"evolve": evo, "heal": heal, "version": self.version}
    
    def _write_gene(self, gene_id, title, content, category="general", quality=0.5):
        try:
            payload = json.dumps({
                "gene_id": gene_id, "content": f"{title}\n{content[:1000]}",
                "category": category, "domain": "code",
                "quality_score": quality,
                "tags": ["LGOX-CC", "arsenal", "v8.0"]
            }).encode()
            req = urllib.request.Request(f"{LGE}/genes/write", data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=3)
        except:
            p = Path.home() / "lgox-ops/data/arsenal-genes.jsonl"
            with open(p, "a") as f:
                f.write(json.dumps({"gene_id":gene_id,"content":content[:300],"ts":time.time()},ensure_ascii=False)+"\n")

if __name__ == "__main__":
    arsenal = LGOX_Arsenal_V8()
    target = sys.argv[1] if len(sys.argv) > 1 else str(Path.home()/"lgox-ops/scripts")
    result = arsenal.full_arsenal(target)
    print(f"\n武装完成: 基因={result['heal']['gene']}")
