#!/bin/bash
# ============================================================
# LGOX AI飞轮部署脚本 v1.0
# 将优化的futures.html和signals.html部署到天枢990Pro
# 
# 用法: 在天枢Mac Studio上运行此脚本
#   bash /path/to/deploy-ai-flywheel.sh
# ============================================================
set -e

WEBROOT="/Volumes/990Pro/public-web"
JS_DIR="$WEBROOT/public/js"
NGINX_CONF="/opt/homebrew/etc/nginx/servers/stock.uavgpt.com.conf"

echo "🦐 LGOX AI飞轮部署 v1.0"
echo "========================="

# 1. 部署AI飞轮JS模块
echo ""
echo "① 部署 ai-flywheel-v1.js ..."
mkdir -p "$JS_DIR"
cat > "$JS_DIR/ai-flywheel-v1.js" << 'JSEOF'
/**
 * LGOX AI飞轮增强 v1.0 — futures.html + signals.html 共享
 * ① 联邦状态栏 ② 小枢AI分析 ③ 基因反馈 ④ 互测数据
 */
(function(){
'use strict';
const XIAOSHU_CHAT = '/api/xiaoshu/chat';
const DASHBOARD = '/dashboard.json';
const GENE_WRITE = '/api/gene/write';

// ═══ 联邦状态栏 ═══
function initFedBar(){
  let bar = document.getElementById('xs-v15-bar');
  if(!bar){
    bar = document.createElement('div'); bar.id = 'xs-v15-bar';
    bar.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;background:#0a0e1a;border-bottom:1px solid #1f6feb33;padding:4px 16px;font-size:11px;color:#8b949e;display:flex;gap:18px;align-items:center;font-family:Menlo,Monaco,monospace;flex-wrap:wrap';
    document.body.prepend(bar);
  }
  function upd(){
    fetch(DASHBOARD+'?t='+Date.now()).then(r=>r.json()).then(d=>{
      var sv=Object.values(d.seven_self||{}), sa=sv.reduce(function(a,b){return a+b},0)/sv.length;
      var fw=Object.values(d.flywheels||{}).filter(Boolean).length, ft=Object.keys(d.flywheels||{}).length;
      var mt=d.mutual_test||{};
      bar.innerHTML=
        '<b style="color:#e2b04a">🦐 LGOX</b>'+
        '<span style="color:'+(sa>=80?'#00ff88':'#ffd600')+'">七自'+Math.round(sa)+'%</span>'+
        '<span>'+(d.genes?.total||'--')+'基因</span>'+
        '<span>飞轮'+fw+'/'+ft+'</span>'+
        (mt.rounds?'<span style="color:#7c4dff">互测'+mt.rounds+'轮·均'+(mt.avg_score||0).toFixed(2)+'</span>':'')+
        '<span style="color:#d29922;margin-left:auto">⚡VOD·免费</span>';
    }).catch(function(){});
  }
  upd(); setInterval(upd,60000);
}

// ═══ 小枢AI实时分析面板 ═══
function injectAI(containerId, title, getData){
  var c = document.getElementById(containerId); if(!c) return;
  var p = document.createElement('div');
  p.style.cssText = 'background:#0a0e1a;border:1px solid #1f6feb44;border-radius:10px;padding:16px;margin:16px 0;font-size:13px';
  p.innerHTML = 
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'+
    '<h3 style="margin:0;color:#79c0ff;font-size:15px">🤖 '+title+'</h3>'+
    '<button id="ai-analyze-btn" style="padding:8px 18px;background:linear-gradient(135deg,#1f6feb,#7c4dff);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🔄 AI实时分析</button>'+
    '</div>'+
    '<div id="ai-content" style="color:#c9d1d9;line-height:1.8;min-height:60px;max-height:400px;overflow-y:auto;font-size:13px">'+
    '<span style="color:#6e7681">👆 点击按钮让小枢解读当前市场数据</span></div>'+
    '<div id="ai-feedback" style="display:none;margin-top:12px;padding-top:10px;border-top:1px solid #30363d;font-size:11px">'+
    '<span style="color:#8b949e">分析质量如何？</span> '+
    '<button onclick="window._rateAI(1)" style="padding:3px 12px;background:#23863622;color:#3fb950;border:1px solid #238636;border-radius:4px;cursor:pointer">👍 有用</button> '+
    '<button onclick="window._rateAI(0)" style="padding:3px 12px;background:#da363322;color:#f85149;border:1px solid #da3633;border-radius:4px;cursor:pointer">👎 不行</button> '+
    '<span id="ai-rated" style="display:none;color:#3fb950;margin-left:8px">✅ 已反馈·纳基因</span>'+
    '</div>';
  c.appendChild(p);

  var lastQ = '';
  document.getElementById('ai-analyze-btn').onclick = async function(){
    var ct = document.getElementById('ai-content');
    ct.innerHTML = '<span style="color:#d29922">⏳ 小枢分析中...（约2秒）</span>';
    try{
      var data = getData();
      lastQ = '请简要分析以下市场数据的关键信号、风险和机会（用中文·200字内）:\n'+JSON.stringify(data).substring(0,1500);
      var r = await fetch(XIAOSHU_CHAT,{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({messages:[{role:'user',content:lastQ}],max_tokens:300,stream:false})});
      var d = await r.json();
      ct.innerHTML = (d.choices?.[0]?.message?.content||'分析不可用').replace(/\n/g,'<br>');
      document.getElementById('ai-feedback').style.display = 'block';
    }catch(e){
      ct.innerHTML = '<span style="color:#f85149">⚠️ AI分析不可用: '+e.message+'</span>';
    }
  };

  window._rateAI = async function(rating){
    document.getElementById('ai-rated').style.display = 'inline';
    try{
      await fetch(GENE_WRITE,{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({content:'[AI飞轮反馈] 页面:'+containerId+' 评分:'+rating+' Q:'+lastQ.substring(0,200),
        memory_type:'episodic',source:'ai-flywheel',fitness:rating?0.65:0.2})});
    }catch(e){}
  };
}

// ═══ 互测飞轮面板 ═══
function injectMutualTest(containerId){
  var c = document.getElementById(containerId); if(!c) return;
  var p = document.createElement('div');
  p.id = 'mutual-test-bar';
  p.style.cssText = 'background:#0a0e1a;border:1px solid #7c4dff22;border-radius:8px;padding:8px 14px;margin-top:8px;font-size:11px;color:#8b949e';
  p.innerHTML = '<span style="color:#7c4dff">🔄 互测飞轮:</span> 加载中...';
  c.appendChild(p);
  function upd(){
    fetch(DASHBOARD+'?t='+Date.now()).then(r=>r.json()).then(d=>{
      var mt=d.mutual_test||{};
      if(mt.rounds){
        p.innerHTML = '<span style="color:#7c4dff">🔄 互测飞轮:</span> '+
          '今日<b style="color:#c9d1d9">'+mt.rounds+'</b>轮 '+
          '均<b style="color:#3fb950">'+(mt.avg_score||0).toFixed(2)+'</b>分 '+
          '小枢<b style="color:#58a6ff">'+(mt.xiaoshu_avg||0).toFixed(2)+'</b> '+
          '天巡<b style="color:#79c0ff">'+(mt.tianxun_avg||0).toFixed(2)+'</b> '+
          (mt.genes_today?'🧬<b style="color:#d29922">+'+mt.genes_today+'</b>':'');
      }
    }).catch(function(){});
  }
  upd(); setInterval(upd,120000);
}

// ═══ 启动 ═══
document.addEventListener('DOMContentLoaded',function(){
  initFedBar();

  // futures.html: 期货行情AI解读
  if(document.getElementById('price-grid')){
    injectAI('flywheel-info','期货行情·小枢AI实时解读',function(){
      var rows=document.querySelectorAll('#price-grid .row'),s=[];
      rows.forEach(function(r){var cs=r.querySelectorAll('div');if(cs.length>=6)s.push({name:(cs[1]?.textContent||'').trim(),price:(cs[2]?.textContent||'').trim(),change:(cs[3]?.textContent||'').trim()})});
      return {page:'futures',count:s.length,samples:s.slice(0,10)};
    });
  }

  // signals.html: 信号AI解读 + 互测面板
  if(document.getElementById('tableContainer')){
    injectAI('mockPanel','股票信号·小枢AI深度解读',function(){
      var rows=document.querySelectorAll('#tableContainer table tr'),s=[];
      rows.forEach(function(r){var cs=r.querySelectorAll('td');if(cs.length>=6)s.push({code:(cs[2]?.textContent||'').trim(),name:(cs[3]?.textContent||'').trim(),pattern:(cs[4]?.textContent||'').trim(),score:(cs[5]?.textContent||'').trim()})});
      return {page:'signals',count:s.length,top8:s.slice(0,8)};
    });
    injectMutualTest('mockPanel');
  }
});

})();
JSEOF
echo "   ✅ JS已部署: $JS_DIR/ai-flywheel-v1.js"

