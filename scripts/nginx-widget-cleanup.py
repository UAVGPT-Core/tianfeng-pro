#!/usr/bin/env python3
"""nginx去根: 22条widget sub_filter → 1条widget-loader + forestry只天巡"""
import re, shutil, os

nginx_conf = "/opt/homebrew/etc/nginx/nginx.conf"
forestry_html = "/Volumes/990Pro/public-web/forestry.html"

# ═══ Step 1: forestry.html → 只天巡 ═══
with open(forestry_html) as f:
    fh = f.read()
fh = fh.replace('<body>', '<body data-lgox-widget="tianxun">')
with open(forestry_html, "w") as f:
    f.write(fh)
print("✅ forestry.html: body → data-lgox-widget=tianxun")

# ═══ Step 2: nginx备份 ═══
bak = nginx_conf + ".bak-widget-cleanup-" + __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(nginx_conf, bak)
print(f"✅ nginx备份: {bak}")

# ═══ Step 3: nginx去根 ═══
with open(nginx_conf) as f:
    nginx = f.read()

# Widget loader injection (one line to rule them all)
loader_inject = "sub_filter '</body>' '<script src=\"https://stock.uavgpt.com/public/public/js/widget-loader.js?v=1\"></script></body>';"

# Remove ALL lines that inject tianxun or xiaoshu widgets
# These lines contain sub_filter and reference the widget JS files
lines = nginx.split('\n')
new_lines = []
removed = 0

for line in lines:
    stripped = line.strip()
    # Keep: non-widget sub_filter lines (footer bars, etc.)
    # Remove: lines that inject tianxun-v14-living.js or xiaoshu-chat.js 
    if 'sub_filter' in stripped and ('tianxun-v14-living' in stripped or 'xiaoshu-chat.js' in stripped or 'xiaoshu-v' in stripped):
        removed += 1
        continue
    # Also handle the escaped versions
    if 'sub_filter' in stripped and ('tianxun-v14-living' in stripped or 'xiaoshu-chat' in stripped):
        removed += 1
        continue
    new_lines.append(line)

nginx = '\n'.join(new_lines)
print(f"✅ 移除了 {removed} 条widget sub_filter")

# Insert ONE widget-loader in the first server block sub_filter section
# Find the first sub_filter line in a server block and add our loader after it
# Actually, find the first '</body>' sub_filter in each server block
# There are likely 3 server blocks. Insert at the end of each.

# Simpler: add the loader line after the first sub_filter '</body>' occurrence
# Find pattern: sub_filter '</body>' '...existing stuff...</body>';
# Replace with: sub_filter '</body>' '<script...loader...></script>...existing...</body>';
# 
# Actually, let's find lines that already inject sub_filter for '</body>'
# and insert our loader. If there are none left, add to each server block.

# Find server blocks
server_blocks = re.finditer(r'server\s*\{', nginx)
server_positions = [m.start() for m in server_blocks]

# For each server block, find the right place to add the loader
# Best approach: add after the 'location' block that handles the main site
# Or just append to the end of each server block before the closing '}'

# Even simpler: insert the loader injection before the closing '}' of each server block
# But we need to be careful about nginx syntax

# Let's use a different approach: find sub_filter lines that inject footer bars
# (these are our markers) and add the loader nearby

# Actually the simplest: inject loader as the LAST sub_filter in each server block
# Find sub_filter lines, and after the last one in each server block, add our loader

# Let me just insert it in each server block before the closing brace
# by finding '}' at start of line preceded by a sub_filter block

# Most reliable: add loader right after the existing sub_filter lines
# in each block. Find any sub_filter, add loader after it.

# Actually, let me just inject after the first sub_filter in each server block
modified = 0
result_lines = []
in_server = False
last_sub_filter_idx = -1

for i, line in enumerate(nginx.split('\n')):
    result_lines.append(line)
    if re.match(r'\s*server\s*\{', line):
        in_server = True
    if in_server and re.match(r'\s*\}', line) and i > 0:
        # End of server block - inject loader if not already there
        in_server = False
    if 'sub_filter' in line and "'</body>'" in line:
        # Found a sub_filter that injects into </body> - this is a good spot
        # Only add once per block
        pass

# Simpler approach: just prepend the loader to the first sub_filter '</body>' line 
# in each block, or add at the end of the main sub_filter section

# Let me just find the right location to add the loader
# Look for the line just before the closing brace of server blocks that have sub_filter

# THE SIMPLEST: Find lines with 'sub_filter' and '</body>', 
# add our loader BEFORE the first such line in each server block
blocks = nginx.split('}\n')
new_blocks = []
for block in blocks:
    if 'sub_filter' in block and "'</body>'" in block:
        # This block has sub_filter - add our loader
        # Find the first sub_filter line
        blines = block.split('\n')
        injected = False
        new_blines = []
        for bline in blines:
            if not injected and 'sub_filter' in bline and "'</body>'" in bline:
                new_blines.append('            ' + loader_inject)
                injected = True
            new_blines.append(bline)
        if injected:
            modified += 1
            new_blocks.append('\n'.join(new_blines))
        else:
            new_blocks.append(block)
    else:
        new_blocks.append(block)

nginx = '}\n'.join(new_blocks)
print(f"✅ 注入了 {modified} 个server块的widget-loader")

with open(nginx_conf, "w") as f:
    f.write(nginx)

# ═══ Step 4: nginx语法检查 ═══
import subprocess
r = subprocess.run(["/opt/homebrew/bin/nginx", "-t"], capture_output=True, text=True)
if r.returncode == 0:
    print("✅ nginx -t: OK")
    # Reload
    r2 = subprocess.run(["sudo", "/opt/homebrew/bin/nginx", "-s", "reload"], capture_output=True, text=True)
    if "OK" in r2.stderr + r2.stdout or r2.returncode == 0:
        print("✅ nginx reload OK")
    else:
        print(f"⚠️ reload output: {r2.stderr[:100]}")
else:
    print(f"❌ nginx -t FAILED:\n{r.stderr[:500]}")
    print("恢复备份...")
    shutil.copy2(bak, nginx_conf)
    subprocess.run(["sudo", "/opt/homebrew/bin/nginx", "-s", "reload"])
    print("已恢复")
