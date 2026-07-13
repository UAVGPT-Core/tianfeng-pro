#!/usr/bin/env python3
"""
LGOX联邦 信号多维富化引擎 v4.0
=================================
从纯技术面→多维融合:
  技术面(40%) + 基本面(25%) + 资金面(25%) + 情绪面(10%)

数据源: Tushare Pro (daily_basic + hsgt_top10 + top_list)
部署: 天枢 /Users/a1/stockagent-backend/v4_enricher.py
配额: 日耗≤2分 (daily_basic免费, hsgt_top10免费, top_list免费)

调用方式:
  from v4_enricher import enrich_signals
  enriched = enrich_signals(signals, trade_date="20260626")
"""

import os, json, logging, time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("v4_enricher")

# ═══════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════
WEIGHTS = {
    "technical": 0.40,    # 技术面(现有confidence)
    "fundamental": 0.25,  # 基本面(PE/PB/ROE)
    "capital": 0.25,      # 资金面(北向/主力)
    "sentiment": 0.10,    # 情绪面(龙虎榜/公告)
}

# 缓存: 同一天不重复查Tushare
_CACHE: Dict[str, dict] = {}
_CACHE_DATE: str = ""

# ═══════════════════════════════════════════════
# Tushare连接
# ═══════════════════════════════════════════════

def _get_pro():
    """懒加载Tushare Pro API"""
    import tushare as ts
    
    # 读token
    env_paths = [
        "/Users/a1/stockagent-backend/.env",
        os.path.expanduser("~/.tushare_token"),
    ]
    token = None
    for p in env_paths:
        try:
            with open(p) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line and "TUSHARE" in line.upper():
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            continue
        if token:
            break
    
    if not token:
        raise RuntimeError("Tushare token not found")
    
    ts.set_token(token)
    return ts.pro_api()

# ═══════════════════════════════════════════════
# 数据获取 (批量)
# ═══════════════════════════════════════════════

def _get_recent_trade_date(pro, max_tries: int = 3) -> str:
    """获取最近一个交易日"""
    today = datetime.now().strftime("%Y%m%d")
    for i in range(max_tries):
        dt = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        try:
            cal = pro.trade_cal(exchange="SSE", start_date=dt, end_date=dt)
            if len(cal) > 0 and cal.iloc[0]["is_open"] == 1:
                return dt
        except Exception as e:
            pass
    return today

def fetch_daily_basic_batch(ts_codes: List[str], trade_date: str = None) -> Dict[str, dict]:
    """
    批量获取基本面数据
    策略: 一次拉取全市场(daily_basic不支持多ts_code过滤),本地筛选
    返回: {ts_code: {pe, pb, roe, pe_ttm, total_mv, circ_mv, ...}}
    Tushare积分: 免费 (daily_basic)
    """
    global _CACHE, _CACHE_DATE
    
    cache_key = f"daily_basic_{trade_date}"
    if cache_key in _CACHE and _CACHE_DATE == trade_date:
        return _CACHE[cache_key]
    
    pro = _get_pro()
    if not trade_date:
        trade_date = _get_recent_trade_date(pro)
    
    code_set = set(ts_codes)
    result = {}
    
    try:
        # 一次拉全市场daily_basic(最大5000条,覆盖A股足够)
        df = pro.daily_basic(
            trade_date=trade_date,
            fields="ts_code,trade_date,pe,pb,roe,pe_ttm,pb_ttm,total_mv,circ_mv,revenue,profit"
        )
        
        if df is not None and len(df) > 0:
            for _, row in df.iterrows():
                code = str(row["ts_code"])
                if code in code_set:
                    result[code] = {
                        "pe": float(row.get("pe", 0) or 0),
                        "pb": float(row.get("pb", 0) or 0),
                        "roe": float(row.get("roe", 0) or 0),
                        "pe_ttm": float(row.get("pe_ttm", 0) or 0),
                        "pb_ttm": float(row.get("pb_ttm", 0) or 0),
                        "total_mv": float(row.get("total_mv", 0) or 0),
                        "circ_mv": float(row.get("circ_mv", 0) or 0),
                        "revenue": float(row.get("revenue", 0) or 0),
                        "profit": float(row.get("profit", 0) or 0),
                        "data_date": str(row.get("trade_date", "")),
                    }
        
        logger.info(f"daily_basic: {len(result)}/{len(ts_codes)} codes (from {len(df) if df is not None else 0} total)")
    except Exception as e:
        logger.warning(f"daily_basic batch failed: {e}")
    
    _CACHE[cache_key] = result
    _CACHE_DATE = trade_date
    return result

