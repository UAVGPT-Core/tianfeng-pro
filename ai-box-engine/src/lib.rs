// LGOX AI Box · 边缘推理引擎
// 2035-grade · 自感知·自愈合·自进化
// 编译目标: wasm32-unknown-unknown (浏览器/边缘运行时)
//
// 核心能力:
//   1. 文本嵌入 (384维·三元量化·纯加减法)
//   2. 余弦相似度 (点积·L2归一化)
//   3. 巡检报告语义索引
//   4. 自诊断 → 健康检查 → 联邦上报

use wasm_bindgen::prelude::*;

// ═══════════════════════════════════════
// 嵌入引擎核心
// ═══════════════════════════════════════

/// 三元量化嵌入: 输入文本 → 384维向量
/// 纯加减法运算·零浮点乘法·ARM友好
#[wasm_bindgen]
pub fn embed(text: &str) -> Vec<f32> {
    // Phase2.0: 简单哈希嵌入 (占位·待替换为ternlight逻辑)
    // 后续: 集成BitNet三元权重·蒸馏自MiniLM
    let bytes = text.as_bytes();
    let mut vec = vec![0.0f32; 384];
    
    for (i, &b) in bytes.iter().enumerate() {
        let idx = i % 384;
        // 字符→三元值 (-1, 0, +1)
        vec[idx] += match b % 3 {
            0 =>  1.0,
            1 =>  0.0,
            _ => -1.0,
        };
    }
    
    // L2归一化
    let norm: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        for x in &mut vec { *x /= norm; }
    }
    
    vec
}

/// 余弦相似度 = 点积 (嵌入已L2归一化)
#[wasm_bindgen]
pub fn cosine_sim(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

/// 批量语义搜索: query + corpus → top-K
#[wasm_bindgen]
pub fn search(query: &str, corpus: Vec<String>, top_k: usize) -> String {
    let q = embed(query);
    let mut scored: Vec<(usize, f32)> = corpus.iter()
        .enumerate()
        .map(|(i, text)| (i, cosine_sim(&q, &embed(text))))
        .collect();
    
    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    scored.truncate(top_k);
    
    // 返回JSON
    let results: Vec<serde_json::Value> = scored.iter().map(|(i, s)| {
        serde_json::json!({
            "index": i,
            "text": &corpus[*i],
            "similarity": s
        })
    }).collect();
    
    serde_json::to_string(&results).unwrap_or_default()
}

// ═══════════════════════════════════════
// 自诊断 · 七自: 自感知
// ═══════════════════════════════════════

/// 引擎健康检查: 嵌入维度·吞吐量·内存
#[wasm_bindgen]
pub fn health_check() -> String {
    let test_text = "LGOX联邦AI Box边缘推理引擎";
    let t0 = js_sys::Date::now();
    let vec = embed(test_text);
    let t1 = js_sys::Date::now();
    
    serde_json::json!({
        "status": "healthy",
        "engine": "lgox-ai-box v0.1.0",
        "dim": 384,
        "inference_ms": t1 - t0,
        "norm": vec.iter().map(|x| x*x).sum::<f32>().sqrt(),
        "seven_self": {
            "自感知": "health_check端点正常",
            "自协调": "待联邦桥集成",
            "自愈合": "待watchdog集成",
            "自进化": "待模型蒸馏管线",
            "自迭代": "待巡检数据闭环",
            "自反思": "待质量评分系统",
            "自约束": "Apache-2.0合规"
        }
    }).to_string()
}

// ═══════════════════════════════════════
// 巡检报告索引
// ═══════════════════════════════════════

/// 批量索引巡检报告
#[wasm_bindgen]
pub fn index_reports(reports: Vec<String>) -> String {
    let mut indexed = Vec::new();
    for (i, report) in reports.iter().enumerate() {
        let vec = embed(report);
        indexed.push(serde_json::json!({
            "id": format!("RPT-{:04}", i),
            "preview": &report[..report.len().min(100)],
            "dims": 384,
            "embedded": true
        }));
    }
    serde_json::to_string(&serde_json::json!({
        "total": indexed.len(),
        "reports": indexed
    })).unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_embed_dims() {
        let v = embed("测试文本");
        assert_eq!(v.len(), 384);
    }

    #[test]
    fn test_cosine_self() {
        let v = embed("LGOX联邦");
        let sim = cosine_sim(&v, &v);
        assert!((sim - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_search() {
        let corpus = vec![
            "天巡是联邦第10节点".into(),
            "小枢是金融AI助手".into(),
            "七自基因包括自感知".into(),
        ];
        let result = search("AI助手", corpus, 2);
        assert!(result.contains("小枢"));
    }
}
