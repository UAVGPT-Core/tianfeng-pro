#!/usr/bin/env python3
"""天锋PRO MCP协议桥·吸收OpenClaw MCP模式·外部Agent可调用天锋PRO工具"""
import json,sys
TOOLS=[{"name":"tianfeng_code","description":"基因驱动代码生成·79万基因上下文注入","inputSchema":{"type":"object","properties":{"task":{"type":"string"}},"required":["task"]}},{"name":"tianfeng_review","description":"AST+五角双重代码审查","inputSchema":{"type":"object","properties":{"code":{"type":"string"}},"required":["code"]}},{"name":"tianfeng_gene_search","description":"搜索79万LGE基因库","inputSchema":{"type":"object","properties":{"query":{"type":"string"},"n_results":{"type":"integer","default":5}},"required":["query"]}}]
def handle(req):
    m=req.get("method");rid=req.get("id")
    if m=="initialize":return{"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","serverInfo":{"name":"tianfeng-pro","version":"5.1.0"},"capabilities":{"tools":{}}}}
    if m=="tools/list":return{"jsonrpc":"2.0","id":rid,"result":{"tools":TOOLS}}
    if m=="tools/call":return{"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":f"[天锋PRO] 工具{req['params']['name']}就绪·请在CLI获取完整输出"}]}}
    if m=="notifications/initialized":return None
    return{"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Unknown:{m}"}}
if __name__=="__main__":
    for line in sys.stdin:
        try:
            r=json.loads(line.strip());resp=handle(r)
            if resp:sys.stdout.write(json.dumps(resp,ensure_ascii=False)+"\n");sys.stdout.flush()
        except:continue