def fetch_northbound_top(trade_date: str = None) -> Dict[str, dict]:
    """
    获取北向资金十大成交
    返回: {ts_code: {net_amount, rank, buy, sell, market_type}}
    Tushare积分: 免费 (hsgt_top10)
    """
    global _CACHE, _CACHE_DATE
    
    cache_key = f"northbound_{trade_date}"
    if cache_key in _CACHE and _CACHE_DATE == trade_date:
        return _CACHE[cache_key]
    
    pro = _get_pro()
    if not trade_date:
        trade_date = _get_recent_trade_date(pro)
    
    result = {}
    
    for mkt_type, mkt_name in [("1", "沪股通"), ("2", "深股通")]:
        try:
            df = pro.hsgt_top10(trade_date=trade_date, market_type=mkt_type)
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    ts_code = row["ts_code"]
                    result[ts_code] = {
                        "net_amount": float(row.get("net_amount", 0) or 0),
                        "buy": float(row.get("buy", 0) or 0),
                        "sell": float(row.get("sell", 0) or 0),
                        "rank": int(row.get("rank", 99)),
                        "market_type": mkt_name,
                    }
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"hsgt_top10 {mkt_name} failed: {e}")
    
    logger.info(f"northbound top fetched: {len(result)} codes")
    _CACHE[cache_key] = result
    return result

def fetch_top_list(trade_date: str = None) -> Dict[str, dict]:
    """
    获取龙虎榜数据
    返回: {ts_code: {net_amount, l_buy, l_sell, reason, pct_change}}
    Tushare积分: 免费 (top_list)
    """
    global _CACHE, _CACHE_DATE
    
    cache_key = f"toplist_{trade_date}"
    if cache_key in _CACHE and _CACHE_DATE == trade_date:
        return _CACHE[cache_key]
    
    pro = _get_pro()
    if not trade_date:
        trade_date = _get_recent_trade_date(pro)
    
    result = {}
    
    try:
        df = pro.top_list(trade_date=trade_date)
        if df is not None and len(df) > 0:
            for _, row in df.iterrows():
                ts_code = row["ts_code"]
                result[ts_code] = {
                    "net_amount": float(row.get("net_amount", 0) or 0),
                    "l_buy": float(row.get("l_buy", 0) or 0),
                    "l_sell": float(row.get("l_sell", 0) or 0),
                    "reason": str(row.get("reason", "")),
                    "pct_change": float(row.get("pct_change", 0) or 0),
                }
        
        logger.info(f"top_list fetched: {len(result)} codes")
    except Exception as e:
        logger.warning(f"top_list failed: {e}")
    
    _CACHE[cache_key] = result
    return result

def fetch_fina_indicator_batch(ts_codes: List[str], trade_date: str = None) -> Dict[str, dict]:
    """
    获取财务指标(季度)
    返回: {ts_code: {roe_q, profit_growth, revenue_growth, debt_ratio, ...}}
    Tushare积分: ~0.3分/次(可降至5分/月)
    """
    global _CACHE, _CACHE_DATE
    
    cache_key = f"fina_{trade_date}"
    if cache_key in _CACHE and _CACHE_DATE == trade_date:
        return _CACHE[cache_key]
    
    pro = _get_pro()
    if not trade_date:
        trade_date = _get_recent_trade_date(pro)
    
    # 用最近季度的财报期
    # 简单策略: 取trade_date所在年份最新季度
    year = int(trade_date[:4])
    result = {}
    
    # 只取最近一期年报/季报的数据
    # 这可用最大500只查询
    try:
        for i in range(0, len(ts_codes), 400):
            batch = ts_codes[i:i+400]
            codes_str = ",".join(batch)
            # 尝试最新财年
            for end_date_guess in [f"{year}0331", f"{year-1}1231", f"{year-1}0930"]:
                try:
                    df = pro.fina_indicator(
                        ts_code=codes_str,
                        end_date=end_date_guess,
                        fields="ts_code,end_date,roe,roe_yearly,profit_dedt,growth_rate,or_yoy,debt_to_assets"
                    )
                    if df is not None and len(df) > 0:
                        break
                except Exception as e:
                    continue
            
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    code = row["ts_code"]
                    if code not in result:  # 只取第一个结果(最新)
                        result[code] = {
                            "roe_quarterly": float(row.get("roe", 0) or 0),
                            "profit_growth": float(row.get("profit_dedt", 0) or 0),
                            "revenue_growth": float(row.get("or_yoy", 0) or 0),
                            "debt_ratio": float(row.get("debt_to_assets", 0) or 0),
                            "report_date": str(row.get("end_date", "")),
                        }
            time.sleep(0.5)
        
        logger.info(f"fina_indicator fetched: {len(result)}/{len(ts_codes)} codes")
    except Exception as e:
        logger.warning(f"fina_indicator batch failed: {e}")
    
    _CACHE[cache_key] = result
    return result

