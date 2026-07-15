"""VOD Pro通用客户端·免费·高质量·联邦共享"""
import urllib.request, json, os

def _get_key():
    for p in ["~/.hermes/.env", "~/lgox-ops/.env"]:
        try:
            with open(os.path.expanduser(p)) as f:
                for line in f:
                    if "BAIDU_VOD_KEY" in line:
                        return line.split("=",1)[1].strip().strip('"').strip("'")
        except: pass
    return ""

def vod_pro_chat(prompt, max_tokens=300, temperature=0.3):
    """VOD Pro调用·免费·高质量推理"""
    key = _get_key()
    data = json.dumps({
        "model": "deepseek-v4-pro",
        "messages": [{"role":"user","content":prompt}],
        "max_tokens": max_tokens, "temperature": temperature, "stream": False
    }).encode()
    req = urllib.request.Request(
        "https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions",
        data=data,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]

def vod_flash_chat(prompt, max_tokens=300, temperature=0.4):
    """VOD Flash调用·免费·快速"""
    key = _get_key()
    data = json.dumps({
        "model": "deepseek-v4-flash",
        "messages": [{"role":"user","content":prompt}],
        "max_tokens": max_tokens, "temperature": temperature, "stream": False
    }).encode()
    req = urllib.request.Request(
        "https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions",
        data=data,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]