# 2. 注入到futures.html
echo ""
echo "② 注入 futures.html ..."
FUTURES="$WEBROOT/futures.html"
if [ -f "$FUTURES" ]; then
  if ! grep -q "ai-flywheel-v1.js" "$FUTURES"; then
    # 在</body>前注入脚本引用
    sed -i '' 's|</body>|<script src="/public/js/ai-flywheel-v1.js"></script>\n</body>|' "$FUTURES"
    echo "   ✅ futures.html 已注入"
  else
    echo "   ℹ️ futures.html 已有飞轮引用，跳过"
  fi
else
  echo "   ❌ futures.html 不存在: $FUTURES"
fi

# 3. 注入到signals.html
echo ""
echo "③ 注入 signals.html ..."
SIGNALS="$WEBROOT/signals.html"
if [ -f "$SIGNALS" ]; then
  if ! grep -q "ai-flywheel-v1.js" "$SIGNALS"; then
    sed -i '' 's|</body>|<script src="/public/js/ai-flywheel-v1.js"></script>\n</body>|' "$SIGNALS"
    echo "   ✅ signals.html 已注入"
  else
    echo "   ℹ️ signals.html 已有飞轮引用，跳过"
  fi
else
  echo "   ❌ signals.html 不存在: $SIGNALS"