# ═══════════════════════════════════════════════
# 评分引擎 (子维度 → 0-100)
# ═══════════════════════════════════════════════

def score_fundamental(basic: dict, fina: dict = None) -> Tuple[float, dict]:
    """
    基本面评分 0-100
    维度: PE合理性(0-40) + ROE质量(0-30) + 成长性(0-20) + PB安全边际(0-10)
    """
    detail = {}
    
    pe = basic.get("pe", 0)
    pb = basic.get("pb", 0)
    roe = basic.get("roe", 0)
    
    # 1. PE合理性 (0-40)
    if pe <= 0:
        pe_score = 0  # 亏损企业
    elif pe < 10:
        pe_score = 25  # 极低PE可能有陷阱
    elif pe <= 30:
        pe_score = 40  # 合理区间满分
    elif pe <= 50:
        pe_score = 30
    elif pe <= 80:
        pe_score = 15
    else:
        pe_score = 5
    detail["pe_score"] = pe_score
    
    # 2. ROE质量 (0-30)
    if roe <= 0:
        roe_score = 0
    elif roe < 5:
        roe_score = 10
    elif roe < 10:
        roe_score = 18
    elif roe < 15:
        roe_score = 24
    elif roe < 25:
        roe_score = 30  # 黄金区间15-25%
    else:
        roe_score = 22  # 过高可持续性存疑
    detail["roe_score"] = roe_score
    
    # 3. 成长性 (0-20)
    # 用fina数据(如果有)否则给基础分
    if fina:
        rev_growth = fina.get("revenue_growth", 0)
        profit_growth = fina.get("profit_growth", 0)
        growth_avg = (rev_growth + profit_growth) / 2
        if growth_avg > 30:
            growth_score = 20
        elif growth_avg > 20:
            growth_score = 18
        elif growth_avg > 10:
            growth_score = 15
        elif growth_avg > 0:
            growth_score = 10
        elif growth_avg > -10:
            growth_score = 5
        else:
            growth_score = 0
    else:
        growth_score = 10  # 无数据给中等分
    detail["growth_score"] = growth_score
    
    # 4. PB安全边际 (0-10)
    if pb <= 0:
        pb_score = 0
    elif pb < 1:
        pb_score = 10  # 破净，安全边际高
    elif pb < 2:
        pb_score = 8
    elif pb < 4:
        pb_score = 6
    elif pb < 8:
        pb_score = 3
    else:
        pb_score = 1
    detail["pb_score"] = pb_score
    
    total = pe_score + roe_score + growth_score + pb_score
    return total, detail

def score_capital(north: dict, basic: dict = None) -> Tuple[float, dict]:
    """
    资金面评分 0-100
    维度: 北向十大活跃(0-70) + 市值流动性(0-30)
    """
    detail = {}
    
    # 1. 北向十大活跃 (0-70)
    if north:
        net = north.get("net_amount", 0)
        rank = north.get("rank", 99)
        
        # 净买入评分
        if net > 5:
            net_score = 35  # 净买>5亿=强看多
        elif net > 2:
            net_score = 30
        elif net > 0.5:
            net_score = 25
        elif net > 0:
            net_score = 20
        elif net > -1:
            net_score = 15
        elif net > -3:
            net_score = 10
        else:
            net_score = 5   # 净卖>3亿=看空
        
        # 排名加分(越靠前越受关注)
        if rank <= 3:
            rank_score = 35
        elif rank <= 5:
            rank_score = 25
        elif rank <= 10:
            rank_score = 15
        else:
            rank_score = 5
        
        nb_score = min(70, net_score + rank_score)
    else:
        nb_score = 30  # 不在十大=中等关注度
    detail["northbound_score"] = nb_score
    
    # 2. 市值流动性 (0-30)
    if basic:
        circ_mv = basic.get("circ_mv", 0) or 0
        if circ_mv > 500:   # >500亿=大盘蓝筹
            liq_score = 30
        elif circ_mv > 100:
            liq_score = 25
        elif circ_mv > 50:
            liq_score = 20
        elif circ_mv > 20:
            liq_score = 15
        else:
            liq_score = 8  # 小盘股流动性风险
    else:
        liq_score = 15
    detail["liquidity_score"] = liq_score
    
    total = nb_score + liq_score
    return total, detail

