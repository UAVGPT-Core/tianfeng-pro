#!/usr/bin/env python3
"""nginx去根 v2: 简单字符串替换,不拆block"""
import re, shutil, subprocess

nginx_conf = "/opt/homebrew/etc/nginx/nginx.conf"

# Backup
bak = nginx_conf + ".bak-v2-" + __import__("datetime").datetime.now().strftime("%H%M%S")
shutil.copy2(nginx_conf, bak)
print(f"备份: {bak}")

with open(nginx_conf) as f:
    nginx = f.read()

# Count before
before_count = len(re.findall(r"tianxun-v14-living|xioshu-chat", nginx))
print(f"替换前引用数: {before_count}")

# Replace 1: tianxun-v14-living.js → widget-loader.js  
nginx = re.sub(
    r'tianxun-v14-living\.js\?v=\d+',
    'widget-loader.js?v=1',
    nginx
)

# Replace 2: Remove xiaoshu-chat.js script tags from sub_filter lines
# Pattern: <script src="...xiaoshu-chat.js?v=NUMBER"></script>
nginx = re.sub(
    r'<script src="https://stock\.uavgpt\.com/public/public/js/xiaoshu-chat\.js\?v=\d+"></script>',
    '',
    nginx
)

after_count = len(re.findall(r"tianxun-v14-living|xioshu-chat", nginx))
print(f"替换后引用数: {after_count}")
print(f"widget-loader引用数: {len(re.findall(r'widget-loader', nginx))}")

with open(nginx_conf, "w") as f:
    f.write(nginx)

# Test
r = subprocess.run(["/opt/homebrew/bin/nginx", "-t"], capture_output=True, text=True)
if "syntax is ok" in r.stderr or r.returncode == 0:
    print("✅ nginx -t OK")
    r2 = subprocess.run(["sudo", "/opt/homebrew/bin/nginx", "-s", "reload"], capture_output=True, text=True)
    print("✅ nginx reloaded")
else:
    print(f"❌ nginx -t FAILED:\n{r.stderr[:300]}")
    print("Restoring backup...")
    shutil.copy2(bak, nginx_conf)
    subprocess.run(["sudo", "/opt/homebrew/bin/nginx", "-s", "reload"])
    print("Backup restored")
