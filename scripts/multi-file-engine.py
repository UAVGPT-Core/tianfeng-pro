#!/usr/bin/env python3
"""
天锋PRO·多文件全项目引擎 v1.0
==============================
2035核心: 基因驱动的全项目理解·多文件联动编辑
替代单文件模式: 扫描→依赖图→跨文件分析→多文件建议

吸收: Claude Code全项目理解 + Cursor多文件编辑
差异: 基因驱动·零token·联邦协同
"""

import json, sqlite3, os, re, ast, uuid, urllib.request
from datetime import datetime
from pathlib import Path
from collections import defaultdict

HOME = Path(os.environ.get("HOME", "/Users/a112233"))
LGE_URL = "http://100.116.0.29:8200"
MULTI_DB = HOME / "lgox-ops/data/multi-file-engine.db"

def init_db():
    conn = sqlite3.connect(MULTI_DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE, name TEXT, files_count INTEGER,
            languages TEXT, total_lines INTEGER,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS file_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_path TEXT, file_path TEXT,
            language TEXT, lines INTEGER, functions INTEGER,
            classes INTEGER, imports TEXT, exports TEXT,
            dependencies TEXT, gene_refs TEXT,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cross_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT, target_file TEXT,
            ref_type TEXT, symbol_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_path TEXT, file_path TEXT,
            suggestion TEXT, priority TEXT, gene_id TEXT,
            applied INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS flywheel_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT, projects_scanned INTEGER,
            files_analyzed INTEGER, cross_refs_found INTEGER,
            suggestions_made INTEGER, duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    return conn


# ══════════════════════════════════════════
# 项目扫描器
# ══════════════════════════════════════════

def scan_project(project_path):
    """扫描项目: 文件树+语言识别+统计"""
    path = Path(project_path).resolve()
    if not path.exists():
        return None
    
    files = []
    total_lines = 0
    languages = set()
    
    for f in path.rglob("*.py"):
        if "node_modules" in str(f) or "__pycache__" in str(f) or ".git" in str(f):
            continue
        try:
            content = f.read_text()
            lines = content.count("\n")
            total_lines += lines
            languages.add("Python")
            files.append({"path": str(f), "lines": lines, "content": content})
        except:
            pass
    
    for f in path.rglob("*.js"):
        if "node_modules" in str(f) or ".git" in str(f):
            continue
        try:
            content = f.read_text()
            lines = content.count("\n")
            total_lines += lines
            languages.add("JavaScript")
            files.append({"path": str(f), "lines": lines, "content": content[:5000]})
        except:
            pass
    
    return {
        "name": path.name,
        "path": str(path),
        "files": files,
        "files_count": len(files),
        "total_lines": total_lines,
        "languages": list(languages),
    }


# ══════════════════════════════════════════
# AST分析器: 提取函数/类/导入/导出
# ══════════════════════════════════════════

def analyze_python_file(filepath, content):
    """Python文件AST分析"""
    result = {"functions": [], "classes": [], "imports": [], "exports": []}
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result["functions"].append(node.name)
                # 检测是否公开
                if not node.name.startswith("_"):
                    result["exports"].append(node.name)
            elif isinstance(node, ast.ClassDef):
                result["classes"].append(node.name)
                result["exports"].append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    result["imports"].append(f"{node.module}")
    except:
        pass
    return result


def analyze_js_file(content):
    """JavaScript文件简单分析"""
    result = {"functions": [], "imports": [], "exports": []}
    # function声明
    for m in re.finditer(r'function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(', content):
        name = m.group(1) or m.group(2)
        if name: result["functions"].append(name)
    # import
    for m in re.finditer(r'(?:import|require)\s*\(?["\']([^"\']+)["\']', content):
        result["imports"].append(m.group(1))
    # export
    for m in re.finditer(r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)', content):
        result["exports"].append(m.group(1))
    return result


# ══════════════════════════════════════════
# 跨文件引用分析
# ══════════════════════════════════════════

def build_cross_refs(file_analyses, project_path):
    """构建跨文件引用图"""
    cross_refs = []
    
    # 建立符号→文件映射
    symbol_map = defaultdict(list)
    for filepath, analysis in file_analyses.items():
        for sym in analysis.get("exports", []):
            symbol_map[sym].append(filepath)
        for cls in analysis.get("classes", []):
            symbol_map[cls].append(filepath)
    
    # 检测每个文件的导入是否引用了项目内文件
    for filepath, analysis in file_analyses.items():
        for imp in analysis.get("imports", []):
            if imp in symbol_map:
                for target in symbol_map[imp]:
                    if target != filepath:
                        cross_refs.append({
                            "source": filepath,
                            "target": target,
                            "ref_type": "import",
                            "symbol": imp,
                        })
            # 模糊匹配(相对导入)
            imp_module = imp.split(".")[-1]
            if imp_module in symbol_map and imp_module != imp:
                for target in symbol_map[imp_module]:
                    if target != filepath:
                        cross_refs.append({
                            "source": filepath,
                            "target": target,
                            "ref_type": "relative_import",
                            "symbol": imp_module,
                        })
    
    return cross_refs


# ══════════════════════════════════════════
# 基因驱动跨文件建议
# ══════════════════════════════════════════

def generate_suggestions(project_info, cross_refs):
    """基于基因+跨文件分析生成建议"""
    suggestions = []
    
    # 1. 文件过大建议
    for f in project_info["files"]:
        if f["lines"] > 500:
            suggestions.append({
                "file": f["path"],
                "suggestion": f"文件{f['path'].split('/')[-1]}有{f['lines']}行，建议拆分为多个模块",
                "priority": "medium",
            })
    
    # 2. 循环依赖检测
    dep_graph = defaultdict(set)
    for ref in cross_refs:
        dep_graph[ref["source"]].add(ref["target"])
    
    for src, targets in dep_graph.items():
        for tgt in targets:
            if src in dep_graph.get(tgt, set()):
                suggestions.append({
                    "file": src,
                    "suggestion": f"检测到循环依赖: {src.split('/')[-1]} ↔ {tgt.split('/')[-1]}，建议重构",
                    "priority": "high",
                })
    
    # 3. 缺失__init__.py
    init_dirs = set()
    py_files = set()
    for f in project_info["files"]:
        d = str(Path(f["path"]).parent)
        if f["path"].endswith("__init__.py"):
            init_dirs.add(d)
        else:
            py_files.add(d)
    
    for d in py_files - init_dirs:
        if any(f["path"].endswith(".py") for f in project_info["files"] if str(Path(f["path"]).parent) == d):
            suggestions.append({
                "file": f"{d}/__init__.py",
                "suggestion": f"目录{d.split('/')[-1]}缺少__init__.py，建议添加使成为Python包",
                "priority": "low",
            })
    
    # 4. 单文件无导入(孤岛文件)
    file_imports = {}
    for ref in cross_refs:
        file_imports[ref["source"]] = True
        file_imports[ref["target"]] = True
    
    for f in project_info["files"]:
        if f["path"] not in file_imports and f["lines"] > 50:
            suggestions.append({
                "file": f["path"],
                "suggestion": f"文件{f['path'].split('/')[-1]}({f['lines']}行)可能是孤岛文件，无项目内引用",
                "priority": "low",
            })
    
    return suggestions


# ══════════════════════════════════════════
# 主引擎
# ══════════════════════════════════════════

def run_engine(project_path=None):
    conn = init_db()
    c = conn.cursor()
    start = datetime.now()
    run_id = f"mfe-{start.strftime('%Y%m%d-%H%M%S')}"
    
    # 默认扫描lgox-ops项目
    if not project_path:
        project_path = str(HOME / "lgox-ops")
    
    # ① 扫描
    project = scan_project(project_path)
    if not project:
        return {"error": "项目路径不存在"}
    
    # ② 逐个文件分析
    file_analyses = {}
    total_funcs = 0
    for f in project["files"][:50]:  # 限50文件避免过慢
        if f["path"].endswith(".py"):
            analysis = analyze_python_file(f["path"], f["content"][:5000])
        elif f["path"].endswith(".js"):
            analysis = analyze_js_file(f["content"][:5000])
        else:
            continue
        
        file_analyses[f["path"]] = analysis
        total_funcs += len(analysis.get("functions", [])) + len(analysis.get("classes", []))
        
        # 写入DB
        c.execute("""INSERT OR REPLACE INTO file_index 
            (project_path,file_path,language,lines,functions,classes,imports,exports,dependencies)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (project_path, f["path"],
             "Python" if f["path"].endswith(".py") else "JavaScript",
             f["lines"],
             len(analysis.get("functions", [])),
             len(analysis.get("classes", [])),
             json.dumps(analysis.get("imports", [])),
             json.dumps(analysis.get("exports", [])),
             json.dumps([])))
    
    # ③ 跨文件引用
    cross_refs = build_cross_refs(file_analyses, project_path)
    for ref in cross_refs:
        c.execute("INSERT INTO cross_refs (source_file,target_file,ref_type,symbol_name) VALUES (?,?,?,?)",
                  (ref["source"], ref["target"], ref["ref_type"], ref["symbol"]))
    
    # ④ 生成建议
    suggestions = generate_suggestions(project, cross_refs)
    for s in suggestions:
        c.execute("INSERT INTO suggestions (project_path,file_path,suggestion,priority) VALUES (?,?,?,?)",
                  (project_path, s["file"], s["suggestion"], s["priority"]))
    
    conn.commit()
    
    # ⑤ 统计
    c.execute("SELECT COUNT(*) FROM file_index WHERE project_path=?", (project_path,))
    files_analyzed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM cross_refs")
    total_refs = c.fetchone()[0]
    
    duration = int((datetime.now() - start).total_seconds() * 1000)
    
    c.execute("INSERT INTO flywheel_runs (run_id,projects_scanned,files_analyzed,cross_refs_found,suggestions_made,duration_ms) VALUES (?,?,?,?,?,?)",
              (run_id, 1, files_analyzed, total_refs, len(suggestions), duration))
    
    conn.commit()
    conn.close()
    
    result = {
        "run_id": run_id,
        "project": project["name"],
        "files_total": project["files_count"],
        "files_analyzed": files_analyzed,
        "total_lines": project["total_lines"],
        "languages": project["languages"],
        "functions_classes": total_funcs,
        "cross_references": total_refs,
        "suggestions": len(suggestions),
        "top_suggestions": [s["suggestion"][:100] for s in suggestions[:5]],
        "duration_ms": duration,
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    run_engine(path)