def score_sentiment(top_list_data: dict) -> Tuple[float, dict]:
    """
    情绪面评分 0-100
    维度: 龙虎榜(0-80) + 公告情绪基础(0-20)
    """
    detail = {}
    
    if top_list_data:
        net = top_list_data.get("net_amount", 0) or 0
        l_buy = top_list_data.get("l_buy", 0) or 0
        l_sell = top_list_data.get("l_sell", 0) or 0
        reason = top_list_data.get("reason", "")
        
        # 净买入评分
        if net > 10000:      # >1亿
            net_score = 50
        elif net > 5000:
            net_score = 40
        elif net > 1000:
            net_score = 30
        elif net > 0:
            net_score = 20
        elif net > -1000:
            net_score = 15
        elif net > -5000:
            net_score = 10
        else:
            net_score = 5
        
        # 买入力量比
        if l_buy > 0 and l_sell > 0:
            buy_ratio = l_buy / (l_buy + l_sell)
            if buy_ratio > 0.7:
                buy_score = 30  # 主力猛买
            elif buy_ratio > 0.55:
                buy_score = 20
            elif buy_ratio > 0.5:
                buy_score = 10
            else:
                buy_score = 5
        else:
            buy_score = 10
        
        # 上榜原因额外加分
        reason_bonus = 0
        if "机构" in reason or "专用" in reason:
            reason_bonus = 10  # 机构专用席位
        elif "实力" in reason or "知名" in reason:
            reason_bonus = 5
        
        top_score = min(80, net_score + buy_score + reason_bonus)
    else:
        top_score = 35  # 未上榜=中性情绪
    detail["toplist_score"] = top_score
    
    # 公告情绪基础分 (0-20)
    detail["news_score"] = 10  # 默认中性，未来可接入NLP
    
    total = top_score + 10
    return total, detail

def compute_multi_dim_score(signal: dict, basic: dict, north: dict, 
                             toplist: dict, fina: dict = None) -> dict:
    """
    多维融合评分
    技术面(40%) + 基本面(25%) + 资金面(25%) + 情绪面(10%)
    """
    # 技术面 = 现有confidence (0-100)
    tech_score = signal.get("confidence", 50)
    
    # 基本面
    fund_score, fund_detail = score_fundamental(basic, fina)
    
    # 资金面
    cap_score, cap_detail = score_capital(north, basic)
    
    # 情绪面
    sent_score, sent_detail = score_sentiment(toplist)
    
    # 加权综合
    composite = (
        tech_score * WEIGHTS["technical"] +
        fund_score * WEIGHTS["fundamental"] +
        cap_score * WEIGHTS["capital"] +
        sent_score * WEIGHTS["sentiment"]
    )
    
    return {
        "composite_score": round(composite, 1),
        "technical": {
            "score": round(tech_score, 1),
            "weight": WEIGHTS["technical"],
            "label": "技术形态"
        },
        "fundamental": {
            "score": round(fund_score, 1),
            "weight": WEIGHTS["fundamental"],
            "label": "基本面",
            "detail": fund_detail,
            "pe": basic.get("pe"),
            "pb": basic.get("pb"),
            "roe": basic.get("roe"),
            "total_mv": basic.get("total_mv"),
        },
        "capital": {
            "score": round(cap_score, 1),
            "weight": WEIGHTS["capital"],
            "label": "资金面",
            "detail": cap_detail,
            "north_net": north.get("net_amount") if north else None,
            "north_rank": north.get("rank") if north else None,
        },
        "sentiment": {
            "score": round(sent_score, 1),
            "weight": WEIGHTS["sentiment"],
            "label": "情绪面",
            "detail": sent_detail,
            "toplist_net": toplist.get("net_amount") if toplist else None,
            "toplist_reason": toplist.get("reason") if toplist else None,
        },
    }

# ═══════════════════════════════════════════════
# 主入口: 批量富化
# ═══════════════════════════════════════════════

