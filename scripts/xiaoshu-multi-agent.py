#!/usr/bin/env python3
# 小枢·多Agent对抗分析引擎 v1.0
# AI Berkshire模式: 4个大师视角并行分析 → Team Lead综合 → 强制结论
# 接入小枢信号分析管线
# 调用: POST {"symbol":"600519","stock_name":"贵州茅台"}

import json, os, sys, urllib.request, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 百度VOD
VOD = "https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions"
VOD_KEY = "BAIDU_VOD_KEY_REDACTED"

LGE = "http://100.116.0.29:8200"

def llm(prompt, system="", mt=512):
    ms = [{"role":"system","content":system},{"role":"user","content":prompt}] if system else [{"role":"user","content":prompt}]
    for _ in range(2):
        try:
            r = urllib.request.urlopen(urllib.request.Request(VOD,
                data=json.dumps({"model":"deepseek-v4-flash","messages":ms,"max_tokens":mt,"temperature":0.3}).encode(),
                headers={"Content-Type":"application/json","Authorization":"Bearer "+VOD_KEY}), timeout=30)
            c = json.loads(r.read()).get("choices",[{}])[0].get("message",{}).get("content","")
            if c: return c
        except: time.sleep(2)
    return None

# 四位大师的系统prompt
MASTERS = {
    "段永平": {
        "focus": "商业模式+护城河",
        "system": "你是段永平(步步高创始人·价值投资者)。你关注:①这生意好不好懂?②护城河深不深?③企业文化好不好?④价格合不合理?打分1-5,必须给最终建议:买/观望/不买。简洁犀利,不打太极。"
    },
    "巴菲特": {
        "focus": "财务估值+安全边际",
        "system": "你是巴菲特。你关注:①ROE是否长期>15%?②自由现金流是否充沛?③负债是否可控?④是否有持续竞争优势?⑤当前价格有无安全边际?打分1-5,输出具体目标价区间。"
    },
    "芒格": {
        "focus": "逆向思维+风险",
        "system": "你是查理·芒格。你关注:①投资前先想'什么情况下会死'?②有什么我看不到的风险?③市场共识可能错在哪?④逆向检查清单。打分1-5,必须输出风险警告。"
    },
    "李录": {
        "focus": "10年确定性",
        "system": "你是李录(喜马拉雅资本)。你关注:①10年后这公司还在不在?②管理层诚信和能力?③增长天花板在哪?④文化基因能否传承?打分1-5,只说'确定'或'不确定'。"
    }
}

def master_analyze(master_name, config, symbol, stock_name):
    """单个大师分析"""
    prompt = f"请从{config['focus']}角度分析{stock_name}({symbol})。当前时间2026年7月。给出评分(1-5)和具体建议。"
    resp = llm(prompt, config["system"], 512)
    if not resp: return {"master": master_name, "score": 0, "conclusion": "分析失败", "detail": ""}
    
    # 提取评分
    score = 0
    for line in resp.split("\n"):
        for s in range(1,6):
            if f"{s}/5" in line or f"{s}.0/5" in line or f"评分:{s}" in line or f"分数:{s}" in line:
                score = max(score, s)
    if score == 0: score = 3  # 默认中值
    
    # 提取建议
    conclusion = "观望"
    if any(k in resp for k in ["不买","不投","回避","卖出","不建议","风险大"]): conclusion = "不买"
    elif any(k in resp for k in ["买","买入","建仓","推荐","建议买入"]): conclusion = "买"
    
    return {"master": master_name, "score": score, "conclusion": conclusion, "detail": resp[:300]}

def team_lead_summarize(results, symbol, stock_name):
    """Team Lead综合四位大师观点"""
    scores = {r["master"]: r["score"] for r in results}
    conclusions = {r["master"]: r["conclusion"] for r in results}
    avg = sum(scores.values()) / len(scores) if scores else 0
    
    # 综合判断
    buys = sum(1 for c in conclusions.values() if c == "买")
    sells = sum(1 for c in conclusions.values() if c == "不买")
    
    if buys >= 3: final = "推荐买入"
    elif sells >= 3: final = "不建议"
    elif sells >= buys: final = "观望(风险项多于积极项)"
    else: final = "谨慎关注"
    
    # 价格区间
    price_prompt = f"综合四位大师观点:有{buys}位建议买,{sells}位不建议。给出{stock_name}({symbol})的:①激进型买入区间 ②稳健型买入区间 ③10字以内结论"
    price_resp = llm(price_prompt, "你是一个投研总结助手。简洁输出。", 256)
    
    summary = {
        "symbol": symbol,
        "stock_name": stock_name,
        "final_conclusion": final,
        "composite_score": round(avg, 1),
        "masters": results,
        "detail": conclusions,
        "price_advice": price_resp or "",
        "timestamp": datetime.now().isoformat(),
        "source": "xiaoshu-multi-agent"
    }
    return summary

def analyze(symbol="", stock_name=""):
    """入口: 多Agent对抗分析"""
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        fs = {ex.submit(master_analyze, name, cfg, symbol, stock_name): name for name, cfg in MASTERS.items()}
        for f in as_completed(fs):
            try:
                r = f.result(timeout=90)
                results.append(r)
                print(f"  {r['master']}: {r['score']}/5 → {r['conclusion']}")
            except Exception as e:
                print(f"  {fs[f]}: 超时")
                results.append({"master": fs[f], "score": 0, "conclusion": "超时", "detail": ""})
    
    summary = team_lead_summarize(results, symbol, stock_name)
    
    # 写入LGE
    try:
        urllib.request.urlopen(urllib.request.Request(LGE+"/genes/write",
            data=json.dumps({"content":json.dumps(summary,ensure_ascii=False),"memory_type":"episodic",
                "source":"xiaoshu-multi-agent","tags":["stock","analysis","multi-agent",symbol]}).encode(),
            headers={"Content-Type":"application/json"}), timeout=10)
    except: pass
    
    return summary

if __name__ == "__main__":
    # 测试
    s = sys.argv[1] if len(sys.argv) > 1 else "600519"
    n = sys.argv[2] if len(sys.argv) > 2 else "茅台"
    r = analyze(s, n)
    print(f"\n{'='*40}")
    print(f"📊 {n}({s}) 综合评分: {r['composite_score']}/5")
    print(f"结论: {r['final_conclusion']}")
    print(f"价格建议: {r['price_advice']}")
    print(f"{'='*40}")
