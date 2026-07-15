/**
 * LGOX AI飞轮增强模块 v1.0
 * futures.html + signals.html 共享
 * 
 * 功能:
 *  ① 实时联邦状态栏(七自·基因·飞轮·互测)
 *  ② 小枢AI实时分析面板(调用:8779)
 *  ③ 基因反馈闭环(评分→LGE)
 *  ④ 互测飞轮数据面板
 * 
 * 加载: <script src="/public/js/ai-flywheel-v1.js"></script>
 */
(function(){
'use strict';

// ═══ 配置 ═══
const XIAOSHU_API = '/api/wind/../xiaoshu'; // nginx代理→:8779
const DASHBOARD = 'https://stock.uavgpt.com/dashboard.json';
const GENE_WRITE = '/api/gene/write'; // nginx代理→LGE

// ═══ 联邦状态栏 ═══
function initFedBar() {
  // 找到已有的xs-v15-bar或创建
  let bar = document.getElementById('xs-v15-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'xs-v15-bar';
    bar.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;' +
      'background:#0a0e1a;border-bottom:1px solid #1f6feb33;padding:4px 16px;' +
      'font-size:11px;color:#8b949e;display:flex;gap:16px;align-items:center;' +
      'font-family:Menlo,Monaco,monospace';
    document.body.prepend(bar);
  }
  
  function update() {
    fetch(DASHBOARD + '?t=' + Date.now())
      .then(r => r.json())
      .then(d => {
        const seven = Object.values(d.seven_self||{}).reduce((a,b)=>a+b,0) / Object.keys(d.seven_self||{}).length;
        const fw = Object.values(d.flywheels||{}).filter(Boolean).length;
        const fwTotal = Object.keys(d.flywheels||{}).length;
        const genes = d.genes?.total || '--';
        const mutTest = d.mutual_test || {};
        
        bar.innerHTML = 
          '<span>🦐 LGOX联邦</span>' +
          '<span style="color:' + (seven>=80?'#00ff88':'#ffd600') + '">七自' + Math.round(seven) + '%</span>' +
          '<span>' + genes + '基因</span>' +
          '<span>飞轮' + fw + '/' + fwTotal + '</span>' +
          (mutTest.rounds ? '<span style="color:#7c4dff">互测' + mutTest.rounds + '轮·均' + (mutTest.avg_score||0).toFixed(2) + '</span>' : '') +
          '<span style="color:#d29922">⚡VOD</span>';
      }).catch(()=>{});
  }
  update();
  setInterval(update, 60000);
}

// ═══ 小枢AI实时分析面板 ═══
function injectAIPanel(containerId, title, dataProvider, onFeedback) {
  let container = document.getElementById(containerId);
  if (!container) return;
  
  const panel = document.createElement('div');
  panel.className = 'ai-flywheel-panel';
  panel.style.cssText = 'background:#0a0e1a;border:1px solid #1f6feb44;border-radius:8px;' +
    'padding:14px;margin-top:12px;font-size:12px';
  panel.innerHTML = 
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">' +
    '<h4 style="margin:0;color:#79c0ff">🤖 ' + title + ' <span style="font-size:10px;color:#6e7681">小枢AI·实时</span></h4>' +
    '<button onclick="window._aiFlywheelAnalyze()" style="padding:4px 12px;background:#1f6feb;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:11px">🔄 AI分析</button>' +
    '</div>' +
    '<div id="' + containerId + '-ai-content" style="color:#c9d1d9;line-height:1.6;max-height:300px;overflow-y:auto">' +
    '<span style="color:#6e7681">点击「AI分析」让小枢解读当前数据</span></div>' +
    '<div id="' + containerId + '-ai-feedback" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid #30363d">' +
    '<span style="color:#8b949e;font-size:10px">这个分析有帮助吗？</span>' +
    '<button onclick="window._aiFlywheelRate(1)" style="margin-left:8px;padding:2px 10px;background:#23863622;color:#3fb950;border:1px solid #238636;border-radius:4px;cursor:pointer;font-size:10px">👍</button>' +
    '<button onclick="window._aiFlywheelRate(0)" style="margin-left:4px;padding:2px 10px;background:#da363322;color:#f85149;border:1px solid #da3633;border-radius:4px;cursor:pointer;font-size:10px">👎</button>' +
    '<span id="' + containerId + '-ai-rated" style="display:none;color:#3fb950;font-size:10px;margin-left:8px">✅ 已反馈·纳基因</span>' +
    '</div></div>';
  
  container.appendChild(panel);
  
  // 全局分析函数
  let lastQuestion = '';
  window._aiFlywheelAnalyze = async function() {
    const content = document.getElementById(containerId + '-ai-content');
    const feedback = document.getElementById(containerId + '-ai-feedback');
    content.innerHTML = '<span style="color:#d29922">⏳ 小枢分析中...</span>';
    
    try {
      const data = dataProvider();
      const q = '请简要分析以下市场数据的关键信号和风险:\n' + JSON.stringify(data).substring(0, 1500);
      lastQuestion = q;
      
      const r = await fetch('https://stock.uavgpt.com/api/xiaoshu/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({messages:[{role:'user',content:q}],max_tokens:300,stream:false})
      });
      
      if (!r.ok) throw new Error('API error');
      const d = await r.json();
      const answer = d.choices?.[0]?.message?.content || '分析暂时不可用';
      content.innerHTML = answer.replace(/\n/g, '<br>');
      feedback.style.display = 'block';
    } catch(e) {
      content.innerHTML = '<span style="color:#f85149">⚠️ AI分析暂时不可用: ' + e.message + '</span>';
    }
  };
  
  // 评分反馈
  window._aiFlywheelRate = async function(rating) {
    document.getElementById(containerId + '-ai-rated').style.display = 'inline';
    try {
      await fetch(GENE_WRITE, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          content: '[AI飞轮反馈·' + (rating?'👍':'👎') + '] 页面:' + containerId + ' 评分:' + rating,
          memory_type: 'episodic', source: 'ai-flywheel', fitness: rating ? 0.7 : 0.3
        })
      });
    } catch(e) { console.log('gene feedback err:', e); }
    if (onFeedback) onFeedback(rating);
  };
}

