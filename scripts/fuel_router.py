#!/usr/bin/env python3
"""LGOX联邦NGC燃料路由器 v3.0 · NGC为主·免费121模型·全飞轮接管"""
import json, os, urllib.request

def _key(prefix):
    k = os.environ.get(prefix) or os.environ.get(prefix+'_KEY') or os.environ.get(prefix+'_API_KEY')
    if k: return k
    for f in [os.path.expanduser('~/.hermes/.env'), os.path.expanduser('~/lgox-ops/.env')]:
        if os.path.exists(f):
            for line in open(f):
                if prefix in line: return line.split('=',1)[1].strip().strip('"').strip("'")
    return ''

# ═══ NGC为主·免费Inception会员·121模型 ═══
NGC_K  = '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'
NGC_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
NGC_MODEL = 'meta/llama-3.1-8b-instruct'      # 主力量产
NGC_NEMOTRON = 'nvidia/llama-3.1-nemotron-nano-8b-v1'  # 质量评审

GLM_K  = 'fd867a96bad64f53a8ece13ac6911887.T3zYiYf7KbxhVTb0'  # 降级备路
KIMI_K = _key('KIMI_API') or 'sk-XmG...bYuf'
DS_K   = _key('DEEPSEEK_API')

def ngc_chat(prompt, model=None, max_tokens=256, temperature=0.3):
    """NGC API调用"""
    body = json.dumps({
        'model': model or NGC_MODEL,
        'messages': [{'role':'user','content':prompt}],
        'max_tokens': max_tokens, 'temperature': temperature
    }).encode()
    req = urllib.request.Request(NGC_URL, data=body,
        headers={'Authorization':f'Bearer {NGC_K}','Content-Type':'application/json'})
    d = json.loads(urllib.request.urlopen(req, timeout=20).read())
    return d['choices'][0]['message']['content'].strip(), d['usage']['total_tokens']

def fuel_chat(prompt, max_tokens=None, temperature=None):
    """NGC主路·三级降级: NGC→智谱→DS Flash"""
    
    # T0: NGC API·免费·主力
    try:
        content, tokens = ngc_chat(prompt, NGC_MODEL, max_tokens or 256, temperature or 0.3)
        return {'answer':content, 'model':'llama3.1-8b@NGC','tokens':tokens,'tier':'T0 NGC免费'}
    except: pass

    # T1: 智谱GLM-4-Flash·降级
    if GLM_K:
        try:
            body = json.dumps({'model':'glm-4-flash','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 256,'temperature':temperature or 0.3}).encode()
            req = urllib.request.Request('https://open.bigmodel.cn/api/paas/v4/chat/completions',
                data=body,headers={'Authorization':f'Bearer {GLM_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=12).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),'model':'glm-4-flash',
                    'tokens':d['usage']['total_tokens'],'tier':'T1智谱降级'}
        except: pass

    # T2: DS Flash·兜底
    if DS_K:
        try:
            body = json.dumps({'model':'deepseek-v4-flash','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 1024,'temperature':temperature or 0.5}).encode()
            req = urllib.request.Request('http://localhost:18666/v1/chat/completions',
                data=body,headers={'Authorization':f'Bearer {DS_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=15).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),'model':'ds-v4-flash',
                    'tokens':d['usage']['total_tokens'],'tier':'T2 DS兜底'}
        except: pass
    return None

def fuel_chat_quality(prompt, max_tokens=None):
    """品质路由: NGC nemotron评审 → KIMI K3备选"""
    try:
        content, tokens = ngc_chat(prompt, NGC_NEMOTRON, max_tokens or 512, 0.3)
        return {'answer':content,'model':'nemotron@NGC品质','tokens':tokens,'tier':'NGC品质'}
    except:
        pass
    # KIMI K3降级
    if KIMI_K and len(KIMI_K) > 30:
        try:
            body = json.dumps({'model':'kimi-k3','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 512,'temperature':0.3,'reasoning_effort':'low'}).encode()
            req = urllib.request.Request('https://api.moonshot.cn/v1/chat/completions',
                data=body,headers={'Authorization':f'Bearer {KIMI_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=30).read())
            content = d['choices'][0]['message'].get('content','') or \
                      d['choices'][0]['message'].get('reasoning_content','')[:500]
            return {'answer':content,'model':'kimi-k3','tokens':d['usage']['total_tokens'],'tier':'KIMI K3品质降级'}
        except: pass
    return fuel_chat(prompt, max_tokens)

def fuel_chat_reasoning(prompt, max_tokens=1024):
    """深度推理: KIMI K3 → NGC nemotron"""
    if KIMI_K and len(KIMI_K) > 30:
        try:
            body = json.dumps({'model':'kimi-k3','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens,'reasoning_effort':'high'}).encode()
            req = urllib.request.Request('https://api.moonshot.cn/v1/chat/completions',
                data=body,headers={'Authorization':f'Bearer {KIMI_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=60).read())
            content = d['choices'][0]['message'].get('content','')
            reasoning = d['choices'][0]['message'].get('reasoning_content','')
            return {'answer':content or reasoning[:500],'model':'kimi-k3-reasoning',
                    'tokens':d['usage']['total_tokens'],'tier':'KIMI K3推理',
                    'reasoning':reasoning[:300]}
        except: pass
    return fuel_chat_quality(prompt, max_tokens)

def health():
    """NGC路由健康"""
    s = {}
    try:
        ngc_chat('hi', NGC_MODEL, 5, 0)
        s['NGC'] = '🟢'
    except: s['NGC'] = '🔴'
    s['智谱'] = '🟢' if GLM_K else '🔴'
    s['KIMI'] = '🟢' if (KIMI_K and len(KIMI_K)>30) else '🔴'
    s['DS'] = '🟢' if DS_K else '🔴'
    return s

if __name__ == '__main__':
    h = health()
    print(f"NGC路由 v3.0: {' '.join(f'{k}:{v}' for k,v in h.items())}")
    r = fuel_chat('hi')
    print(f"{'✅' if r else '❌'} {r['tier']} | {r['model']} | {r['tokens']}t")