def enrich_signals(signals: List[dict], trade_date: str = None, 
                    use_fina: bool = False) -> List[dict]:
    """
    批量富化信号 → 多维融合评分
    signals: [{"ts_code":"600519.SH","name":"贵州茅台","confidence":85,...}, ...]
    use_fina: 是否查询财务指标(增加~0.5分Tushare消耗)
    
    返回: 原信号 + multi_dim 字段
    """
    if not signals:
        return signals
    
    # 收集所有ts_code
    ts_codes = list(set(s.get("ts_code", s.get("symbol", "")) for s in signals if s.get("ts_code") or s.get("symbol")))
    if not ts_codes:
        return signals
    
    logger.info(f"Enriching {len(signals)} signals × {len(ts_codes)} unique codes")
    
    # 批量获取数据
    basic_map = fetch_daily_basic_batch(ts_codes, trade_date)
    logger.info(f"  basic_map: {len(basic_map)} codes")
    
    north_map = fetch_northbound_top(trade_date)
    logger.info(f"  north_map: {len(north_map)} codes")
    
    top_map = fetch_top_list(trade_date)
    logger.info(f"  top_map: {len(top_map)} codes")
    
    fina_map = {}
    if use_fina:
        fina_map = fetch_fina_indicator_batch(ts_codes, trade_date)
        logger.info(f"  fina_map: {len(fina_map)} codes")
    
    # 为每个信号计算多维评分
    enriched_count = 0
    for signal in signals:
        ts_code = signal.get("ts_code", signal.get("symbol", ""))
        if not ts_code:
            continue
        
        basic = basic_map.get(ts_code, {})
        north = north_map.get(ts_code)
        toplist = top_map.get(ts_code)
        fina = fina_map.get(ts_code)
        
        multi = compute_multi_dim_score(signal, basic, north, toplist, fina)
        signal["multi_dim"] = multi
        signal["composite_score"] = multi["composite_score"]
        
        # 补充数据(前端展示用)
        if basic:
            signal["pe"] = basic.get("pe")
            signal["pb"] = basic.get("pb")
            signal["roe"] = basic.get("roe")
            signal["total_mv"] = basic.get("total_mv")
        if north:
            signal["north_net"] = north.get("net_amount")
            signal["north_rank"] = north.get("rank")
        if toplist:
            signal["toplist_net"] = toplist.get("net_amount")
            signal["toplist_reason"] = toplist.get("reason")
        
        enriched_count += 1
    
    # 按综合评分降序(先去重: 同一股票只保留最高分信号)
    seen_codes = set()
    deduped = []
    for s in sorted(signals, key=lambda x: x.get("composite_score", 0), reverse=True):
        code = s.get("ts_code", s.get("symbol", ""))
        if code not in seen_codes:
            seen_codes.add(code)
            deduped.append(s)
    signals = deduped
    
    logger.info(f"Enriched {enriched_count}/{len(signals)} signals. "
                f"Score range: {signals[0].get('composite_score',0):.0f} ~ {signals[-1].get('composite_score',0):.0f}")
    
    return signals

# ═══════════════════════════════════════════════
# 缓存管理
# ═══════════════════════════════════════════════

def clear_cache():
    """清除所有缓存"""
    global _CACHE, _CACHE_DATE
    _CACHE.clear()
    _CACHE_DATE = ""

# ═══════════════════════════════════════════════
# CLI: 独立测试
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    
    # 加载信号
    signal_file = sys.argv[1] if len(sys.argv) > 1 else "/Volumes/990Pro/public-web/signals-v2.json"
    
    with open(signal_file) as f:
        data = json.load(f)
    
    signals = data.get("signals", data if isinstance(data, list) else [])
    if isinstance(signals, dict):
        signals = list(signals.values()) if not isinstance(signals, list) else [signals]
    
    print(f"Loaded {len(signals)} signals")
    
    # 富化
    enriched = enrich_signals(signals)
    
    # 输出前10条看效果
    print("\n=== TOP 10 多维评分 ===")
    for i, s in enumerate(enriched[:10]):
        multi = s.get("multi_dim", {})
        print(f"{i+1}. {s.get('name','?')}({s.get('ts_code','?')}) "
              f"综合={multi.get('composite_score',0):.0f} "
              f"技术={multi.get('technical',{}).get('score',0):.0f} "
              f"基本={multi.get('fundamental',{}).get('score',0):.0f} "
              f"资金={multi.get('capital',{}).get('score',0):.0f} "
              f"情绪={multi.get('sentiment',{}).get('score',0):.0f}")
    
    # 保存富化结果
    out_file = signal_file.replace(".json", "-enriched.json")
    # 保留原有结构
    data["signals"] = enriched
    data["enriched"] = True
    data["enriched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["enricher_version"] = "v4.0"
    
    with open(out_file, "w") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
    
    print(f"\nEnriched output: {out_file}")
