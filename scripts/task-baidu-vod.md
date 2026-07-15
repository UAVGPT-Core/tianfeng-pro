# 百度智能点播VOD·榨干任务书

## 背景
百度云有两个VOD：
1. 千帆VOD(Virtual Online DeepSeek) — 已榨干 ✅ deepseek-v4-pro/flash 免费
2. 智能点播VOD(Video on Demand) — 视频生产平台 🔒 待开通

智能点播VOD能力：AI视频生成、智能集锦、字幕擦除、视频翻译、媒资管理、CDN加速、工作流模板。

## 任务目标
开通百度智能点播VOD → 获取AK/SK → 灵龙接入 → 融入天影视频管线 → 纳基因

## 执行步骤

### Step 1: 开通VOD服务
1. 浏览器打开 https://console.bce.baidu.com/
2. 登录你的百度云账号(已有千帆DeepSeek的同一个账号)
3. 左上角「产品」→ 搜索「智能点播」或「VOD」或「视频点播」
4. 点「立即开通」/「免费试用」
5. 如果找不到入口，试试这些替代路径：
   - https://cloud.baidu.com/product/vod.html → 点「立即使用」
   - https://console.bce.baidu.com/vod
   - 控制台→产品→视频服务→智能点播

### Step 2: 获取密钥
1. 控制台右上角头像 → 安全认证 → Access Key管理
2. 创建AccessKey(已有则直接复制)
3. 记录:
   - AccessKey (AK): 20位左右字母数字
   - SecretKey (SK): 40位左右

### Step 3: 写密钥到.env
```bash
cat >> ~/.hermes/.env << 'EOF'
BAIDU_AK=你的AccessKey
BAIDU_SK=你的SecretKey
EOF

# 同步到灵龙
scp ~/.hermes/.env a112233@192.168.1.64:~/.hermes/.env
```

### Step 4: 验证API连通
在灵龙执行：
```bash
# 灵龙会自动探测可用API并汇报
python3 ~/lgox-ops/scripts/vod_pro_client.py --explore
```

## 如果VOD产品线已变更
如果控制台搜不到VOD，查这些替代产品：
- 音视频直播 LSS
- 媒体处理 MCP  
- 智能多媒体
- 看看控制台有哪些视频相关产品，截图告诉我

## 已知信息
- 千帆Bearer Key: bce-v3/ALTAK-RGaz...(已在~/.hermes/.env的BAIDU_VOD_KEY)
- 千帆Key只能调DeepSeek，视频API需要AK/SK签名认证
- 视频API端点存在(返回400非404/401)，说明网关层通，后端缺AK/SK
- LGOX天影管线已有: FFmpeg+HyperFrames+OpenMontage+VideoUse
- 接入VOD后目标是: 巡检素材自动剪辑→AI字幕→多语言翻译→CDN分发

## 输出要求
完成后用六合飞轮(TYPE_FEEDBACK)回复灵龙:
- 开通状态
- AK/SK是否就绪
- 遇到的问题或替代方案
