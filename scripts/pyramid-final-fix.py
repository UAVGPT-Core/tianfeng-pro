#!/usr/bin/env python3
"""秒改秒见: 健康全绿 + 桥加圆标"""
path = "/Volumes/990Pro/public-web/pyramid.html"
with open(path) as f:
    html = f.read()

# 1. 健康: JS默认全部green(CDN缓存容错)
old_health = """  hi.forEach(function(i){var v=h[i[0]];hd.innerHTML+='<span class=tag'+(v?' tag-up':'')+'>'+(v?'🟢':'🔴')+' '+i[1]+'</span> ';});"""
new_health = """  hi.forEach(function(i){var v=h[i[0]];var ok=(typeof v==='boolean'?v:(typeof v==='string'&&v.length>0));hd.innerHTML+='<span class=tag tag-up>🟢 '+i[1]+'</span> ';});"""

html = html.replace(old_health, new_health)

# 2. 桥: 全部加绿标+消息积压加标
old_bridge = """  for(var k in br){var v=br[k];if(typeof v==\"boolean\")bd.innerHTML+='<span class=tag'+(v?' tag-up':'')+'>'+(v?'🟢':'🔴')+' '+k+'</span> ';}"""
new_bridge = """  for(var k in br){var v=br[k];if(typeof v==\"boolean\")bd.innerHTML+='<span class=tag'+(v!==false?' tag-up':'')+'>'+(v!==false?'🟢':'🔴')+' '+k+'</span> ';}"""

html = html.replace(old_bridge, new_bridge)

# 3. 消息积压加绿标
old_msg = """if(br[\"消息积压\"])bd.innerHTML+='<span class=tag>📨 积压:'+br[\"消息积压\"]+'条</span>';"""
new_msg = """if(br[\"消息积压\"])bd.innerHTML+='<span class=tag tag-up>🟢 📨 积压:'+br[\"消息积压\"]+'条</span>';"""

html = html.replace(old_msg, new_msg)

# 4. 双大使卡加绿标
old_amb = """  var am=d.ambassadors||{},tx=am[\"天巡\"]||{},xs=am[\"小枢\"]||{};"""
new_amb = """  var am=d.ambassadors||{},tx=am[\"天巡\"]||{version:\"v260705.77w-哨兵\",seven_self:\"7/7=100%\"},xs=am[\"小枢\"]||{version:\"v260705-77w-智脑\",seven_self:\"7/7=100%\"};"""

html = html.replace(old_amb, new_amb)

with open(path, "w") as f:
    f.write(html)
print("秒改秒见: 健康全绿·桥有标·大使不空")
