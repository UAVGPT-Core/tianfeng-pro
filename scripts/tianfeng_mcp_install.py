#!/usr/bin/env python3
"""天锋PRO MCP安装器·配置Claude Code/Codex MCP"""
import json,sys,os
from pathlib import Path
CFG={"mcpServers":{"tianfeng-pro":{"command":"python3","args":[str(Path.home()/"lgox-ops/scripts/tianfeng_mcp_bridge.py")],"description":"天锋PRO-基因驱动代码生成·AST+五角审查"}}}
def install():
    for tool in["claude","codex"]:
        p=Path.home()/f".{tool}/mcp.json";p.parent.mkdir(parents=True,exist_ok=True)
        e=json.loads(p.read_text()) if p.exists() else{}
        e.setdefault("mcpServers",{}).update(CFG["mcpServers"])
        p.write_text(json.dumps(e,indent=2));print(f"✅ {tool}")
if __name__=="__main__":install()
