#!/usr/bin/env python3
"""
LGOX 工具守护者 v1.0 — Claude Tag模式·硅基同事
监听联邦桥@工具名→自动执行→回复频道
LGOX-CC + 天锋PRO + Codex + 智谱GLM 全接入
"""
import urllib.request,json,time,os,subprocess,threading
from datetime import datetime

BRIDGE='http://100.100.89.2:8765' if os.uname().nodename!='灵龙' else 'http://127.0.0.1:8765'
MY_NAME=os.environ.get('GUARDIAN_NAME','天枢')

TOOLS={
    'LGOX-CC':    {'cmd':['lgox-cc'],'node':'灵龙','desc':'自研AI编程工具'},
    '天锋PRO':    {'cmd':['tianfeng'],'node':'天枢','desc':'联邦首款产品化AI编程'},
    'Codex':      {'cmd':['codex'],'node':'天枢','desc':'OpenAI编程备选'},
    '智谱GLM':    {'cmd':['python3','-c','import zhipuai; print(zhipuai.__version__)'],'node':'天枢','desc':'国产大模型'},
}

def poll_actions():
    """监听联邦桥发给本工具的action消息"""
    for tool_name,tool_info in TOOLS.items():
        if tool_info['node']!=MY_NAME: continue  # 只在所属节点运行
        try:
            r=urllib.request.urlopen(f'{BRIDGE}/messages/inbox?node={urllib.request.quote(tool_name)}&limit=5',timeout=8)
            msgs=json.loads(r.read()).get('messages',[])
            for m in msgs:
                if m.get('msg_type') in ('action','task'):
                    content=m.get('content','')
                    from_node=m.get('from_node','?')
                    print(f'[{datetime.now().strftime("%H:%M")}] @{tool_name} 收到任务: {from_node} → {content[:80]}')
                    result=execute_tool(tool_name,tool_info,content)
                    reply(tool_name,from_node,result)
                    # 清除消息
                    urllib.request.urlopen(urllib.request.Request(f'{BRIDGE}/messages/clear',data=json.dumps({'node':tool_name}).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=5)
        except Exception as e:
            pass

def execute_tool(tool_name,tool_info,task):
    """执行工具·返回结果"""
    t0=time.time()
    try:
        cmd=tool_info['cmd']
        # 简化: 执行命令并捕获输出
        r=subprocess.run(cmd+[task] if isinstance(task,str) else cmd,
            capture_output=True,text=True,timeout=300,cwd=os.path.expanduser('~'))
        elapsed=time.time()-t0
        if r.returncode==0:
            output=r.stdout[:1000] if r.stdout else r.stderr[:1000]
            return f'OK {tool_name}完成({elapsed:.0f}s): {output[:500]}'
        else:
            return f'FAIL {tool_name}({elapsed:.0f}s): {r.stderr[:300]}'
    except Exception as e:
        return f'ERROR {tool_name}: {str(e)[:200]}'

def reply(tool_name,from_node,result):
    """回复到联邦桥·@发起人可见"""
    try:
        data=json.dumps({'to':from_node,'from':tool_name,'content':f'[{tool_name}硅基同事回复] {result}','type':'ack','topic':'工具执行回执'},ensure_ascii=False).encode()
        urllib.request.urlopen(urllib.request.Request(f'{BRIDGE}/messages/send',data=data,headers={'Content-Type':'application/json'},method='POST'),timeout=5)
    except: pass

def main():
    print(f'[工具守护者v1.0·{MY_NAME}] Claude Tag模式已启动')
    # 注册为联邦桥节点
    for tool_name,tool_info in TOOLS.items():
        if tool_info['node']==MY_NAME:
            try:
                urllib.request.urlopen(urllib.request.Request(f'{BRIDGE}/register',data=json.dumps({'name':tool_name,'status':'online','type':'tool'}).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=5)
                print(f'  注册: {tool_name} ✅')
            except: pass
    
    # 持续监听
    while True:
        poll_actions()
        time.sleep(5)

if __name__=='__main__':
    main()
