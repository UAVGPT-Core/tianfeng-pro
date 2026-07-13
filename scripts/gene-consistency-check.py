#!/usr/bin/env python3
"""
小枢Widget基因数一致性检查 v1.0
LGE/API/页面/JS版本 — 四位一体校验
自动修复: nginx footer初始基因数、JS版本号、重启慢服务
"""
import urllib.request, json, re, ssl, subprocess, sys, os
from datetime import datetime

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'LGOX-GeneCheck/1.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode(errors='replace'), r.status
    except Exception as e:
        return None, str(e)

def fmt_gene(n):
    """格式化基因数: 715328 → 71.5万"""
    return f"{n/10000:.1f}万"

# ═══ Phase 1: 数据采集 ═══
print("=" * 60)
print(f"🧬 基因一致性检查 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

issues = []
fixes_applied = []

# 1. LGE ground truth
print("\n[1/5] LGE 基因引擎...")
lge_raw, lge_status = fetch("http://100.116.0.29:8200/health")
if lge_raw:
    lge = json.loads(lge_raw)
    gene_total = lge.get('genes', 0)
    gene_active = lge.get('active', 0)
    gene_formatted = fmt_gene(gene_total)
    print(f"  ✅ LGE: {gene_total:,} 基因 ({gene_formatted}), 活跃 {gene_active:,}")
else:
    print(f"  ❌ LGE连接失败: {lge_status}")
    sys.exit(1)

# 2. Page API
print("\n[2/5] Page API...")
api_raw, api_status = fetch("https://stock.uavgpt.com/api/stats/genes")
api_match = True
if api_raw:
    try:
        api = json.loads(api_raw)
        api_genes = api.get('genes', 0)
        api_formatted = api.get('formatted', '?')
        print(f"  {'✅' if api_genes == gene_total else '⚠️'} API: {api_genes:,} genes, formatted={api_formatted}")
        if api_genes != gene_total:
            issues.append(f"API基因数不一致: LGE={gene_total}, API={api_genes}")
            api_match = False
    except Exception as e:
        print(f"  ⚠️ API解析失败")
        issues.append("API返回非JSON")
else:
    print(f"  ❌ API连接失败: {api_status}")
    issues.append(f"API不可达: {api_status}")

# 3. Page HTML footer
print("\n[3/5] 页面HTML Footer...")
html_raw, html_status = fetch("https://stock.uavgpt.com")
if html_raw:
    # Check initial footer value
    footer_gene = re.findall(r'gene-count-live[^>]*>([^<]+)<', html_raw)
    footer_values = list(set(footer_gene))
    print(f"  Footer初始值: {footer_values}")
    
    # Check data-gene-target
    target_genes = re.findall(r'data-gene-target="full"[^>]*>\s*([^<]+)\s*<', html_raw)
    print(f"  data-gene-target=full: {list(set(target_genes))}")
    
    expected_footer = f"{fmt_gene(gene_total)}+"
    for fv in footer_values:
        if fv != expected_footer and fv != fmt_gene(gene_total):
            issues.append(f"Footer初始基因数:{fv} ≠ LGE:{expected_footer}")
else:
    print(f"  ❌ 页面不可达: {html_status}")
    issues.append(f"页面不可达: {html_status}")

# 4. xiaoshu JS
print("\n[4/5] 小枢 xiaoshu JS...")
xs_raw, xs_status = fetch("https://stock.uavgpt.com/public/public/js/xiaoshu-chat.js?v=100")
if xs_raw:
    xs_ver = re.search(r"var\s+VER\s*=\s*'([^']*)'", xs_raw)
    xs_gene = re.search(r"_geneText\s*=\s*'([^']*)'", xs_raw)
    xs_ver_val = xs_ver.group(1) if xs_ver else 'N/A'
    xs_gene_val = xs_gene.group(1) if xs_gene else 'N/A'
    print(f"  VER={xs_ver_val}")
    print(f"  _geneText={xs_gene_val}")
    
    expected_gene = f"{fmt_gene(gene_total)}+"
    if xs_gene_val != expected_gene:
        issues.append(f"xiaoshu _geneText:{xs_gene_val} ≠ LGE:{expected_gene}")
else:
    print(f"  ❌ xiaoshu JS不可达: {xs_status}")
    issues.append(f"xiaoshu JS不可达: {xs_status}")

# 5. tianxun JS
print("\n[5/5] 天巡 tianxun JS...")
tx_raw, tx_status = fetch("https://stock.uavgpt.com/public/public/js/tianxun-v14-living.js?v=14")
if tx_raw:
    tx_ver = re.search(r"var\s+VERSION\s*=\s*'([^']*)'", tx_raw)
    tx_gene = re.search(r"_geneText\s*=\s*'([^']*)'", tx_raw)
    tx_ver_val = tx_ver.group(1) if tx_ver else 'N/A'
    tx_gene_val = tx_gene.group(1) if tx_gene else 'N/A'
    print(f"  VERSION={tx_ver_val}")
    print(f"  _geneText={tx_gene_val}")
    
    expected_gene_no_plus = fmt_gene(gene_total)
    if tx_gene_val != expected_gene_no_plus:
        issues.append(f"tianxun _geneText:{tx_gene_val} ≠ LGE:{expected_gene_no_plus}")
else:
    # Try v13
    tx_raw, tx_status = fetch("https://stock.uavgpt.com/public/public/js/tianxun-v13-living.js?v=13")
    if tx_raw:
        tx_gene = re.search(r"_geneText\s*=\s*'([^']*)'", tx_raw)
        print(f"  (v13) _geneText={tx_gene.group(1) if tx_gene else 'N/A'}")
    else:
        print(f"  ❌ 天巡JS不可达(v14={tx_status})")
        issues.append("天巡JS不可达")

# ═══ Phase 2: 自动修复 ═══
print("\n" + "=" * 60)
print("🔧 自动修复阶段")
print("=" * 60)

TIANSHU = "a1@100.100.89.2"
NGINX_CONF = "/opt/homebrew/etc/nginx/nginx.conf"
JS_DIR = "/Volumes/990Pro/public-web/public/js"

if issues:
    print(f"\n发现 {len(issues)} 个问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    new_footer_gene = f"{fmt_gene(gene_total)}+"
    new_gene_no_plus = fmt_gene(gene_total)
    today_ver = datetime.now().strftime("%y%m%d")
    
    # Fix 1: nginx footer gene count
    if any('Footer' in i for i in issues):
        print(f"\n🔧 修复nginx footer → {new_footer_gene}")
        # Replace any X.X万+ in sub_filter footer lines with correct value
        sed_ngx = "sed -i '' 's/[0-9]\\+\\.[0-9]万+/" + new_footer_gene.replace('+', '\\\\+') + "/g' " + NGINX_CONF
        result = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=5', TIANSHU, sed_ngx + " && echo OK"],
            capture_output=True, text=True, timeout=15
        )
        if 'OK' in result.stdout:
            fixes_applied.append(f"✅ nginx footer → {new_footer_gene}")
            print(f"  ✅ nginx footer已更新")
        else:
            print(f"  ❌ nginx footer更新失败: {result.stderr[:200]}")
    
    # Fix 2: xiaoshu-chat.js (follow symlink to real file)
    if any('xiaoshu' in i for i in issues):
        xs_file = JS_DIR + "/xiaoshu-chat.js"
        print(f"\n🔧 修复xiaoshu _geneText → {new_footer_gene}")
        # Use sed to replace _geneText='XX万+' with correct value
        sed_xs = "sed -i '' \"s/_geneText='[0-9.]*万[+]*'/_geneText='" + new_footer_gene.replace('+', '\\\\+') + "'/\" " + xs_file
        result = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=5', TIANSHU, sed_xs + " && echo OK"],
            capture_output=True, text=True, timeout=15
        )
        if 'OK' in result.stdout:
            fixes_applied.append(f"✅ xiaoshu _geneText → {new_footer_gene}")
            print(f"  ✅ xiaoshu-chat.js已更新")
        else:
            # Fallback: get real path from symlink
            result2 = subprocess.run(
                ['ssh', '-o', 'ConnectTimeout=5', TIANSHU,
                 "REAL=$(readlink -f " + xs_file + " 2>/dev/null || readlink " + xs_file + "); " + sed_xs.replace(xs_file, "$REAL") + " && echo OK"],
                capture_output=True, text=True, timeout=15
            )
            if 'OK' in result2.stdout:
                fixes_applied.append(f"✅ xiaoshu _geneText → {new_footer_gene}")
                print(f"  ✅ xiaoshu已更新(通过symlink目标)")
            else:
                print(f"  ❌ xiaoshu更新失败: {result2.stderr[:200]}")
    
    # Fix 3: tianxun JS
    if any('tianxun' in i for i in issues):
        tx_file = JS_DIR + "/tianxun-v14-living.js"
        print(f"\n🔧 修复tianxun _geneText → {new_gene_no_plus}")
        # Build sed commands without f-string backslash issues
        sed1 = "sed -i '' \"s/_geneText = '[0-9.]*万'/_geneText = '" + new_gene_no_plus + "'/g\" " + tx_file
        sed2 = "sed -i '' \"s/_geneText||'[0-9.]*万+'/_geneText||'" + new_footer_gene + "'/g\" " + tx_file
        result = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=5', TIANSHU,
             sed1 + " && " + sed2 + " && echo OK"],
            capture_output=True, text=True, timeout=15
        )
        if 'OK' in result.stdout:
            fixes_applied.append(f"✅ tianxun _geneText → {new_gene_no_plus}")
            print(f"  ✅ tianxun-v14-living.js已更新")
        else:
            print(f"  ❌ tianxun更新失败: {result.stderr[:200]}")
    
    # Fix 4: Reload nginx
    print(f"\n🔧 重启nginx...")
    result = subprocess.run(
        ['ssh', '-o', 'ConnectTimeout=5', TIANSHU,
         'sudo /opt/homebrew/bin/nginx -t && sudo /opt/homebrew/bin/nginx -s reload && echo RELOADED'],
        capture_output=True, text=True, timeout=15
    )
    if 'RELOADED' in result.stdout or 'successful' in result.stdout.lower():
        fixes_applied.append("✅ nginx已重载")
        print(f"  ✅ nginx重载成功")
    else:
        # Try without sudo
        result2 = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=5', TIANSHU,
             '/opt/homebrew/bin/nginx -t 2>&1 && /opt/homebrew/bin/nginx -s reload 2>&1 && echo RELOADED'],
            capture_output=True, text=True, timeout=15
        )
        if 'RELOADED' in result2.stdout:
            fixes_applied.append("✅ nginx已重载")
            print(f"  ✅ nginx重载成功")
        else:
            print(f"  ⚠️ nginx重载输出: {result.stdout[:200]}{result.stderr[:200]}")
    
    # Fix 5: Clear Cloudflare cache hint
    print(f"\n💡 Cloudflare缓存提示: 基因数footer有60秒JS自动更新，CF缓存自动过期。")
    
else:
    print("\n✅ 无问题，所有基因数一致！")

# ═══ Phase 3: 验证 ═══
print("\n" + "=" * 60)
print("🔍 修复后验证")
print("=" * 60)

# Re-check HTML footer
html2_raw, _ = fetch("https://stock.uavgpt.com")
if html2_raw:
    footer2 = re.findall(r'gene-count-live[^>]*>([^<]+)<', html2_raw)
    print(f"  Footer: {list(set(footer2))}")

# Re-check API
api2_raw, _ = fetch("https://stock.uavgpt.com/api/stats/genes")
if api2_raw:
    try:
        api2 = json.loads(api2_raw)
        print(f"  API: genes={api2.get('genes')}, formatted={api2.get('formatted')}")
    except Exception as e:
        pass

# ═══ 报告 ═══
print("\n" + "=" * 60)
print("📊 最终报告")
print("=" * 60)
print(f"  LGE基因总数: {gene_total:,} ({gene_formatted})")
print(f"  LGE活跃基因: {gene_active:,}")
print(f"  发现问题数: {len(issues)}")
print(f"  应用修复数: {len(fixes_applied)}")
if fixes_applied:
    for fix in fixes_applied:
        print(f"    {fix}")
print(f"  检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
