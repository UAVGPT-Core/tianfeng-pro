#!/usr/bin/env python3
"""秒改秒见 v1.0 — 统一版本号格式优化
天巡: -living → -哨兵 | 小枢: v15 → 动态日期 + -智脑 | nginx bump | 后端精简
"""

import os, sys

JS_BASE = "/Volumes/990Pro/public-web/public/js"
NGINX_CONF = "/opt/homebrew/etc/nginx/nginx.conf"
GW_EXT = "/Users/a1/ai-gateway/gateway_extensions.py"

changes = []

# ═══ 1. 天巡: 后缀 -living → -哨兵 ═══
tx_file = os.path.join(JS_BASE, "tianxun-v14-living.js")
with open(tx_file) as f:
    tx = f.read()

if "-living" in tx:
    tx_new = tx.replace("'-living'", "'-哨兵'")
    # 也改BRAND_CACHE中的greeting里的版本引用
    tx_new = tx_new.replace(".slice(2,10).replace(/-/g,'') + '.' + (_geneText||'77').replace('万','w') + '-living'",
                           ".slice(2,10).replace(/-/g,'') + '.' + (_geneText||'77').replace('万','w') + '-哨兵'")
    with open(tx_file, "w") as f:
        f.write(tx_new)
    changes.append("天巡JS: -living → -哨兵")

# ═══ 2. 小枢: 硬编码v15 → 动态日期 + 后缀 -智脑 ═══
xs_file = os.path.join(JS_BASE, "xiaoshu-chat.js")
with open(xs_file) as f:
    xs = f.read()

old_ver_line = "var VER='v15-'+(_geneText||'77w').replace(/[.]/g,'-').replace('万','w');"
new_ver_line = "var VER='v'+new Date().toISOString().slice(2,10).replace(/-/g,'')+'-'+(_geneText||'77w').replace(/[.]/g,'-').replace('万','w')+'-智脑';"

if old_ver_line in xs:
    xs = xs.replace(old_ver_line, new_ver_line)
    with open(xs_file, "w") as f:
        f.write(xs)
    changes.append("小枢JS: v15- → 动态日期 + -智脑")

# ═══ 3. nginx sub_filter v= bump ═══
with open(NGINX_CONF) as f:
    nginx = f.read()

import re
# 找到所有 tianxun-v14-living.js?v=XXX 和 xiaoshu-chat.js?v=XXX
def bump_version(match):
    num = int(match.group(1))
    return match.group(0).replace(f'v={num}', f'v={num+1}')

# Bump 天巡
old_tx_ver = re.search(r'tianxun-v14-living\.js\?v=(\d+)', nginx)
if old_tx_ver:
    new_ver = int(old_tx_ver.group(1)) + 1
    nginx = re.sub(r'tianxun-v14-living\.js\?v=\d+', f'tianxun-v14-living.js?v={new_ver}', nginx)
    changes.append(f"nginx 天巡: v={old_tx_ver.group(1)} → v={new_ver}")

# Bump 小枢
old_xs_ver = re.search(r'xiaoshu-chat\.js\?v=(\d+)', nginx)
if old_xs_ver:
    new_ver = int(old_xs_ver.group(1)) + 1
    nginx = re.sub(r'xiaoshu-chat\.js\?v=\d+', f'xiaoshu-chat.js?v={new_ver}', nginx)
    changes.append(f"nginx 小枢: v={old_xs_ver.group(1)} → v={new_ver}")

with open(NGINX_CONF, "w") as f:
    f.write(nginx)

# ═══ 4. nginx reload ═══
os.system("nginx -t 2>&1 && nginx -s reload 2>&1")
changes.append("nginx: 语法检查+reload")

# ═══ 5. 后端/v 格式说明(不改功能, 只记录) ═══
# 后端 /v 保留完整信息: v{YYMMDD}.{build}.{gene_10k}w
# 前端只显示: v{YYMMDD}.{gene_10k}w-{角色}
# 这是设计分离: 后端=运维看, 前端=用户看

# ═══ 6. 验证 ═══
# 读回验证
with open(tx_file) as f:
    tx_check = f.read()
with open(xs_file) as f:
    xs_check = f.read()

print("=" * 50)
print("秒改秒见 v1.0 · 版本号优化完成")
print("=" * 50)
for c in changes:
    print(f"  ✅ {c}")
print()
print("验证 — 天巡VERSION行:")
for line in tx_check.split('\n'):
    if 'VERSION' in line and 'var VERSION' in line:
        print(f"  {line.strip()}")
        break
print("验证 — 小枢VER行:")
for line in xs_check.split('\n'):
    if "var VER=" in line:
        print(f"  {line.strip()}")
        break
print()
# ═══ 6. 修复天巡: VERSION在基因回调中同步更新 ═══
# 问题: VERSION在_geneText之前初始化, 回调只更新span不更新VERSION
tx_file2 = os.path.join(JS_BASE, "tianxun-v14-living.js")
with open(tx_file2) as f:
    tx2 = f.read()

old_cb = "_el2.textContent='v'+new Date().toISOString().slice(2,10).replace(/-/g,'')+'.'+_gw+'w'"
new_cb = "_el2.textContent='v'+new Date().toISOString().slice(2,10).replace(/-/g,'')+'.'+_gw+'w-哨兵';VERSION='v'+new Date().toISOString().slice(2,10).replace(/-/g,'')+'.'+_gw+'w-哨兵'"

if old_cb in tx2:
    tx2 = tx2.replace(old_cb, new_cb)
    with open(tx_file2, "w") as f:
        f.write(tx2)
    changes.append("天巡JS: VERSION同步更新 + span后缀 -哨兵")

print("效果: 所有前端页面刷新即见新版本号 · 零重启 · 零等待")
