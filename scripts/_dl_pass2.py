# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, record_issue, next_book  # noqa: E402

record_pass("GB/T9278-2008",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T  9278-2008 涂料试样状态调节和试验的温湿度.pdf",
            1)
record_issue("C-OCR单字误", "GB/T9278-2008", "...",
             "扫描件 MinerU OCR 字误：'几是'(凡是→几是)；扫描件固有(MinerU OCR 精度)，主体/数字/符号保真。待 A2.5 LLM 纠错")
b = next_book()
print("next:", (b["std_no"] + " | " + b["rel"]) if b else "NO_MORE")
