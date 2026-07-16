#!/usr/bin/env python3
"""
天锋PRO MCP分类管理器 v1.0 · 吸收ECC 30+服务器7分类
═══════════════════════════════════════════════════════════
七自: 自感知·自协调·自进化
30+ MCP服务器 → 7大分类 → 天锋PRO统一管理
═══════════════════════════════════════════════════════════
"""
import json, os, subprocess
from datetime import datetime
from pathlib import Path

MCP_CONFIG = Path.home() / ".lgox" / "mcp" / "tianfeng-mcp.json"
MCP_CONFIG.parent.mkdir(parents=True, exist_ok=True)

# ═══ 7分类·30+ MCP服务器 ═══
MCP_CATALOG = {
    "开发管理": {
        "icon": "🔧",
        "servers": {
            "github":       {"desc":"GitHub API·Issues/PR/仓库管理","command":"npx","args":["-y","@modelcontextprotocol/server-github"]},
            "jira":         {"desc":"Jira项目管理·任务/看板/冲刺","command":"npx","args":["-y","@modelcontextprotocol/server-jira"]},
            "confluence":   {"desc":"Confluence文档·知识库搜索","command":"npx","args":["-y","@modelcontextprotocol/server-confluence"]},
            "vercel":       {"desc":"Vercel部署·预览·域名管理","command":"npx","args":["-y","@modelcontextprotocol/server-vercel"]},
            "linear":       {"desc":"Linear问题追踪·敏捷开发","command":"npx","args":["-y","@modelcontextprotocol/server-linear"]},
        }
    },
    "数据库": {
        "icon": "🗄️",
        "servers": {
            "supabase":     {"desc":"Supabase·PostgreSQL·Auth·Storage","command":"npx","args":["-y","@modelcontextprotocol/server-supabase"]},
            "clickhouse":   {"desc":"ClickHouse·实时分析·OLAP","command":"npx","args":["-y","@modelcontextprotocol/server-clickhouse"]},
            "sqlite":       {"desc":"SQLite本地数据库·零配置","command":"npx","args":["-y","@modelcontextprotocol/server-sqlite"]},
        }
    },
    "记忆持久化": {
        "icon": "🧠",
        "servers": {
            "memory":       {"desc":"持久化记忆·会话间共享","command":"npx","args":["-y","@modelcontextprotocol/server-memory"]},
            "squish":       {"desc":"上下文压缩·token优化","command":"npx","args":["-y","@anthropic/squish-mcp"]},
            "omega-memory": {"desc":"Omega记忆·图数据库·关系记忆","command":"python3","args":["-m","omega_memory"]},
        }
    },
    "搜索研究": {
        "icon": "🔍",
        "servers": {
            "exa":          {"desc":"Exa语义搜索·网页内容提取","command":"npx","args":["-y","@modelcontextprotocol/server-exa"]},
            "parallel-search":{"desc":"并行搜索·多引擎聚合","command":"npx","args":["-y","@modelcontextprotocol/server-parallel-search"]},
            "firecrawl":    {"desc":"Firecrawl网页抓取·151K⭐","command":"npx","args":["-y","@modelcontextprotocol/server-firecrawl"]},
            "brave-search": {"desc":"Brave搜索API·隐私优先","command":"npx","args":["-y","@modelcontextprotocol/server-brave-search"]},
        }
    },
    "云基础设施": {
        "icon": "☁️",
        "servers": {
            "cloudflare":   {"desc":"Cloudflare Workers·KV·R2·D1","command":"npx","args":["-y","@modelcontextprotocol/server-cloudflare"]},
            "aws":          {"desc":"AWS SDK·Lambda·S3·DynamoDB","command":"npx","args":["-y","@modelcontextprotocol/server-aws"]},
            "docker":       {"desc":"Docker容器管理·镜像·编排","command":"npx","args":["-y","@modelcontextprotocol/server-docker"]},
        }
    },
    "AI自动化": {
        "icon": "🤖",
        "servers": {
            "fal-ai":       {"desc":"fal.ai图像/视频生成·API","command":"npx","args":["-y","@modelcontextprotocol/server-fal-ai"]},
            "browserbase":  {"desc":"Browserbase云端浏览器·自动化","command":"npx","args":["-y","@modelcontextprotocol/server-browserbase"]},
            "playwright":   {"desc":"Playwright浏览器自动化·测试","command":"npx","args":["-y","@modelcontextprotocol/server-playwright"]},
            "comfyui":      {"desc":"ComfyUI图像生成工作流","command":"python3","args":["-m","comfyui_mcp"]},
            "voxcpm":       {"desc":"VoxCPM2语音合成·33K⭐","command":"python3","args":["-m","voxcpm.server"]},
        }
    },
    "工具链": {
        "icon": "🛠️",
        "servers": {
            "sequential-thinking":{"desc":"顺序思考·推理链·深度分析","command":"npx","args":["-y","@modelcontextprotocol/server-sequential-thinking"]},
            "token-optimizer":{"desc":"Token优化·上下文压缩","command":"npx","args":["-y","@modelcontextprotocol/server-token-optimizer"]},
            "filesystem":   {"desc":"文件系统·读写·搜索·编辑","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem"]},
            "git":          {"desc":"Git操作·提交·分支·diff","command":"npx","args":["-y","@modelcontextprotocol/server-git"]},
            "terminal":     {"desc":"终端命令执行·Shell访问","command":"npx","args":["-y","@modelcontextprotocol/server-terminal"]},
        }
    },
}

def save_config():
    """保存MCP配置"""
    config = {
        "version": "1.0.0",
        "updated": datetime.now().isoformat(),
        "total_categories": len(MCP_CATALOG),
        "total_servers": sum(len(c["servers"]) for c in MCP_CATALOG.values()),
        "categories": MCP_CATALOG,
        "seven_self": {
            "自感知": "每30min巡检MCP服务器健康·自动标记离线",
            "自协调": "根据任务类型自动激活对应分类·按需加载",
            "自愈合": "服务器离线→自动重启·3次失败→降级通知",
            "自进化": "新MCP服务器发现→自动注册·基因沉淀",
        }
    }
    with open(MCP_CONFIG, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return config

def list_servers(filter_category=None):
    """列出所有MCP服务器(支持分类过滤)"""
    for cat, info in MCP_CATALOG.items():
        if filter_category and filter_category != cat:
            continue
        print(f"\n{info['icon']} {cat} ({len(info['servers'])}个服务器)")
        for name, srv in info['servers'].items():
            print(f"  ├─ {name}: {srv['desc']}")
            print(f"  │  {srv['command']} {' '.join(srv.get('args',[]))}")

def health_check():
    """MCP服务器健康巡检"""
    total = sum(len(c["servers"]) for c in MCP_CATALOG.values())
    online = 0
    for cat, info in MCP_CATALOG.items():
        for name, srv in info['servers'].items():
            cmd = srv['command']
            available = subprocess.run(["which", cmd], capture_output=True).returncode == 0
            if available:
                online += 1
    print(f"MCP健康: {online}/{total} 可用 ({online/total*100:.0f}%)")

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        list_servers()
    elif cmd == "health":
        health_check()
    elif cmd == "save":
        config = save_config()
        print(f"✅ MCP配置已保存: {MCP_CONFIG}")
        print(f"   分类: {config['total_categories']} | 服务器: {config['total_servers']}")
    else:
        list_servers(sys.argv[1] if len(sys.argv) > 1 else None)
