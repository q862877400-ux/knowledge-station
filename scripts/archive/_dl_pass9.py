# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, record_issue, next_book  # noqa: E402

record_pass("GB/T1019-2008",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1019-2008 家用和类似用途电器包装通则.pdf",
            1)
record_issue("C-英文术语空格粘连", "GB/T1019-2008", "...",
             "英文术语空格粘连(moistureproofpackaging/generalrequirement)——fitz 英文空格(同 GB/T1008 同类，边缘)") 
b = next_book()
print("next:", (b["std_no"] + " | " + b["rel"]) if b else "NO_MORE")
