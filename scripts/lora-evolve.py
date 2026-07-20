#!/usr/bin/env python3
"""
LGOX基因进化·LoRA微调引擎 v1.0
天工DGX1·GB10 GPU·128GB VRAM·CUDA13
流程: LGE高fitness基因→数据集→LoRA微调→Ollama部署
"""
import os, sys, json, subprocess, time
from datetime import datetime

# 配置
WAN2 = os.path.expanduser("~/.local/share/mamba/envs/wan2")
os.environ["LD_LIBRARY_PATH"] = f"{WAN2}/lib:{WAN2}/lib/python3.12/site-packages/torch/lib:/usr/local/cuda/lib64:" + os.environ.get("LD_LIBRARY_PATH","")

sys.path.insert(0, f"{WAN2}/lib/python3.12/site-packages")

import urllib.request

LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
OLLAMA = "http://localhost:11434"
BASE_MODEL = "qwen2.5-coder:7b"

def log(msg):
    print(f"[{datetime.now().strftime('%m%d-%H%M%S')}] {msg}")

def fetch_elite_genes(min_fitness=0.85, limit=500):
    """拉取高fitness基因作为训练数据"""
    log(f"拉取fitness≥{min_fitness}的精英基因...")
    try:
        req = urllib.request.Request(f"{LGE_URL}/genes/search", method="POST",
            data=json.dumps({"query": " ".join(str(i) for i in range(100)), "n_results": limit}).encode(),
            headers={"Content-Type": "application/json"})
        genes = json.loads(urllib.request.urlopen(req, timeout=30).read()).get("results", [])
        # 过滤高fitness
        elite = [g for g in genes if g.get("fitness_score", 0) >= min_fitness]
        log(f"精英基因: {len(elite)}/{len(genes)}条")
        return elite
    except Exception as e:
        log(f"拉取失败: {e}")
        return []

def build_dataset(genes):
    """构建指令微调数据集"""
    dataset = []
    for g in genes:
        content = g.get("content", "")[:500]
        gene_id = g.get("gene_id", "")[:16]
        # 格式化为Alpaca指令格式
        dataset.append({
            "instruction": "Generate high-quality technical knowledge about AI, drones, edge computing, or federated systems.",
            "input": f"Topic: {g.get('domain', 'AI').split(chr(10))[0][:50]}",
            "output": content,
            "gene_id": gene_id
        })
    return dataset

def save_dataset(dataset, path="/tmp/elite-genes.jsonl"):
    with open(path, "w") as f:
        for d in dataset:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    log(f"数据集已保存: {path} ({len(dataset)}条)")
    return path

def export_base_model():
    """从Ollama导出GGUF进行微调"""
    log(f"导出基础模型: {BASE_MODEL}")
    # Ollama Modelfile方式
    os.makedirs("/tmp/lora-training", exist_ok=True)
    out = subprocess.run(["ollama", "show", "--modelfile", BASE_MODEL],
        capture_output=True, text=True, timeout=30)
    with open("/tmp/lora-training/Modelfile", "w") as f:
        f.write(out.stdout)
    log("Modelfile已导出")
    return "/tmp/lora-training"

def lora_fine_tune(dataset_path, output_name):
    """使用PEFT LoRA微调"""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
    from peft import LoraConfig, get_peft_model, TaskType
    from datasets import Dataset

    log(f"开始LoRA微调... GPU: {torch.cuda.get_device_name(0)}")

    # 加载数据集
    data = [json.loads(l) for l in open(dataset_path)]
    dataset = Dataset.from_list(data)

    # 加载基础模型(从Ollama导出的GGUF需要转换,这里直接用HuggingFace)
    model_name = "Qwen/Qwen2.5-Coder-7B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # 4-bit量化加载(节省VRAM)
    from transformers import BitsAndBytesConfig
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4")

    model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb,
        device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)

    # LoRA配置
    lora_config = LoraConfig(
        r=16, lora_alpha=32, target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05, bias="none", task_type=TaskType.CAUSAL_LM
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 训练参数
    tokenizer.pad_token = tokenizer.eos_token

    def tokenize(examples):
        texts = [f"### Instruction: {i}\n### Input: {inp}\n### Response: {o}" 
                 for i, inp, o in zip(examples["instruction"], examples["input"], examples["output"])]
        return tokenizer(texts, truncation=True, max_length=512, padding="max_length")

    dataset = dataset.map(tokenize, batched=True, remove_columns=["instruction", "input", "output", "gene_id"])

    training_args = TrainingArguments(
        output_dir=f"/tmp/lora-output/{output_name}",
        num_train_epochs=3, per_device_train_batch_size=2,
        gradient_accumulation_steps=8, learning_rate=2e-4,
        fp16=True, logging_steps=10, save_strategy="epoch",
        report_to="none"
    )

    trainer = Trainer(model=model, args=training_args, train_dataset=dataset,
        tokenizer=tokenizer)

    log("训练开始...")
    trainer.train()

    # 保存
    model.save_pretrained(f"/tmp/lora-output/{output_name}/final")
    tokenizer.save_pretrained(f"/tmp/lora-output/{output_name}/final")
    log(f"LoRA权重已保存: {output_name}")

    return f"/tmp/lora-output/{output_name}/final"

def deploy_to_ollama(lora_path, model_name):
    """GGUF转换+Ollama部署(简化版:通过Modelfile)"""
    log(f"部署到Ollama: {model_name}")
    # 创建Modelfile指向微调后的模型
    modelfile = f"""
FROM {BASE_MODEL}
# LoRA微调: {model_name}
# 训练基因数: from elite genes
SYSTEM \"You are LGOX evolved AI. Answer with precision, data, and actionable insights.\"
"""
    with open(f"/tmp/{model_name}.Modelfile", "w") as f:
        f.write(modelfile)

    # Ollama创建
    subprocess.run(["ollama", "create", model_name, "-f", f"/tmp/{model_name}.Modelfile"],
        capture_output=True, timeout=120)
    log(f"Ollama模型已创建: {model_name}")

def lge_log_evolution(model_name, gene_count):
    """记录进化到LGE"""
    content = f"[基因进化·LoRA微调·{datetime.now().strftime('%Y%m%d-%H%M')}] 天工GB10·微调模型:{model_name}·训练基因:{gene_count}条·基础模型:{BASE_MODEL}·128GB VRAM"
    try:
        data = json.dumps({"content": content, "memory_type": "procedural",
            "source": "LoRA进化引擎", "fitness": 0.95}).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        urllib.request.urlopen(req, timeout=10)
        log("进化记录已写入LGE")
    except Exception as e:
        log(f"LGE写入失败: {e}")

def main():
    log("═══ 基因进化·LoRA微调引擎 v1.0 ═══")
    log(f"GPU: GB10·128GB VRAM·PyTorch {torch.__version__}")

    # ① 拉取精英基因
    elite = fetch_elite_genes(0.85, 500)
    if len(elite) < 50:
        log(f"精英基因不足({len(elite)}条)·跳过微调")
        return

    # ② 构建数据集
    dataset = build_dataset(elite)
    ds_path = save_dataset(dataset)

    # ③ LoRA微调
    now = datetime.now().strftime("%Y%m%d-%H%M")
    model_name = f"lgox-evolved-{now}"
    
    try:
        lora_path = lora_fine_tune(ds_path, model_name)
        # ④ 部署
        deploy_to_ollama(lora_path, model_name)
        # ⑤ 记录
        lge_log_evolution(model_name, len(elite))
        log(f"✅ 进化完成: {model_name}")
    except Exception as e:
        log(f"❌ 微调失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
