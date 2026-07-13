#!/usr/bin/env python3
"""
字幕烧录 v1.0 · PIL零依赖方案
优于libass: 免费·MIT·不重编译ffmpeg·直接烧字到帧
基因ID: GENE-PRO-subtitle-burn-v1
"""
from PIL import Image, ImageDraw, ImageFont
import os, sys

FONT = "/System/Library/Fonts/Helvetica.ttc"

def parse_srt(srt_path):
    with open(srt_path) as f:
        text = f.read()
    subs = []
    for block in text.strip().split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            times = lines[1].split(" --> ")
            t1 = sum(float(x)*[3600,60,1][i] for i,x in enumerate(times[0].replace(",",".").split(":")))
            t2 = sum(float(x)*[3600,60,1][i] for i,x in enumerate(times[1].replace(",",".").split(":")))
            subs.append((t1, t2, " ".join(lines[2:])))
    return subs

def burn_subs(image_dir, srt_path, output_dir, font_size=48, color="#c9a24e"):
    subs = parse_srt(srt_path)
    images = sorted([f for f in os.listdir(image_dir) if f.endswith(('.png','.jpg'))])
    if not images: return []
    try: font = ImageFont.truetype(FONT, font_size)
    except: font = ImageFont.load_default()
    
    results = []
    for i, fn in enumerate(images):
        img = Image.open(os.path.join(image_dir, fn)).convert("RGBA")
        d = ImageDraw.Draw(img)
        frame_time = i * (len(subs)*0.8)
        for start, end, text in subs:
            if frame_time >= start and frame_time <= end:
                bbox = d.textbbox((0,0), text, font=font)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                x, y = (img.width-tw)//2, img.height - 140
                d.rectangle([x-24, y-12, x+tw+24, y+th+12], fill=(0,0,0,180))
                d.text((x, y), text, fill=color, font=font)
        out = os.path.join(output_dir, f"sub_{fn}")
        img.convert("RGB").save(out)
        results.append(out)
    return results

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("burn-subs v1.0 | 用法: burn-subs.py <图片目录> <SRT> [输出目录]")
        sys.exit(1)
    img_dir, srt = sys.argv[1], sys.argv[2]
    out_dir = sys.argv[3] if len(sys.argv) > 3 else img_dir + "/subs"
    os.makedirs(out_dir, exist_ok=True)
    r = burn_subs(img_dir, srt, out_dir)
    print(f"✅ {len(r)}帧字幕已烧录 → {out_dir}")
