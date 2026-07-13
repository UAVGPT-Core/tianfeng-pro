#!/usr/bin/env python3
"""pyramid.html v6.1 升级: 双大使+自洁+健康+桥+LOGOS"""
path = "/Volumes/990Pro/public-web/pyramid.html"
with open(path) as f:
    html = f.read()

# 1. 双大使+自洁+仪表盘 cards
html = html.replace(
    '<div class="card"><h3>🎮 自我对弈</h3>',
    '''<div class="card"><h3>🪶 天巡</h3><div class="value" id="a-tx-ver">...</div><div class="sub-val" id="a-tx-ss"></div></div>
  <div class="card"><h3>🧬 小枢</h3><div class="value" id="a-xs-ver">...</div><div class="sub-val" id="a-xs-ss"></div></div>
  <div class="card"><h3>🧹 自洁</h3><div class="value" id="sc-status">...</div><div class="sub-val" id="sc-next"></div></div>
  <div class="card"><h3>📊 仪表盘</h3><div class="value" id="db-conv">...</div><div class="sub-val">对话量</div></div>
  <div class="card"><h3>🎮 自我对弈</h3>''')

# 2. footer前加新分区
html = html.replace('<div class="footer">',
    '''<div class="section-title">🏥 联邦健康 · 无人值守</div><div id="fhealth" style="margin:10px 0"></div>
<div class="section-title">🪟 Widget Loader · 秒改秒见</div><div id="widget-info" style="margin:10px 0"></div>
<div class="section-title">📡 联邦桥</div><div id="bridge-info" style="margin:10px 0"></div>
<div class="section-title">📋 LOGOS智序</div><div id="logos-info" style="margin:5px 0"></div>
<div class="footer">''')

# 3. JS中添加新数据渲染
html = html.replace(
    "  var dl=d.distillation||{};",
    '''  // === 双大使 ===
  var am=d.ambassadors||{},tx=am["天巡"]||{},xs=am["小枢"]||{};
  document.getElementById("a-tx-ver").textContent=tx.version||"...";
  document.getElementById("a-tx-ss").textContent=tx.seven_self||"...";
  document.getElementById("a-xs-ver").textContent=xs.version||"...";
  document.getElementById("a-xs-ss").textContent=xs.seven_self||"...";

  // === 自洁 ===
  var sc=d.self_clean||{};
  document.getElementById("sc-status").textContent=sc.active?"🟢运转":"🔴停";
  document.getElementById("sc-next").textContent=(sc.schedule||"")+"·"+(sc.mode||"");

  // === 仪表盘 ===
  var db=d.dashboard||{};
  document.getElementById("db-conv").textContent=(db.conversations||0).toLocaleString();

  // === 健康 ===
  var h=d.health||{},hd=document.getElementById("fhealth");hd.innerHTML="";
  var hi=[["disksleep","磁盘休眠"],["auto_update","自动更新"],["tcc_fda","TCC全盘访问"],["hermes_allowlist","Hermes白名单"]];
  hi.forEach(function(i){var v=h[i[0]];hd.innerHTML+='<span class=tag'+(v?' tag-up':'')+'>'+(v?'🟢':'🔴')+' '+i[1]+'</span> ';});
  if(h.disk_free_gb)hd.innerHTML+='<span class=tag tag-up>💾 '+h.disk_free_gb+'GB可用('+h.disk_pct+'%)</span>';

  // === Widget Loader ===
  var wl=d.widget_loader||{},wd=document.getElementById("widget-info");
  wd.innerHTML=wl.active?'<span class=tag tag-up>🟢 运行中·nginx:'+(wl.nginx_lines||"22->1")+'</span>':'<span class=tag>🔴 未激活</span>';
  var wp=wl.pages_configured||{};
  for(var k in wp)wd.innerHTML+='<span class=tag tag-up>📄 '+k+':'+wp[k]+'</span> ';

  // === 桥 ===
  var br=d.bridges||{},bd=document.getElementById("bridge-info");bd.innerHTML="";
  for(var k in br){var v=br[k];if(typeof v=="boolean")bd.innerHTML+='<span class=tag'+(v?' tag-up':'')+'>'+(v?'🟢':'🔴')+' '+k+'</span> ';}
  if(br["消息积压"])bd.innerHTML+='<span class=tag>📨 积压:'+br["消息积压"]+'条</span>';

  // === LOGOS ===
  var lg=d.logos_score||0,ld=document.getElementById("logos-info");
  ld.innerHTML='<span class=tag tag-up>⭐ LOGOS:'+lg+'/100</span> <span class=tag tag-up>👤 人类参与度:'+(d.human_participation||"0%")+'</span> <span class=tag tag-up>🔀 择优路由</span>';

  var dl=d.distillation||{};''')

with open(path, "w") as f:
    f.write(html)
print("pyramid.html v6.1 updated")