// ═══ 互测飞轮数据面板 ═══
function injectMutualTestPanel(containerId) {
  let container = document.getElementById(containerId);
  if (!container) return;
  
  const panel = document.createElement('div');
  panel.id = 'mutual-test-panel';
  panel.style.cssText = 'background:#0a0e1a;border:1px solid #7c4dff33;border-radius:8px;' +
    'padding:10px 14px;margin-top:8px;font-size:11px';
  panel.innerHTML = '<span style="color:#7c4dff">🔄 互测飞轮</span> <span style="color:#6e7681">加载中...</span>';
  
  container.appendChild(panel);
  
  function update() {
    fetch(DASHBOARD + '?t=' + Date.now())
      .then(r => r.json())
      .then(d => {
        const mt = d.mutual_test || {};
        if (mt.rounds) {
          panel.innerHTML = 
            '<span style="color:#7c4dff">🔄 互测飞轮</span> ' +
            '<span>今日' + mt.rounds + '轮</span> ' +
            '<span style="color:#3fb950">均' + (mt.avg_score||0).toFixed(2) + '分</span> ' +
            '<span>小枢' + (mt.xiaoshu_avg||0).toFixed(2) + '</span> ' +
            '<span>天巡' + (mt.tianxun_avg||0).toFixed(2) + '</span> ' +
            (mt.genes_today ? '<span style="color:#d29922">🧬+' + mt.genes_today + '</span>' : '');
        }
      }).catch(()=>{});
  }
  update();
  setInterval(update, 120000);
}

// ═══ 启动 ═══
document.addEventListener('DOMContentLoaded', function() {
  initFedBar();
  
  // 自动检测页面类型并注入对应面板
  if (document.querySelector('#price-grid')) {
    // futures.html
    injectAIPanel('flywheel-info', '期货行情AI解读', function() {
      const rows = document.querySelectorAll('#price-grid .row');
      const summary = [];
      rows.forEach(r => {
        const cells = r.querySelectorAll('div');
        if (cells.length >= 6) {
          summary.push({
            name: cells[1]?.textContent?.trim() || '',
            price: cells[2]?.textContent?.trim() || '',
            change: cells[3]?.textContent?.trim() || ''
          });
        }
      });
      return {type:'futures', count: summary.length, top: summary.slice(0,10)};
    });
  }
  
  if (document.querySelector('#tableContainer')) {
    // signals.html
    injectAIPanel('mockPanel', '信号AI深度解读', function() {
      const rows = document.querySelectorAll('#tableContainer table tr');
      const signals = [];
      rows.forEach(r => {
        const cells = r.querySelectorAll('td');
        if (cells.length >= 5) {
          signals.push({
            code: cells[2]?.textContent?.trim() || '',
            name: cells[3]?.textContent?.trim() || '',
            pattern: cells[4]?.textContent?.trim() || '',
            score: cells[5]?.textContent?.trim() || ''
          });
        }
      });
      return {type:'signals', count: signals.length, top: signals.slice(0,8)};
    });
    
    // 互测面板
    injectMutualTestPanel('mockPanel');
  }
});

})();
