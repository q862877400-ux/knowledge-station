# -*- coding: utf-8 -*-
"""诊断 text_layer_pua_mangled 各判据指标，确认 GB/T 1000-2016 被哪个判据误判。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.ingestion.mineru_adapter import _extract_text_blocks, text_layer_pua_mangled  # noqa: E402
from src.core.ingestion.mineru_adapter import _PUA_GB_PREFIX, _is_weird_char  # noqa: E402

pdf = r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1000-2016 高压线路针式瓷绝缘子尺寸与特性.pdf"
blocks = _extract_text_blocks(Path(pdf))
sample, total = [], 0
for b in blocks[:120]:
    t = (b.get("text") or "").strip()
    if t:
        sample.append(t)
        total += len(t)
    if total > 4000:
        break
joined = "\n".join(sample)
n = max(1, len(joined))
gb = len(_PUA_GB_PREFIX.findall(joined))
shift = sum(1 for ch in joined if 0x21 <= ord(ch) <= 0x2A)
digits = sum(1 for ch in joined if "0" <= ch <= "9")
weird = sum(1 for ch in joined if _is_weird_char(ch))
cjk = sum(1 for ch in joined if "\u4e00" <= ch <= "\u9fff")
print("blocks:", len(blocks), "sample_len:", len(joined))
print("判据一 犌犅犜 计数:", gb, "->", gb >= 2)
print("判据二 shift:", shift, "占比%.3f" % (shift / n), "digits占比%.3f" % (digits / n),
      "->", shift >= 30 and shift / n > 0.03 and digits / n < 0.005)
print("判据三 weird占比%.3f" % (weird / n), "->", weird / n > 0.15)
print("判据四 cjk占比%.3f" % (cjk / n), "->", cjk / n < 0.05)
print("长跑: ", end="")
run, prev, hitrun = 1, None, False
for ch in joined:
    if ch == prev and not ch.isspace() and not ch.isascii() and not ("\u4e00" <= ch <= "\u9fff"):
        run += 1
        if run >= 12:
            hitrun = True
    else:
        run = 1
    prev = ch
print(hitrun)
print("---------- text_layer_pua_mangled() =", text_layer_pua_mangled(blocks))
