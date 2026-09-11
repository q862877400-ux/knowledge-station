# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, record_issue, next_book  # noqa: E402

record_pass("GB/T1.2-2020",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1.2-2020 标准化工作导则 第2部分：以ISOIEC标准化文件为基础的标准化文件起草规则.pdf",
            1)
record_issue("C-OCR数字尾丢", "GB/T1.2-2020", "...",
             "扫描件 MinerU OCR 数字尾丢：'ISO 9000:201'(应为2015)；另引号形态《>。扫描件固有(MinerU OCR 精度)，主体/术语/结构保真")
b = next_book()
print("next:", (b["std_no"] + " | " + b["rel"]) if b else "NO_MORE")
