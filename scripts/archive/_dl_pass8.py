# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, record_issue, next_book  # noqa: E402

record_pass("GB/T1008-2008",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1008-2008 机械加工工艺装备基本术语.pdf",
            1)
record_issue("C-英文术语空格粘连", "GB/T1008-2008", "...",
             "英文术语空格粘连(special tooling→specialtooling, cold-compactingtooling, bench-worktool, body→bady 同类)——疑似 fitz 提取英文空格/字形处理，影响英文术语可读/检索(边缘，正文中文/数字/引用全对)。登记待核(可能原文无空格或 fitz 提取限制)")
b = next_book()
print("next:", (b["std_no"] + " | " + b["rel"]) if b else "NO_MORE")
