# -*- coding: utf-8 -*-
"""从 scnet OCR 文档提取 限速/大小/类型/计费/配额 信息。"""
import re, html as h
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]) if False else "")
from pathlib import Path
sys.path.insert(0, r"D:\AI\work space\zcode")
from src.core.update.channels.base import CurlCffiTransport

t = CurlCffiTransport()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
url = "https://www1.scnet.cn/ac/openapi/doc/2.0/moduleapi/api/ocr.html"
st, body = t.fetch(url, headers={"User-Agent": UA})
txt = re.sub(r"<[^>]+>", " ", str(body))
txt = h.unescape(re.sub(r"\s+", " ", txt))
print("=== ocr.html 限速/限制/计费相关 ===")
seen = set()
for kw in ["限速", "限流", "QPS", "额度", "免费", "上限", "次数", "计费",
           "MB", "大小", "格式", "类型", "支持", "限制", "并发", "有效期", "token"]:
    for m in re.finditer(re.escape(kw) + r".{0,90}", txt):
        s = m.group(0).strip()
        if 12 < len(s) < 110 and s[:40] not in seen:
            seen.add(s[:40])
            print(f"  [{kw}] {s}")