fi

# 4. nginx代理: /api/xiaoshu/chat → localhost:8779
echo ""
echo "④ 配置 nginx 小枢API代理 ..."
if [ -f "$NGINX_CONF" ]; then
  if ! grep -q "api/xiaoshu/chat" "$NGINX_CONF"; then
    # 在server块内添加location
    sed -i '' '/server {/a\
    # LGOX AI飞轮: 小枢API代理\
    location /api/xiaoshu/chat {\
        proxy_pass http://127.0.0.1:8779/chat/completions;\
        proxy_set_header Host \$host;\
        proxy_set_header X-Real-IP \$remote_addr;\
        proxy_read_timeout 30s;\
    }\
    location /api/gene/write {\
        proxy_pass http://100.116.0.29:8200/genes/write;\
        proxy_set_header Host \$host;\
        proxy_read_timeout 10s;\
    }\
' "$NGINX_CONF"
    echo "   ✅ nginx代理已添加"
    echo "   ⚠️ 需要reload: brew services restart nginx"
  else
    echo "   ℹ️ nginx已有代理配置"
  fi
else
  echo "   ❌ nginx配置不存在: $NGINX_CONF"
fi

echo ""
echo "═══════════════════════════════════════"
echo "  部署完成！"
echo "═══════════════════════════════════════"
echo ""
echo "下一步:"
echo "  1. nginx -t && brew services restart nginx"
echo "  2. 浏览器强刷 futures.html + signals.html (Cmd+Shift+R)"
echo "  3. 确认顶部出现🦐LGOX联邦状态栏"
echo "  4. 点击「AI实时分析」测试小枢解读"
