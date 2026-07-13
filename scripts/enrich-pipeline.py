#!/usr/bin/env python3
"""
LGOX 无人机供应商富化管线 v1.0
================================
功能: 
  1. 搜索引擎批量查官网
  2. 企查查API补齐工商信息(需API Key)
  3. 按分类生成触达邮件模板
  4. 输出Onyx可索引的Markdown文档
  5. 每年UASE展会后更新

用法:
  python3 enrich-pipeline.py input.csv output_dir/
  
环境变量:
  QICHACHA_API_KEY  企查查API Key (可选)
  QICHACHA_SECRET   企查查Secret (可选)
"""
import csv, json, os, sys, re, time, urllib.request, urllib.parse
from pathlib import Path

# ===== 搜索引擎查官网 =====
def search_website(name):
    """通过搜索引擎查找官网"""
    # 已知域名库 (手动维护)
    KNOWN = {
        "深圳智航无人机": "smdrone.com",
        "天鹰兄弟": "ty-uav.com",
        "迪飞无人机": "diflyuav.com",
        "银通无人机": "yintonguav.com",
    }
    for k, v in KNOWN.items():
        if k in name:
            return f"https://www.{v}"
    
    # 搜索引擎查询
    try:
        q = urllib.parse.quote(f"{name} 官方网站")
        req = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?q={q}",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)"}
        )
        r = urllib.request.urlopen(req, timeout=10)
        html = r.read().decode('utf-8', errors='ignore')
        
        # Extract first non-DDG URL
        urls = re.findall(r'uddg=([^"&]+)', html)
        for u in urls[:3]:
            u = urllib.parse.unquote(u)
            if u and not any(x in u.lower() for x in ['duckduckgo','baidu','google']):
                proto = 'https' if u.startswith('http') else 'https://'
                u = u if u.startswith('http') else proto + u
                return u.split('/')[0] + '/' if u.count('/') > 3 else u  # root domain
    except Exception as e:
        pass
    
    return ""

# ===== 企查查API (占位) =====
def qichacha_lookup(name):
    """通过企查查API查工商信息 (需API Key)"""
    api_key = os.environ.get('QICHACHA_API_KEY', '')
    if not api_key:
        return {"status": "skipped", "reason": "无API Key,请在环境变量设置QICHACHA_API_KEY"}
    
    # TODO: 对接企查查开放API
    # https://openapi.qcc.com/
    return {"status": "not_implemented"}

# ===== 生成触达邮件模板 =====
def generate_email(company, category, role):
    """按角色生成商务邮件模板"""
    templates = {
        "供应商": f"""主题: LGOX机巢项目-供应链合作询价
{company}负责人您好:

我们是LGOX(低空经济智能机巢方案商),现正扩充无人机零部件供应链。
贵司在UASE展会展示的{category}产品,与我们机巢项目需求匹配。

期待了解:
1. 产品规格书与报价
2. MOQ与交期
3. 是否支持定制

盼复。
LGOX采购部""",
        
        "合作伙伴": f"""主题: 低空经济合作探讨 - LGOX × {company}
{company}团队您好:

关注到贵司在UASE的{category}展示,我们在低空经济赛道(机巢/HABaaS)有深度布局。
建议探讨:
1. 技术互补: 贵司[飞行器/平台] + 我们[机巢/管控]
2. 渠道共享: 低空经济示范区联合拓展
3. 标准共建: 机巢-无人机对接标准

期待交流。
LGOX战略合作部""",
        
        "客户": f"""主题: 无人机自动机巢方案-为您降本增效
{company}负责人您好:

LGOX专注无人机自动机巢与HABaaS(蜂巢即服务)。
可帮贵司实现: 无人机自动起降/充电/数据回传,7×24无人值守。

附件: LGOX机巢产品手册
诚邀: 方案演示(线上30分钟)

LGOX销售部"""
    }
    
    cat_key = "客户"
    if "供应" in role or "部件" in role:
        cat_key = "供应商"
    elif "伙伴" in role or "合作" in role:
        cat_key = "合作伙伴"
    
    return templates.get(cat_key, templates["客户"])

# ===== 生成Onyx Markdown =====
def gen_onyx_md(rows, output_dir):
    """生成Onyx可索引的Markdown文档"""
    md_path = os.path.join(output_dir, "drone-suppliers-index.md")
    with open(md_path, 'w') as f:
        f.write("# 无人机供应商名录 (LGOX商业情报)\n\n")
        f.write(f"**来源**: china-drone.com.cn | **更新**: {time.strftime('%Y-%m-%d')} | **企业数**: {len(rows)}\n\n")
        f.write("---\n\n")
        
        cats = {}
        for r in rows:
            cat = r.get('分类', '其他')
            cats.setdefault(cat, []).append(r)
        
        for cat, items in cats.items():
            f.write(f"## {cat} ({len(items)}家)\n\n")
            for r in items[:50]:  # Top 50 per category
                f.write(f"- **{r['公司名']}** | {r.get('展馆','?')}馆{r.get('展位','')} | {r.get('省份','')} | {r.get('网站','') or '无官网'}\n")
            if len(items) > 50:
                f.write(f"- ... 等{len(items)-50}家\n")
            f.write("\n")
    
    print(f"📄 Onyx文档: {md_path}")
    return md_path

# ===== 主流程 =====
def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    
    input_csv = sys.argv[1]
    output_dir = sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)
    
    with open(input_csv) as f:
        rows = list(csv.DictReader(f))
    
    print(f"📊 加载 {len(rows)} 家企业")
    
    # Phase 1: 搜官网
    print("\n🔍 Phase 1: 搜索官网...")
    enriched = 0
    for r in rows:
        if not r.get('网站', '').strip():
            site = search_website(r['公司名'])
            if site:
                r['网站'] = site
                enriched += 1
                print(f"  ✅ {r['公司名'][:30]} → {site}")
            time.sleep(1)
    print(f"  新发现: {enriched} 个官网")
    
    # Phase 2: 企查查 (占位)
    print("\n📋 Phase 2: 企查查(需API Key,跳过)")
    
    # Phase 3: 生成邮件模板
    print("\n✉️ Phase 3: 生成触达邮件...")
    emails = []
    for r in rows[:20]:  # Top 20
        email = generate_email(r['公司名'], r.get('分类',''), r.get('分类',''))
        emails.append({"to": r['公司名'], "body": email})
    
    email_path = os.path.join(output_dir, "outreach-emails.json")
    with open(email_path, 'w') as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)
    print(f"  {len(emails)} 封邮件 → {email_path}")
    
    # Phase 4: Onyx文档
    print("\n📚 Phase 4: 生成Onyx索引文档...")
    gen_onyx_md(rows, output_dir)
    
    # Save enriched CSV
    out_csv = os.path.join(output_dir, "enriched.csv")
    with open(out_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(rows[0].keys())
        for r in rows:
            w.writerow(r.values())
    print(f"\n✅ 完成! 富化CSV: {out_csv}")

if __name__ == '__main__':
    main()
