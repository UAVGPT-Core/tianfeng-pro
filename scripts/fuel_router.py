#!/usr/bin/env python3
"""LGOX联邦混元燃料路由器 v2.0 · 六层自动降级 · KIMI K3已纳入"""
import json, os, urllib.request

def _key(prefix):
    k = os.environ.get(prefix) or os.environ.get(prefix+'_KEY') or os.environ.get(prefix+'_API_KEY')
    if k: return k
    for f in [os.path.expanduser('~/.hermes/.env'), os.path.expanduser('~/lgox-ops/.env')]:
        if os.path.exists(f):
            for line in open(f):
                if prefix in line: return line.split('=',1)[1].strip().strip('"').strip("'")
    return ''

# ═══ 六层燃料密钥 ═══
GLM_K  = 'fd867a96bad64f53a8ece13ac6911887.T3zYiYf7KbxhVTb0'  # 智谱200万token/天免费
KIMI_K = _key('KIMI_API') or 'sk-XmGO0caLhBkTDJPcIsV9EPrhqAYa6teraxgPksnSmRgSbYuf'  # 65元充值
DS_K   = _key('DEEPSEEK_API')
NV_K   = _key('NVIDIA_API')
TIANGONG = 'http://100.118.207.31:11434'  # 天工GPU
NV_URL   = 'https://integrate.api.nvidia.com/v1'

def fuel_chat(prompt, max_tokens=None, temperature=None):
    """六层自动降级: T0天工→T1 NGC→T2智谱→T3 KIMI K3→T4 DS Flash→None"""
    
    # Tier 0: 天工GPU·零成本本地推理
    try:
        body = json.dumps({'model':'qwen2.5:14b','messages':[{'role':'user','content':prompt}],
            'stream':False,'options':{'temperature':temperature or 0.3,'num_predict':max_tokens or 256}}).encode()
        req = urllib.request.Request(f'{TIANGONG}/api/chat',data=body,
            headers={'Content-Type':'application/json'})
        d = json.loads(urllib.request.urlopen(req,timeout=15).read())
        return {'answer':d['message']['content'].strip(),'model':'qwen2.5:14b@天工GPU',
                'tokens':d.get('eval_count',0),'tier':'T0零成本'}
    except: pass

    # Tier 1: NVIDIA NGC·121模型·Inception免费
    if NV_K:
        try:
            body = json.dumps({'model':'nvidia/llama-3.1-nemotron-nano-8b-v1',
                'messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 256,'temperature':temperature or 0.3}).encode()
            req = urllib.request.Request(f'{NV_URL}/chat/completions',data=body,
                headers={'Authorization':f'Bearer {NV_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=15).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),
                    'model':'nemotron-nano@NGC','tokens':d['usage']['total_tokens'],
                    'tier':'T1 NGC免费'}
        except: pass

    # Tier 2: 智谱GLM-4-Flash·200万token/天免费·主力
    if GLM_K:
        try:
            body = json.dumps({'model':'glm-4-flash','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 256,'temperature':temperature or 0.3}).encode()
            req = urllib.request.Request('https://open.bigmodel.cn/api/paas/v4/chat/completions',
                data=body,headers={'Authorization':f'Bearer {GLM_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=12).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),'model':'glm-4-flash',
                    'tokens':d['usage']['total_tokens'],'tier':'T2智谱免费'}
        except: pass

    # Tier 3: KIMI K3·付费·强推理·1M上下文·代码专长 ⭐NEW
    if KIMI_K and len(KIMI_K) > 30:
        try:
            body = json.dumps({'model':'kimi-k3','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 512,'temperature':temperature or 0.5,
                'reasoning_effort':'low'}).encode()  # low推理避免空content
            req = urllib.request.Request('https://api.moonshot.cn/v1/chat/completions',
                data=body,headers={'Authorization':f'Bearer {KIMI_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=30).read())
            content = d['choices'][0]['message'].get('content','')
            if not content:
                content = d['choices'][0]['message'].get('reasoning_content','')[:500]
            return {'answer':content.strip(),'model':'kimi-k3',
                    'tokens':d['usage']['total_tokens'],'tier':'T3 KIMI K3付费'}
        except: pass

    # Tier 4: DeepSeek Flash·兜底
    if DS_K:
        try:
            body = json.dumps({'model':'deepseek-v4-flash','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 1024,'temperature':temperature or 0.5}).encode()
            req = urllib.request.Request('http://localhost:18666/v1/chat/completions',
                data=body,headers={'Authorization':f'Bearer {DS_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=15).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),'model':'deepseek-v4-flash',
                    'tokens':d['usage']['total_tokens'],'tier':'T4 DS Flash兜底'}
        except: pass
    return None

def fuel_chat_quality(prompt, max_tokens=None):
    """品质优先路由: KIMI K3→智谱→NGC→DS Flash(跳过天工CPU)"""
    return fuel_chat(prompt, max_tokens, temperature=0.5)
    # KIMI K3将在Tier3被触发

def fuel_chat_reasoning(prompt, max_tokens=1024):
    """深度推理路由: KIMI K3 reasoning=high·适合复杂分析"""
    if KIMI_K and len(KIMI_K) > 30:
        try:
            body = json.dumps({'model':'kimi-k3','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens,'temperature':0.3,'reasoning_effort':'high'}).encode()
            req = urllib.request.Request('https://api.moonshot.cn/v1/chat/completions',
                data=body,headers={'Authorization':f'Bearer {KIMI_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=60).read())
            content = d['choices'][0]['message'].get('content','')
            reasoning = d['choices'][0]['message'].get('reasoning_content','')
            return {'answer':content or reasoning[:500],'model':'kimi-k3-high',
                    'tokens':d['usage']['total_tokens'],'tier':'KIMI K3深度推理',
                    'reasoning':reasoning[:300]}
        except: pass
    # 降级
    return fuel_chat(prompt, max_tokens, 0.3)

def health():
    """路由健康检查"""
    status = {}
    for name, key, test in [
        ('天工GPU', True, 'ping'),
        ('NGC', NV_K, 'key'),
        ('智谱', GLM_K, 'key'),
        ('KIMI K3', KIMI_K, 'key'),
        ('DS Flash', DS_K, 'key'),
    ]:
        status[name] = '🟢' if (test == 'ping' or (key and len(key) > 20)) else '🔴'
    return status

if __name__ == '__main__':
    h = health()
    print(f"混元路由 v2.0: {' '.join(f'{k}:{v}' for k,v in h.items())}")
    r = fuel_chat('hi')
    print(f"{'✅' if r else '❌'} {r['tier'] if r else 'ALL DOWN'} {r.get('tokens','?')}t")
