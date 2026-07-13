#!/usr/bin/env python3
"""
LGOX外部雷达 - 代码扫描扩展模块
===============================
为天锋PRO扫描全球代码资源: GitHub趋势·arXiv论文·HuggingFace模型·技术博客
遇水架桥·逢山筑路·缺什么扫什么

扫描目标:
  - GitHub Trending: 代码工具/框架/CLI
  - arXiv: 代码生成/程序综合/形式化验证论文
  - HuggingFace: 代码模型(CodeLlama/StarCoder/DeepSeek-Coder等)
  - 技术博客: 架构设计/工程实践

基因ID: GENE-RADAR-CODE-V1
"""

import json, os, time, re
from datetime import datetime
from pathlib import Path

HOME = os.path.expanduser("~")


def scan_github_code_trending():
    """
    GitHub Trending 代码工具扫描
    免费·无需API Key
    """
    results = []
    try:
        import urllib.request
        # GitHub Trending RSS (非官方但可用)
        for lang in ["python", "go", "rust", "typescript"]:
            url = f"https://github.com/trending/{lang}?since=weekly"
            req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Radar/1.0"})
            r = urllib.request.urlopen(req, timeout=15)
            html = r.read().decode()

            # 提取仓库名
            repos = re.findall(r'/([^/]+/[^/"]+)', html)
            for repo in list(set(repos))[:5]:
                if "/" in repo and not repo.startswith(("login", "settings", "explore")):
                    results.append({
                        "source": "github",
                        "language": lang,
                        "repo": repo,
                        "url": f"https://github.com/{repo}",
                    })
    except Exception as e:
        results.append({"source": "github", "error": str(e)})

    return results


def scan_arxiv_code_papers():
    """
    arXiv 代码相关论文扫描
    搜索: code generation, program synthesis, LLM code, formal verification
    """
    papers = []
    queries = [
        "code+generation+AND+large+language+model",
        "program+synthesis+AND+deep+learning",
        "automated+code+repair+AND+neural",
        "formal+verification+AND+LLM",
        "software+engineering+AND+AI+agent",
    ]

    try:
        import urllib.request, xml.etree.ElementTree as ET
        for query in queries[:3]:  # 限制以免超时
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
            r = urllib.request.urlopen(url, timeout=15)
            root = ET.fromstring(r.read())

            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()[:200]
                link = entry.find('{http://www.w3.org/2005/Atom}id').text.strip()
                papers.append({
                    "source": "arxiv",
                    "title": title,
                    "summary": summary,
                    "url": link,
                })
    except Exception as e:
        papers.append({"source": "arxiv", "error": str(e)})

    return papers


def scan_huggingface_code_models():
    """
    HuggingFace 代码模型扫描
    模型: CodeLlama, StarCoder, DeepSeek-Coder, Qwen-Coder等
    """
    models = [
        {"name": "deepseek-ai/DeepSeek-Coder-V2", "desc": "DeepSeek开源代码模型·MoE架构"},
        {"name": "Qwen/Qwen2.5-Coder-32B", "desc": "阿里通义千问代码模型·多语言"},
        {"name": "codellama/CodeLlama-34b", "desc": "Meta代码模型·Python特化"},
        {"name": "bigcode/starcoder2", "desc": "BigCode开源·多语言代码生成"},
        {"name": "cognitivecomputations/dolphin-2.9-llama3-8b", "desc": "通用+代码微调"},
    ]
    return [{"source": "huggingface", **m, "relevance": "high"} for m in models]


def scan_dev_blogs():
    """
    技术博客扫描
    """
    blogs = [
        {"source": "openai", "title": "OpenAI Codex Paper & Updates", "url": "https://openai.com/research"},
        {"source": "anthropic", "title": "Claude Code Architecture", "url": "https://docs.anthropic.com/en/docs/claude-code"},
        {"source": "deepseek", "title": "DeepSeek Coder V2 Tech Report", "url": "https://arxiv.org/abs/2406.11931"},
        {"source": "cursor", "title": "Cursor IDE Architecture", "url": "https://cursor.sh/blog"},
    ]
    return [{"source": "dev_blog", **b, "relevance": "reference"} for b in blogs]


def full_code_radar_scan():
    """
    全量代码雷达扫描
    """
    scan_id = f"radar-code-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    results = {
        "scan_id": scan_id,
        "timestamp": datetime.now().isoformat(),
        "target": "天锋PRO代码工具链增强",
        "github": scan_github_code_trending(),
        "arxiv": scan_arxiv_code_papers(),
        "huggingface": scan_huggingface_code_models(),
        "blogs": scan_dev_blogs(),
        "summary": {},
    }

    # 汇总
    gh_count = len([r for r in results["github"] if "error" not in r])
    ar_count = len([r for r in results["arxiv"] if "error" not in r])
    hf_count = len(results["huggingface"])
    bl_count = len(results["blogs"])
    results["summary"] = {
        "total_sources": 4,
        "total_items": gh_count + ar_count + hf_count + bl_count,
        "github_repos": gh_count,
        "arxiv_papers": ar_count,
        "huggingface_models": hf_count,
        "dev_blogs": bl_count,
    }

    return results


def ingest_to_lge(scan_results):
    """将扫描结果注入LGE基因库"""
    genes_written = 0
    for source_key, items in scan_results.items():
        if source_key in ("scan_id", "timestamp", "target", "summary"):
            continue
        for item in items:
            if "error" in item:
                continue
            content = f"[CodeRadar] {item.get('source','?')}: {item.get('title',item.get('repo','?'))} | {item.get('desc',item.get('summary',''))[:100]} | url:{item.get('url','')}"
            try:
                import urllib.request
                data = json.dumps({
                    "content": content[:300],
                    "memory_type": "semantic",
                    "source": "code-radar"
                }).encode()
                req = urllib.request.Request(
                    "http://100.116.0.29:8200/genes/write",
                    data=data, headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=8)
                genes_written += 1
            except:
                pass
    return genes_written


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"

    if cmd == "scan":
        result = full_code_radar_scan()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "ingest":
        result = full_code_radar_scan()
        count = ingest_to_lge(result)
        print(f"基因入库: {count}条")

    elif cmd == "summary":
        result = full_code_radar_scan()
        s = result["summary"]
        print(f"代码雷达扫描: {s['total_items']}项")
        print(f"  GitHub: {s['github_repos']}个仓库")
        print(f"  arXiv: {s['arxiv_papers']}篇论文")
        print(f"  HuggingFace: {s['huggingface_models']}个模型")
        print(f"  技术博客: {s['dev_blogs']}篇")
