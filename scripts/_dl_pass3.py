# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, next_book  # noqa: E402

record_pass("GB/T1.1-2020",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1.1-2020 标准化工作导则 第1部分：标准化文件的结构和起草规则(1).pdf",
            1)
b = next_book()
print("next:", (b["std_no"] + " | " + b["rel"]) if b else "NO_MORE")
