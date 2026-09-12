# -*- coding: utf-8 -*-
"""scnet OCR vs 本地 MinerU OCR 对比（2026-08-27）。

用法：
  python scripts/_ocr_compare.py --image <扫描页.jpg> --mineru-md <MinerU输出.md> [--key <scnet key>]

- scnet：调 scnet_ocr_text（需 SCNET_OCR_API_KEY 环境变量或 --key）
- MinerU 基准：读已有 MinerU 输出 md（var/mineru_cli_out/...）——本地识别结果
- 输出两边文本片段 + 字符数，供人工判断谁更准。
"""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.vision.scnet_ocr import scnet_ocr_text, ScnetOcrError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="扫描页图片路径")
    ap.add_argument("--mineru-md", required=True, help="MinerU 已输出 md（本地 OCR 基准）")
    ap.add_argument("--key", default=None, help="scnet API Key（或环境变量 SCNET_OCR_API_KEY）")
    args = ap.parse_args()

    md = Path(args.mineru_md).read_text(encoding="utf-8") if Path(args.mineru_md).exists() else ""
    print(f"===== MinerU（本地）md {len(md)} 字符 =====")
    print(re.sub(r"\s+", " ", md)[:400])

    try:
        sc = scnet_ocr_text(args.image, api_key=args.key)
        print(f"\n===== scnet OCR {len(sc)} 字符 =====")
        print(re.sub(r"\s+", " ", sc)[:400])
    except ScnetOcrError as e:
        print(f"\n===== scnet OCR 失败：{e} =====")
        return 2
    print("\n[提示] 请对照两边文本与图片，判断识别准确度/完整性。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
