# -*- coding: utf-8 -*-
"""诊断：OCR/云 key 存在性 + 书单文本层分布。（一次性，供 Debug Loop 环境判断）"""
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

print("=== keys ===")
for k in ["SCNET_OCR_API_KEY", "MINERU_API_KEY", "MINERU_CLOUD", "DEEPSEEK_API_KEY",
          "MINERU_VIRTUAL_VRAM_SIZE"]:
    v = os.environ.get(k)
    print(f"  {k}: {'SET(len=%d)' % len(v) if v else '-'}")
try:
    import winreg
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
    i = 0
    while True:
        try:
            n, val, _ = winreg.EnumValue(k, i)
            i += 1
            if any(x in n.upper() for x in ["OCR", "MINERU", "SCNET", "DEEPSEEK", "API"]):
                print(f"  reg {n}: {'SET' if val else '-'}")
        except OSError:
            break
except Exception as e:
    print("  reg err", e)

print("=== text-layer scan first books ===")
import fitz
from scripts._stdparse import derive_standard
root = Path(r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)")
pdfs = sorted([p for p in root.rglob("*.pdf") if "体检结果" not in p.parts],
              key=lambda p: str(p.relative_to(root)))
seen = set()
for p in pdfs:
    no, _ = derive_standard(p)
    key = no or str(p.relative_to(root))
    if key in seen:
        continue
    seen.add(key)
    d = fitz.open(str(p))
    tl = sum(1 for i in range(min(len(d), 6)) if len(d[i].get_text().strip()) > 20)
    print(f"  {no or '?':20} pages={len(d)} textpages={tl}")
    d.close()
    if len(seen) >= 8:
        break
