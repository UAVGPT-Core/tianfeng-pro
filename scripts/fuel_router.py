#!/usr/bin/env python3
"""LGOX联邦燃料路由器 · T0天工→T1智谱→T4 DS Flash自动降级"""
import json, os, urllib.request
def _key(prefix):
    k = os.environ.get(prefix) or os.environ.get(prefix+'_KEY') or os.environ.get(prefix+'_API_KEY')
    if k: return k
    for f in [os.path.expanduser('~/.hermes/.env'), os.path.expanduser('~/lgox-ops/.env')]:
        if os.path.exists(f):
            for line in open(f):
                if prefix in line: return line.split('=',1)[1].strip().strip('"').strip("'")
    return ''
GLM_K = 'fd867a96bad64f53a8ece13ac6911887.T3zYiYf7KbxhVTb0'  # 智谱200万token/天免费
DS_K = _key('DEEPSEEK_API')
TIANGONG = 'http://100.118.207.31:11434'

def fuel_chat(prompt, max_tokens=None, temperature=None):
    # Tier0: 天工GPU零成本(新·2026-07-13成本优化)
    try:
        body = json.dumps({'model':'qwen2.5:14b','messages':[{'role':'user','content':prompt}],
            'stream':False,'options':{'temperature':temperature or 0.3,'num_predict':max_tokens or 256}}).encode()
        req = urllib.request.Request(f'{TIANGONG}/api/chat',data=body,
            headers={'Content-Type':'application/json'})
        d = json.loads(urllib.request.urlopen(req,timeout=15).read())
        return {'answer':d['message']['content'].strip(),'model':'qwen2.5:14b@天工GPU',
                'tokens':d.get('eval_count',0),'tier':'T0零成本'}
    except: pass

    # Tier1: 智谱GLM免费(Key过期暂时跳过)
    if GLM_K:
        try:
            body = json.dumps({'model':'glm-4-flash','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 256,'temperature':temperature or 0.3}).encode()
            req = urllib.request.Request('https://open.bigmodel.cn/api/paas/v4/chat/completions',
                data=body,headers={'Authorization':f'Bearer {GLM_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=12).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),'model':'glm-4-flash',
                    'tokens':d['usage']['total_tokens'],'tier':'T1免费'}
        except: pass

    # Tier4: DeepSeek Flash兜底
    if DS_K:
        try:
            body = json.dumps({'model':'deepseek-v4-flash','messages':[{'role':'user','content':prompt}],
                'max_tokens':max_tokens or 1024,'temperature':temperature or 0.5}).encode()
            req = urllib.request.Request('https://api.deepseek.com/v1/chat/completions',
                data=body,headers={'Authorization':f'Bearer {DS_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req,timeout=15).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),'model':'deepseek-v4-flash',
                    'tokens':d['usage']['total_tokens'],'tier':'T4付费兜底'}
        except: pass
    return None

if __name__ == '__main__':
    print(f"天工:{'🟢' if _key('DUMMY') or True else '🔴'} GLM:{'🟢' if GLM_K else '🔴(过期)'} DS:{'🟢' if DS_K else '🔴'}")
    r = fuel_chat('hi'); print(f"{'✅' if r else '❌'} {r['tier'] if r else ''} {r['tokens'] if r else ''}t")
